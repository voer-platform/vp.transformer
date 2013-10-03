import os
import datetime
import subprocess
import shutil
import libxml2
import libxslt
import zipfile
import json
import requests
import codecs

from cStringIO import StringIO
from lxml import etree

from pyramid.view import view_config
from pyramid.response import Response

from rhaptos.cnxmlutils.odt2cnxml import transform
from rhaptos.cnxmlutils.xml2xhtml import transform_cnxml
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

import convert as JOD # Imports JOD convert script
from .tasks import process_import
from .no_accent_vietnamese_unicodedata import no_accent_vietnamese

def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'

@view_config(route_name='home', renderer='templates/home.pt')
def home_view(request):
    """
    Default homepage with help information.
    """
    return {'project': 'vpt.transformer'}

@view_config(name='import')
def import_view(request):
    # get input file from request
    fs = request.POST.get('file')
    # get token and client id from request
    token = request.POST.get('token')
    cid = request.POST.get('cid')
    # get celery task id from request
    task_id = request.params.get('task_id')

    # validate inputs
    error = validate_inputs(fs, token, cid)
    if error is not None:
        return Response(error[0], error[1])

    # path to filestorages
    save_dir_path = request.registry.settings['transform_dir']

    # handle vietnamese filename
    fs_filename = no_accent_vietnamese(fs.filename)

    if task_id:
        # check the status of celery task
        result = process_import.AsyncResult(task_id)
        # get the status
        msg = result.status
        if result.successful():
            # get the result of the task (an download url)
            msg = result.get()
        elif result.failed():
            # running task got error
            return Response('Conversion Error', 500)
        return Response(msg)
    else:
        # save the original file so that we can convert, plus keep it.
        now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        original_filename = '%s-%s' % (now_string, fs_filename)
        original_filepath = str(os.path.join(save_dir_path, original_filename))
        saved_file = open(original_filepath, 'wb')
        input_file = fs.file
        shutil.copyfileobj(input_file, saved_file)
        saved_file.close()
        input_file.close()

        # get the filename without extension
        filename, extension = os.path.splitext(original_filename)

        # generate the expected download url of converted file
        download_url = request.static_url('transforms/%s.zip' % filename)

    	# call celery task
    	result = process_import.delay(save_dir_path, original_filepath, filename, download_url)
    	return Response(result.task_id)

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

def validate_inputs(fs, token, cid):
    # TODO: validate mimetypes
    # TODO: validate file size
    if fs is None:
        return ('File Not Found', 404)
    if not hasattr(fs, 'filename'):
        return ('File Error', 500)
#    if token is None:
#        return ('Token Not Found', 404)
#    if cid is None:
#        return ('Client Id Not Found', 404)
#    if not isValidToken(token, cid):
#        return ('Invalid Token', 401)
    # if no errors
    return None

def isValidToken(token, cid):
    base_url = 'http://dev.voer.vn:2013/1/token'
    url = '%s/%s/?cid=%s' % (base_url, token, cid)
    r = requests.get(url)
    if r.status_code == 200:
        return True
    return False

