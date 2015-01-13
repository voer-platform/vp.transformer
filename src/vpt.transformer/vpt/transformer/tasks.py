import os
import re
import datetime
import shutil
import subprocess
import zipfile
import json
import codecs
import libxml2
import libxslt
from lxml import etree
from cStringIO import StringIO

from celery.task import task

from rhaptos.cnxmlutils.odt2cnxml import transform
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

import convert as JOD # Imports JOD convert script

from pyramid.i18n import TranslationStringFactory, make_localizer
_ = TranslationStringFactory('transformer')

@task
def process_import(save_dir_path, original_filepath, filename, download_url):
    # convert from other office format to odt
    odt_filename = '%s.odt' % filename
    odt_filepath = str(os.path.join(save_dir_path, odt_filename))
    # run jod service
    converter = JOD.DocumentConverterClient()
    try:
        converter.convert(original_filepath, 'odt', odt_filepath)
    except Exception as e:
        raise e

    # check file existed
    try:
        fp = open(odt_filepath, 'r')
        fp.close()
    except IOError as io:
        # TODO: raise exception
        raise io

    # convert to cnxml
    tree, files, errors = transform(odt_filepath)
    cnxml = clean_cnxml(etree.tostring(tree))

    # convert to html
    html = cnxml_to_htmlpreview(cnxml)

    # produce zipfile
    ram = StringIO()
    zip_archive = zipfile.ZipFile(ram, 'w')
    zip_archive.writestr('index.html', html)
    for fname, fdata in files.items():
        zip_archive.writestr(fname, fdata)
    zip_archive.close()

    # save zipfile
    zip_file_path = os.path.join(save_dir_path, '%s.zip' % filename)
    if os.path.exists(zip_file_path):
        os.rename(zip_file_path, zip_file_path + '~')
    f = open(zip_file_path, 'wb')
    f.write(ram.getvalue())
    f.close()

    return download_url

# Pretty CNXML printing with libxml2 because etree/lxml cannot do pretty printing semantic correct
def clean_cnxml(iCnxml, iMaxColumns=80):
    current_dir = os.path.dirname(__file__)

    # WORKAROUND - fix bug: duplicated figures show on top after imported docx
    xsl = etree.parse(os.path.join(current_dir, 'cleanup.xsl'))
    xslt = etree.XSLT(xsl)
    xml = etree.fromstring(iCnxml)
    xml = xslt(xml)
    iCnxml = etree.tostring(xml)
    
    xsl = os.path.join(current_dir, 'utils_pretty.xsl')
    style_doc = libxml2.parseFile(xsl)
    style = libxslt.parseStylesheetDoc(style_doc)
    doc = libxml2.parseDoc(iCnxml)
    result = style.applyStylesheet(doc, None)
    pretty_cnxml = style.saveResultToString(result)
    style.freeStylesheet()
    doc.freeDoc()
    result.freeDoc()
    return pretty_cnxml

@task
def process_export(output_type, save_dir_path, export_dir_path, output_file_path, download_url, translation_dirs):
    input_file_paths, err_msg = getInputFiles(output_type, export_dir_path, save_dir_path, translation_dirs)
    if err_msg is not None:
        raise Exception(err_msg)

    if output_type == 'pdf':
        process_pdf(save_dir_path, export_dir_path, output_file_path, input_file_paths)
    else:
        process_epub(save_dir_path, export_dir_path, output_file_path, input_file_paths)

    # get exported file
    rf = open(output_file_path, 'r')
    body = rf.read()
    rf.close()

    return download_url

def process_pdf(save_dir_path, export_dir_path, output_file_path, input_file_paths):
    # Run princexml to generate a pdf file
    pdfgen = '/usr/local/bin/prince'
    strCmd = [pdfgen, '-i', 'html5',
              '-s', '%s/pdf.css' % save_dir_path]
    strCmd.extend(input_file_paths)
    strCmd.extend(['-o', output_file_path])
    env = { }
    # run the program with subprocess and pipe the input and output to variables
    p = subprocess.Popen(strCmd, close_fds=True, env=env)
    # set STDIN and STDOUT and wait untill the program finishes
    _, stdErr = p.communicate()

def process_epub(save_dir_path, export_dir_path, output_file_path, input_file_paths):
    # Run ebook-convert (calibre) to generate a epub file
    epubgen = '/usr/bin/ebook-convert'
    strCmd = [epubgen,]
    strCmd.extend(input_file_paths)
    strCmd.extend([output_file_path, '--no-default-epub-cover', '--no-chapters-in-toc',
                   '--level1-toc', '//h:h1[@class="section-title level-0"]',
                   '--level2-toc', '//h:h1[@class="section-title level-1"]',
                   '--level3-toc', '//h:h1[@class="section-title level-2"]'])
    env = { }
    # run the program with subprocess and pipe the input and output to variables
    p = subprocess.Popen(strCmd, close_fds=True, env=env)
    # set STDIN and STDOUT and wait untill the program finishes
    _, stdErr = p.communicate()

