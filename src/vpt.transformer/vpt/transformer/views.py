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

    # validate inputs
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

    # convert from other office format to odt
    filename, extension = os.path.splitext(original_filename)
    odt_filename = '%s.odt' % filename
    odt_filepath = str(os.path.join(save_dir_path, odt_filename))
    # run jod service
    converter = JOD.DocumentConverterClient()
    try:
        converter.convert(original_filepath, 'odt', odt_filepath)
    except Exception as e:
        print e

    # check file existed
    try:
        fp = open(odt_filepath, 'r')
        fp.close()
    except IOError as io:
        # TODO: raise exception
        return Response('Conversion Error', 500)

    # convert to cnxml
    tree, files, errors = transform(odt_filepath)
    cnxml = clean_cnxml(etree.tostring(tree))

    # convert to html
    html = cnxml_to_htmlpreview(cnxml)

    # produce zipfile
    ram = StringIO()
    zip_archive = zipfile.ZipFile(ram, 'w')
    # uncomment this if you need a vpxml
    #zip_archive.writestr('index.vpxml', generateVPXML(filename, files.keys()))
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

    return Response(content_type='application/octet-stream', body=ram.getvalue())

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
            # processing the collection title
            title = collection['title']
            title_filepath = os.path.join(export_dir_path, 'title.html')
            createTitlePage(title_filepath, title)
            # add path of title.html into result list
            results.append(title_filepath)
            data = processCollection(export_dir_path, collection['content'])
            results.extend(data[0])
            tocs = data[1]
            tocs.sort(key=lambda toc: toc[1])
            # create a toc.html file
            toc_filename = 'toc.html'
            toc_filepath = os.path.join(export_dir_path, toc_filename)
            createTOCPage(toc_filepath, tocs)
            results.insert(1, toc_filepath)
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
            createTitlePage(chapter_filepath, chapter_name)
            # add path of chapter_x.html to result list
            results.append(chapter_filepath)
        i += 1
        # build data for TOC
        numbering = '.'.join(parents + [str(i),])
        toc_str = '%s. %s' % (numbering, item['title'])
        toc_level = len(parents)
        tocs.append((toc_level, toc_str))
        if item['type'] == 'module':
            # add path of index.html in each module into result list
            results.append(os.path.join(export_dir_path, item['id'], 'index.html'))
        else:
            data = processCollection(export_dir_path, item['content'], parents + [str(i),]) 
            results.extend(data[0])
            tocs.extend(data[1])
    return results, tocs

def createTitlePage(filepath, content):
    try:
        content = unicode(content, 'utf-8')
    except TypeError:
        pass
    html = '<html><body><center><h1 style="margin-top:250px">%s</h1></center></body></html>' % content.encode('ascii', 'xmlcharrefreplace')
    f = open(filepath, 'wb')
    f.write(html)
    f.close()

def createTOCPage(filepath, tocs):
    html = '<html><body><p><b>Table of Contents:</b></p><ul style="list-style-type: none;">'
    for toc in tocs:
        toc_level = toc[0]
        toc_str = toc[1]
        try:
            toc_str = unicode(toc_str, 'utf-8')
        except TypeError:
            pass
        html += '<li>%s%s</li>' % ('&nbsp;&nbsp;&nbsp;&nbsp;'*toc_level, toc_str.encode('ascii', 'xmlcharrefreplace'))
    html += '</ul></body></html>'
    f = open(filepath, 'wb')
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
  <p>B&#7903;i:</p>
""" % metadata['title']
    for author in metadata.get('authors', []):
        html += '<p>%s</p>' % author
    html += '</div>%s</body></html>' % content
    f.write(html)
    f.close()