# not used, should be removed then
def generateVPXML(original_filename='', filenames=[]):
    content = """
<?xml version="1.0"?>
<vpxml xmlns="http://voer.edu.vn/vpxml" vdp_version="1.0">
    <title>%(title)s</title>

    <metadata>    
       <type>module</type>
       <version>1.0</version>
       <origin>VOER CMS</origin>
       <created>%(created)s<created>
       <modified></modified>
       <license></license>
    </metadata>

    <files>"""
    for filename in filenames:
        content += """
       <file id="%s">
           <path>content/%s</path>
       </file>""" % (filename, filename)
    content += """
    </files>

    <order>"""
    for filename in filenames:
        content += """
       <file_id>%s</file_id>""" % filename
    content += """
    </order>
</vpxml>"""
    return content % {'title': original_filename,
                      'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

@view_config(name='export')
def export_view(request):
    # get input file from request
    fs = request.POST.get('file')
    # get export type
    output_type = request.POST.get('output')
    # get token and client id from request
    token = request.POST.get('token')
    cid = request.POST.get('cid')

    # validate inputs
    # TODO: validate output type
    error = validate_inputs(fs, token, cid)
    if error is not None:
        return Response(error[0], error[1])

    # path to filestorages
    save_dir_path = request.registry.settings['transform_dir']

    # handle vietnamese filename
    fs_filename = no_accent_vietnamese(fs.filename)

    # save the original file so that we can convert, plus keep it.
    now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    original_filename = '%s-%s' % (now_string, fs_filename)
    original_filepath = str(os.path.join(save_dir_path, original_filename))
    saved_file = open(original_filepath, 'wb')
    input_file = fs.file
    shutil.copyfileobj(input_file, saved_file)
    saved_file.close()
    input_file.close()

    zip_archive = zipfile.ZipFile(original_filepath, 'r')
    # Unzip into a new directory
    filename, extension = os.path.splitext(original_filename)
    export_dir_path = os.path.join(save_dir_path, filename)
    os.mkdir(export_dir_path)
    zip_archive.extractall(path=export_dir_path)

    # Run wkxhtmltopdf to generate a pdf file
    pdfgen = '/usr/bin/wkhtmltopdf'
    input_file_paths, err_msg, extraCmd = getInputFiles(export_dir_path)
    if err_msg is not None:
        return Response(err_msg, 500)
    output_filename = '%s.pdf' % os.path.splitext(fs_filename)[0]
    output_file_path = os.path.join(export_dir_path, output_filename)
    strCmd = [pdfgen,
              '--footer-spacing', '2', '--header-spacing', '5',
              '--encoding', 'utf8',
              '-L','25mm', '-T','20mm', '-R','20mm', '-B','20mm',
              '--user-style-sheet', '%s/pdf.css' % save_dir_path,
              '-q']
    strCmd.extend(extraCmd)
    strCmd.extend(input_file_paths)
    strCmd.append(output_file_path)
    env = { }
    # run the program with subprocess and pipe the input and output to variables
    p = subprocess.Popen(strCmd, close_fds=True, env=env)
    # set STDIN and STDOUT and wait untill the program finishes
    _, stdErr = p.communicate()

    # get exported file and return the response
    rf = open(output_file_path, 'r')
    body = rf.read()
    rf.close()

    return Response(content_type='application/pdf', content_disposition='attachment; filename=%s' % output_filename, body=body)

def getInputFiles(export_dir_path):
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
    extraCmd = []
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
                return results, err_msg, extraCmd
            # processing the title page
            title = collection['title']
            editors = collection.get('editors')
            title_filepath = os.path.join(export_dir_path, 'title.html')
            createTitlePage(title_filepath, title, editors)
            # add path of title.html into result list
            results.append(title_filepath)
            # recursively process collection content
            data = processCollection(export_dir_path, collection['content'])
            authors = data[2]
            # processing the title page 2
            title_filepath2 = os.path.join(export_dir_path, 'title2.html')
            createTitlePage(title_filepath2, title, editors, authors, collection.get('url'), collection.get('version'))
            # add path of title2.html into result list
            results.append(title_filepath2)
            tocs = data[1]
            tocs.sort(key=lambda toc: toc[1])
            # create a toc.html file
            toc_filename = 'toc.html'
            toc_filepath = os.path.join(export_dir_path, toc_filename)
            createTOCPage(toc_filepath, tocs)
            results.append(toc_filepath)
            # add path of modules index.html into result list
            results.extend(data[0])
            # processing contribution page
            contrib_filename = 'contrib.html'
            contrib_filepath = os.path.join(export_dir_path, contrib_filename)
            createContributionPage(contrib_filepath, collection, data[3])
            results.append(contrib_filepath)
    except IOError:
        # it's a module
        data = processModule(export_dir_path)
        results.extend(data[0])
        err_msg = data[1]
        extraCmd.extend(data[2])

    # add footer-html with page number only if it's not set previously
    if '--footer-html' not in extraCmd:
        footer_filepath = os.path.join(export_dir_path, 'footer.html')
        createHTMLFooter(footer_filepath)
        extraCmd.extend(['--footer-html', footer_filepath])

    return results, err_msg, extraCmd

def processModule(export_dir_path):
    site_name = 'Th&#432; vi&#7879;n H&#7885;c li&#7879;u m&#7903; Vi&#7879;t Nam'
    results = []
    err_msg = None
    # it's a module -> return path to index.html only
    index_filepath = os.path.join(export_dir_path, 'index.html')
    results.append(index_filepath)
    # process metadata
    extraCmd = []
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
                return results, err_msg, extraCmd
            # encoding module title
            title = metadata['title']
            try:
                title = unicode(title, 'utf-8')
            except TypeError:
                pass
            title = title.encode('ascii', 'xmlcharrefreplace')
            # generate html header
            header_filepath = os.path.join(export_dir_path, 'header.html')
            createHTMLHeader(header_filepath, '%s - %s' % (title, site_name))
            extraCmd.extend(['--header-html', header_filepath])
            # add module url to footer-left
            footer_filepath = os.path.join(export_dir_path, 'footer.html')
            createHTMLFooter(footer_filepath, metadata.get('url', ''))
            extraCmd.extend(['--footer-html', footer_filepath])
            # update module's index.html
            updateModuleHTML(index_filepath, metadata)
    except IOError:
        # no metadata
        pass
    return results, err_msg, extraCmd

def processCollection(export_dir_path, content, parents=[]):
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
            # create a chapter.html file for first level only
            chapter_filename = 'chapter_%s.html' % id
            chapter_filepath = os.path.join(export_dir_path, chapter_filename)
            chapter_name = item['title']
            createChapterTitlePage(chapter_filepath, chapter_name)
            # add path of chapter_x.html to result list
            results.append(chapter_filepath)
        i += 1
        # build data for TOC
        numbering = '.'.join(parents + [str(i),])
        toc_str = '%s. %s' % (numbering, item['title'])
        toc_level = len(parents)
        tocs.append((toc_level, toc_str))
        if item['type'] == 'module':
            authors.update(item.get('authors', []))
            modules.append(item)
            # add path of index.html in each module into result list
            results.append(os.path.join(export_dir_path, item['id'], 'index.html'))
        else:
            data = processCollection(export_dir_path, item['content'], parents + [str(i),]) 
            results.extend(data[0])
            tocs.extend(data[1])
            authors.update(data[2])
            modules.extend(data[3])
    return results, tocs, authors, modules

def createTitlePage(filepath, title, editors=None, authors=None, url=None, version=None):
    html = u'<html><body><h1 class="collection-title %s">%s</h1>' % (authors and 'title2' or '', title)
    # insert editors
    if editors:
        html += u"""<div id="editors">
  <div class="by coll-by">Bi&#234;n t&#7853;p b&#7903;i:</div>"""
        for editor in editors:
            html += u'<div>%s</div>' % editor
        html += u'</div>'
    # insert authors
    if authors:
        html += u"""<div id="authors">
  <div class="by coll-by">C&#225;c t&#225;c gi&#7843;:</div>"""
        for author in authors:
            html += u'<div>%s</div>' % author
        html += u'</div>'
    # insert link
    if url:
        if version: url = '/'.join([url.rstrip('/'), version])
        html += u"""<div id="collection-link">
  <div>Phi&#234;n b&#7843;n tr&#7921;c tuy&#7871;n:</div>"""
        html += u'<div>{link} <a href="%s">%s</a></div>' % (url, url)
        html += u'</div>'
    # end html
    html += u'</body></html>'
    f = codecs.open(filepath, 'wb', 'utf-8')
    f.write(html)
    f.close()

def createChapterTitlePage(filepath, content):
    try:
        content = unicode(content, 'utf-8')
    except TypeError:
        pass
    html = '<html><body><h1 class="chapter-title">%s</h1></body></html>' % content.encode('ascii', 'xmlcharrefreplace')
    f = open(filepath, 'wb')
    f.write(html)
    f.close()

def createTOCPage(filepath, tocs):
    html = '<html><body><h1 id="menu">M&#7908;C L&#7908;C</h1><ul class="tocs">'
    for toc in tocs:
        toc_level = toc[0]
        toc_str = toc[1]
        try:
            toc_str = unicode(toc_str, 'utf-8')
        except TypeError:
            pass
        html += '<li class="level-%d">%s%s</li>' % (toc_level, '&nbsp;&nbsp;&nbsp;&nbsp;'*toc_level, toc_str.encode('ascii', 'xmlcharrefreplace'))
    html += '<li class="level-0">Tham gia &#273;&#243;ng g&#243;p</li></ul></body></html>'
    f = open(filepath, 'wb')
    f.write(html)
    f.close()

def createContributionPage(filepath, collection, modules):
    html = """<html><body>
  <h1 class="contrib-title">Tham gia &#273;&#243;ng g&#243;p</h1>
  <div class="coll-contrib">
    <div>T&#224;i li&#7879;u: %s</div>""" % collection['title']
    html += '<div>Bi&#234;n so&#7841;n b&#7903;i: '
    editors = ''
    for editor in collection.get('editors', []):
        editors += '%s, ' % editor
    html += editors.rstrip(', ') + '</div>'
    html += '<div>URL: %s/%s</div>' % (collection.get('url', ''), collection.get('version', ''))
    html += '<div>Gi&#7845;y ph&#233;p: %s</div>' % collection.get('license', '')
    for module in modules:
        html += '<div class="module-contrib">'
        html += '<div>Module: %s</div>' % module['title']
        html += '<div>T&#225;c gi&#7843;: '
        authors = ''
        for author in module.get('authors', []):
            authors += '%s, ' % author
        html += authors.rstrip(', ') + '</div>'
        html += '<div>URL: %s/%s</div>' % (module.get('url', ''), module.get('version', ''))
        html += '<div>Gi&#7845;y ph&#233;p: %s</div>' % module.get('license', '')
        html += '</div>'
    html += '</div>'
    html += '</body></html>'
    f = codecs.open(filepath, 'wb', 'utf-8')
    f.write(html)
    f.close()
    
def createHTMLHeader(filepath, left_text='', right_text=''):
    html = """
<html><body>
<table style="width:100%; color:grey; font-size:10pt;">
  <tr>
    <td>{0}</td>
    <td style="text-align:right">{1}</td>
  </tr>
</table>
</body></html>
""".format(left_text, right_text)
    f = open(filepath, 'wb')
    f.write(html)
    f.close()

def createHTMLFooter(filepath, left_text='', right_text=''):
    html = """
<html><head><script>
function subst() {
  var vars={};
  var x=document.location.search.substring(1).split('&');
  for (var i in x) {var z=x[i].split('=',2);vars[z[0]] = unescape(z[1]);}
  var x=['frompage','topage','page','webpage','section','subsection','subsubsection'];
  for (var i in x) {
    var y = document.getElementsByClassName(x[i]);
    for (var j=0; j<y.length; ++j) y[j].textContent = vars[x[i]];
  }
}
</script></head><body style="border:0; margin: 0;" onload="subst()">
<table style="width: 100%; color:grey; font-size:10pt;">
  <tr>
    <td>"""
    html += left_text
    html += """</td>
    <td style="text-align:right">
      <span class="page"></span> / <span class="topage"></span>
    </td>
  </tr>
</table>
</body></html>
"""
    f = open(filepath, 'wb')
    f.write(html)
    f.close()

def updateModuleHTML(filepath, metadata):
    f = codecs.open(filepath, 'r+', 'utf-8')
    content = f.read()
    f.seek(0)
    # insert module title and authors above content
    html = """<html><body>
<h1 class="module-title">%s</h1>
<div id="authors">
  <div class="by">B&#7903;i:</div>
""" % metadata['title']
    for author in metadata.get('authors', []):
        html += '<div>%s</div>' % author
    html += '</div>%s</body></html>' % content
    f.write(html)
    f.close()