def getInputFiles(output_type, export_dir_path, save_dir_path='', translation_dirs=[]):
    """
    Return a list of path to index.html and chapter.html files if it's a collection.
    Return turn the path to index.html only if it's a module.
    Collection file structrure looks like:
        collection-x/
            collection.json
            module-1/
                index.html
                p1.jpg
                p2.jpg
                ...
            module-2/
                index.html
                p1.jpg
                p2.jpg
                ...
    """
    results = []
    err_msg = None
    # FIXED config filename
    config_filename = 'collection.json'
    config_filepath = os.path.join(export_dir_path, config_filename)
    try:
        with open(config_filepath, 'rb') as cf:
            lines = cf.readlines()
            data = ''.join([line.strip('\n').strip() for line in lines])
            try:
                collection = json.loads(data)
            except ValueError, e:
                err_msg = 'ValueError [parsing collection.json]: %s' % e.message
                return results, err_msg
            # processing the title page
            title = collection['title']
            subtitle = collection.get('subtitle', '')
            editors = collection.get('editors')
            language = collection.get('language', 'vi')
            # making localizer for i18n translation
            localizer = make_localizer(language, translation_dirs)
            title_filepath = os.path.join(export_dir_path, 'title.html')
            titlepage_html = createTitlePage(title_filepath, title, editors, subtitle=subtitle,
                                             save_dir_path=save_dir_path, localizer=localizer, output_type=output_type)
            # add path of title.html into result list
            results.append(title_filepath)
            # recursively process collection content
            data = processCollection(export_dir_path, collection['content'], save_dir_path=save_dir_path, localizer=localizer)
            authors = data[2]
            # processing the title page 2
            title_filepath2 = os.path.join(export_dir_path, 'title2.html')
            createTitlePage(title_filepath2, title, editors, authors, collection.get('url'),
                            collection.get('version'), subtitle=subtitle, save_dir_path=save_dir_path, localizer=localizer)
            # add path of title2.html into result list
            results.append(title_filepath2)
            tocs = data[1]
            tocs.sort(key=lambda toc: toc[2])
            # create a toc.html file
            toc_filename = 'toc.html'
            toc_filepath = os.path.join(export_dir_path, toc_filename)
            createTOCPage(toc_filepath, tocs, localizer=localizer, output_type=output_type,
                          titlepage_html=titlepage_html, collection_title=title)
            results.append(toc_filepath)
            # add path of modules index.html into result list
            results.extend(data[0])
            # processing contribution page
            contrib_filename = 'contrib.html'
            contrib_filepath = os.path.join(export_dir_path, contrib_filename)
            # append endpage after contrib page for epub export only
            endfile_name = 'end_%s.html' % language
            endfile_path = os.path.join(save_dir_path, endfile_name)
            createContributionPage(contrib_filepath, collection, data[3], localizer=localizer,
                                   endfile_path=endfile_path, output_type=output_type)
            results.append(contrib_filepath)
            # add end page
            results.append(endfile_path)
            if output_type == 'epub':
                # copy epub css file and brand images to exported dir
                import shutil, errno
                epub_css_src = '%s/epub.css' % save_dir_path
                epub_css_dst = '%s/epub.css' % export_dir_path
                shutil.copy(epub_css_src, epub_css_dst)
                imgs_src = '%s/images' % save_dir_path
                imgs_dst = '%s/images' % export_dir_path
                shutil.copytree(imgs_src, imgs_dst)
                # epub export only need toc file
                return [toc_filepath, ], err_msg
    except IOError:
        # it's a module
        metadata_filepath = os.path.join(export_dir_path, 'metadata.json')
        with open(metadata_filepath, 'rb') as mf:
            lines = mf.readlines()
            json_data = ''.join([line.strip('\n').strip() for line in lines])
            try:
                metadata = json.loads(json_data)
            except ValueError, e:
                err_msg = 'ValueError [parsing metadata.json]: %s' % e.message
                return results, err_msg
        language = metadata.get('language', 'vi')
        # making localizer for i18n translation
        localizer = make_localizer(language, translation_dirs)
        data = processModule(export_dir_path, localizer=localizer)
        results.extend(data[0])
        err_msg = data[1]

    return results, err_msg

