import os
import datetime
import shutil
import libxml2
import libxslt
import zipfile

from cStringIO import StringIO
from lxml import etree

from pyramid.view import view_config
from pyramid.response import Response

from rhaptos.cnxmlutils.odt2cnxml import transform
from rhaptos.cnxmlutils.xml2xhtml import transform_cnxml

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

    # validate file
    if fs is None:
        return Response('File Not Found', 404)
    if not hasattr(fs, 'filename'):
        return Response('File Error', 500)

    # TODO: validate mimetypes

    # TODO: validate file size

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
    # run openoffice command
    command = '/usr/bin/soffice --headless --nologo --nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + escape_system(original_filepath)[1:-1] + ',' + odt_filepath + ')"'
    os.system(command)

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
    cnxml_file = StringIO(cnxml)
    html_tree = transform_cnxml(cnxml_file)
    html = etree.tostring(html_tree)

    # produce zipfile
    ram = StringIO()
    zip_archive = zipfile.ZipFile(ram, 'w')
    zip_archive.writestr('index.vpxml', generateVPXML(filename, files.keys()))
    zip_archive.writestr(os.path.join('content', 'index.html'), html)
    for fname, fdata in files.items():
        zip_archive.writestr(os.path.join('content', fname), fdata)
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

