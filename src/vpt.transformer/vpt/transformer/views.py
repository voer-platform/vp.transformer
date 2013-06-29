import os
import datetime
import subprocess
import shutil
import libxml2
import libxslt
import zipfile
import csv
import requests

from cStringIO import StringIO
from lxml import etree

from pyramid.view import view_config
from pyramid.response import Response

from rhaptos.cnxmlutils.odt2cnxml import transform
from rhaptos.cnxmlutils.xml2xhtml import transform_cnxml
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

import convert as JOD # Imports JOD convert script
from .models import VPTRoot

def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'

@view_config(context=VPTRoot, renderer='templates/home.pt')
def home_view(request):
    """
    Default homepage with help information.
    """
    return {'project': 'vpt.transformer'}

@view_config(context=VPTRoot, name='import')
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

    # save the original file so that we can convert, plus keep it.
    now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    original_filename = '%s-%s' % (now_string, fs.filename)
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

@view_config(context=VPTRoot, name='export')
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

    # save the original file so that we can convert, plus keep it.
    now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    original_filename = '%s-%s' % (now_string, fs.filename)
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
    input_file_paths = getInputFiles(export_dir_path)
    output_filename = '%s.pdf' % os.path.splitext(fs.filename)[0]
    output_file_path = os.path.join(export_dir_path, output_filename)
    strCmd = [pdfgen, '--footer-right', '[page] / [toPage]', '--footer-spacing', '1', '-q']
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
            chapters.txt
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
    # FIXED config filename
    config_filename = 'chapters.txt'
    config_filepath = os.path.join(export_dir_path, config_filename)
    try:
        with open(config_filepath, 'rb') as cf:
            reader = csv.reader(cf, delimiter=',', quotechar='"')
            for row in reader:
                # TODO: create a chapter.html file
                chapter_name = row[1]
                # add path of index.html in each module into result list
                results.append(os.path.join(export_dir_path, row[0], 'index.html'))
    except IOError:
        # it's a module -> return path to index.html only
        results.append(os.path.join(export_dir_path, 'index.html'))

    return results