def processModule(export_dir_path, localizer=None):
    results = []
    err_msg = None
    # it's a module -> return path to index.html only
    index_filepath = os.path.join(export_dir_path, 'index.html')
    results.append(index_filepath)
    # process metadata
    # FIXED metadata filename
    metadata_filename = 'metadata.json'
    metadata_filepath = os.path.join(export_dir_path, metadata_filename)
    try:
        with open(metadata_filepath, 'rb') as mf:
            # read metadata from json
            lines = mf.readlines()
            data = ''.join([line.strip('\n').strip() for line in lines])
            try:
                metadata = json.loads(data)
            except ValueError, e:
                err_msg = 'ValueError [parsing metadata.json]: %s' % e.message
                return results, err_msg
            # encoding module title
            title = metadata['title']
            try:
                title = unicode(title, 'utf-8')
            except TypeError:
                pass
            title = title.encode('ascii', 'xmlcharrefreplace')
            # update module's index.html
            updateModuleHTML(index_filepath, metadata, localizer=localizer)
    except IOError:
        # no metadata
        pass
    return results, err_msg

def processCollection(export_dir_path, content, parents=[], save_dir_path='', localizer=None):
    results = []
    tocs = []
    authors = set()
    modules = [] # list of module metadata
    i = 0
    for item in content:
        if len(parents) == 0:
            if item['type'] == 'module':
                id = item['id']
            else:
                id = 'subcollection_%d_%d' % (len(parents), i)
        i += 1
        # build data for TOC
        numbers = [parent.get('number', 0) for parent in parents]
        numbers.append(i)
        numbering = '.'.join([str(n) for n in numbers])
        toc_str = '%s. %s' % (numbering, item['title'])
        toc_level = len(parents)
        # add module id to toc to build href
        toc_module_id = getModuleId4TOC(item)
        tocs.append((toc_level, toc_str, numbers, toc_module_id))
        if item['type'] == 'module':
            authors.update(item.get('authors', []))
            modules.append(item)
            index_filepath = os.path.join(export_dir_path, item['id'], 'index.html')
            # update module's index.html
            if len(parents) and i == 1:
                section_titles = getParentTitles(parents)
            else:
                section_titles = []
            section_titles.append([item['title'], toc_level])
            updateModuleHTML(index_filepath, save_dir_path=save_dir_path, section_titles=section_titles, localizer=localizer)
            # add path of index.html in each module into result list
            results.append(index_filepath)
        else:
            parent = dict(
                number = i,
                title = item['title'],
                level = toc_level
            )
            data = processCollection(export_dir_path, item['content'], parents + [parent,], save_dir_path, localizer=localizer)
            results.extend(data[0])
            tocs.extend(data[1])
            authors.update(data[2])
            modules.extend(data[3])
    return results, tocs, authors, modules

def getModuleId4TOC(data):
    """
    Input: json metadata of sub-collection/module
    Output: nearest module id
    """
    if data['type'] == 'module':
        return data.get('id')
    elif data.has_key('content') and len(data['content']) > 0:
        return getModuleId4TOC(data['content'][0])
    return None

def getParentTitles(parents):
    """
    Input: a list of parent sections of a module
    Ouput: titles of direct parent sections (1st index in level)
    """
    titles = []
    for parent in reversed(parents):
        titles.append([parent.get('title', ''), parent.get('level', 0)])
        if parent.get('number', 0) <> 1: break
    return titles[::-1]

def createTitlePage(filepath, title, editors=None, authors=None, url=None, version=None,
                    subtitle='', save_dir_path='', localizer=None, output_type='pdf'):
    logo_path = os.path.join(save_dir_path, 'images/VOER.logo.jpeg')
    if output_type == 'pdf':
        html = u'<html><body>'
        html += u'<div id="title-page"><div class="logo"><center><img src="%s" width="155" /></center></div>' % logo_path
    else:
        html = u'<div id="title-page">'
    html += u'<h1 class="collection-title %s">%s</h1>' % (authors and 'title2' or '', title)
    html += u'<h2 class="collection-subtitle">%s</h2>' % subtitle
    # insert editors
    if editors:
        lbl_edited_by = localizer.translate(_('edited-by', default='Edited by'))
        html += u"""<div id="editors">
  <div class="by coll-by">%s:</div>""" % lbl_edited_by
        for editor in editors:
            html += u'<div>%s</div>' % editor
        html += u'</div>'
    # insert authors
    if authors:
        lbl_authors = localizer.translate(_('authors', default='Authors'))
        html += u"""<div id="authors">
  <div class="by coll-by">%s:</div>""" % lbl_authors
        for author in authors:
            html += u'<div>%s</div>' % author
        html += u'</div>'
    # insert link
    if url:
        # WORKAROUND: hide version from url
        #if version: url = '/'.join([url.rstrip('/'), str(version)])
        lbl_ol_ver = localizer.translate(_('online-version', default='Online version'))
        html += u"""<div id="collection-link">
  <div>%s:</div>""" % lbl_ol_ver
        html += u'<div><a href="%s">%s</a></div>' % (url, url)
        html += u'</div>'
    # end html
    html += u'</div>'
    if output_type == 'pdf':
        html += u'</body></html>'
        f = codecs.open(filepath, 'wb', 'utf-8')
        f.write(html)
        f.close()
    return html

def createTOCPage(filepath, tocs, localizer=None, output_type='pdf', titlepage_html='', collection_title=''):
    lbl_outline = localizer.translate(_('outline', default='Outline'))
    html = '<html>'
    if output_type == 'epub':
        html += '<head><title>%s</title>' % collection_title
        html += '<link href="epub.css" rel="stylesheet" />'
        html += '</head><body>'
        html += titlepage_html
    else:
        html += '<head></head><body>'
    html += '<div id="toc"><h1 id="menu">%s</h1><ul class="tocs">' % lbl_outline
    for toc in tocs:
        toc_level = toc[0]
        toc_str = toc[1]
        try:
            toc_str = unicode(toc_str, 'utf-8')
        except TypeError:
            pass
        module_index_file_path = ''
        if toc[3]:
            module_index_file_path = '%s/index.html' % toc[3]
        html += '<li class="level-%d">%s<a href="%s">%s</a></li>' % (toc_level, '&nbsp;&nbsp;&nbsp;&nbsp;'*toc_level, module_index_file_path, toc_str.encode('ascii', 'xmlcharrefreplace'))
    lbl_contrib = localizer.translate(_('contribution', default='Contribution'))
    html += '<li class="level-0"><a href="contrib.html">%s</a></li></ul></div></body></html>' % lbl_contrib
    f = codecs.open(filepath, 'wb', 'utf-8')
    f.write(html)
    f.close()

def createContributionPage(filepath, collection, modules, localizer=None, endfile_path='', output_type='pdf'):
    lbl_contrib = localizer.translate(_('contribution', default='Contribution'))
    lbl_coll = localizer.translate(_('collection', default='Collection'))
    html = '<html><body>'
    html += """
  <div class="coll-contrib">
    <h1 class="contrib-title">%s</h1>
    <div>%s: %s</div>""" % (lbl_contrib, lbl_coll, collection['title'])
    lbl_edited_by = localizer.translate(_('edited-by', default='Edited by'))
    html += '<div>%s: ' % lbl_edited_by
    editors = ''
    for editor in collection.get('editors', []):
        editors += '%s, ' % editor
    html += editors.rstrip(', ') + '</div>'
    html += '<div>URL: %s</div>' % collection.get('url', '')
    lbl_license = localizer.translate(_('license', default='License'))
    html += '<div>%s: %s</div>' % (lbl_license, collection.get('license', ''))
    for module in modules:
        html += '<div class="module-contrib">'
        html += '<div>Module: %s</div>' % module['title']
        lbl_authors = localizer.translate(_('authors', default='Authors'))
        html += '<div>%s: ' % lbl_authors
        authors = ''
        for author in module.get('authors', []):
            authors += '%s, ' % author
        html += authors.rstrip(', ') + '</div>'
        html += '<div>URL: %s</div>' % module.get('url', '')
        html += '<div>%s: %s</div>' % (lbl_license, module.get('license', ''))
        html += '</div>'
    html += '</div>'
    if endfile_path:
        f = codecs.open(endfile_path, 'r+', 'utf-8')
        endfile_html = f.read()
        f.close()
        endfile_html.replace('<html>', '')
        endfile_html.replace('<head></head>', '')
        endfile_html.replace('<body>', '')
        endfile_html.replace('</body>', '')
        endfile_html.replace('</html>', '')
        html += endfile_html
    html += '</body></html>'
    f = codecs.open(filepath, 'wb', 'utf-8')
    f.write(html)
    f.close()

def updateModuleHTML(filepath, metadata=None, save_dir_path='', section_titles=[], localizer=None):
    f = codecs.open(filepath, 'r+', 'utf-8')
    content = f.read()
    f.seek(0)
    # remove self-closing tags
    content = re.sub(r'<em[^>]+?/>', r'', content)
    content = re.sub(r'<strong[^>]+?/>', r'', content)
    # TEMP: remove display-math.js
    html = """<html>
<head></head>"""

    if metadata: # it's module export
        # insert module title and authors above content
        lbl_by = localizer.translate(_('by', default='By'))
        html += """<body class="module-export">
    <h1 class="module-title">%s</h1>
    <div id="authors">
      <div class="by">%s:</div>
    """ % (metadata['title'], lbl_by)
        for author in metadata.get('authors', []):
            html += '<div>%s</div>' % author
        html += '</div>'
    else:
        html += """<body class="collection-export">"""

    for section_title in section_titles:
        # insert section title (for collection export only)
        html += """<h1 class="section-title level-%d">%s</h1>""" % (section_title[1], section_title[0])

    html += """%s</body></html>""" % content
    f.write(html)
    f.close()

