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
import webob
from webob import exc

from cornice import Service

from rhaptos.cnxmlutils.odt2cnxml import transform
from rhaptos.cnxmlutils.xml2xhtml import transform_cnxml
from oerpub.rhaptoslabs.cnxml2htmlpreview.cnxml2htmlpreview import cnxml_to_htmlpreview

import convert as JOD # Imports JOD convert script
from .tasks import process_import, process_export
from .no_accent_vietnamese_unicodedata import no_accent_vietnamese

class HTTPError(exc.HTTPError):
    def __init__(self, status, msg, traceback=''):
        body = {'status': status, 'message': msg}
        if traceback: body['error'] = traceback
        webob.Response.__init__(self, json.dumps(body))
        self.status = status
        self.content_type = 'application/json'

def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'

@view_config(route_name='home', renderer='templates/home.pt')
def home_view(request):
    """
    Default homepage with help information.
    """
    return {'project': 'vpt.transformer'}

imp = Service(name='import', path='/import',
                 description="Convert doc to html")
@imp.get()
@imp.post()
def import_view(request):
    # get input file from request
    fs = request.POST.get('file')
    # get token and client id from request
    token = request.POST.get('token')
    cid = request.POST.get('cid')
    # get celery task id from request
    task_id = request.params.get('task_id')

    if task_id:
        # check the status of celery task
        result = process_import.AsyncResult(task_id)
        # get the status
        status = result.status
        if result.successful():
            # get the result of the task (an download url)
            return {'status': status, 'url': result.get()}
        elif result.failed():
            # running task got error
            raise HTTPError(500, 'Conversion Error', result.traceback)
        return {'status': status}
    else:
        # validate inputs
        error = validate_inputs(fs, token, cid)
        if error is not None:
            raise HTTPError(error[1], error[0])
    
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

        # get the filename without extension
        filename, extension = os.path.splitext(original_filename)

        # generate the expected download url of converted file
        download_url = request.static_url('transforms/%s.zip' % filename)

    	# call celery task
    	result = process_import.delay(save_dir_path, original_filepath, filename, download_url)
    	return {'status': result.status, 'task_id': result.task_id}

exp = Service(name='export', path='/export',
                 description="Convert zipped html to pdf")
@exp.get()
@exp.post()
def export_view(request):
    # get input file from request
    fs = request.POST.get('file')
    # get export type
    output_type = request.POST.get('output')
    # get token and client id from request
    token = request.POST.get('token')
    cid = request.POST.get('cid')
    # get celery task id from request
    task_id = request.params.get('task_id')

    if task_id:
        # check the status of celery task
        result = process_export.AsyncResult(task_id)
        # get the status
        status = result.status
        if result.successful():
            # get the result of the task (an download url)
            return {'status': status, 'url': result.get()}
        elif result.failed():
            # running task got error
            raise HTTPError(500, 'Export Error', result.traceback)
        return {'status': status}
    else:
        # validate inputs
        error = validate_inputs(fs, token, cid)
        if error is not None:
            raise HTTPError(error[1], error[0])

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

        output_filename = '%s.pdf' % os.path.splitext(fs_filename)[0]
        output_file_path = os.path.join(export_dir_path, output_filename)

        # generate the expected download url of converted file
        download_url = request.static_url('transforms/%s/%s' % (filename, output_filename))

        # call celery task
        result = process_export.delay(save_dir_path, export_dir_path, output_file_path, download_url)
        return {'status': result.status, 'task_id': result.task_id}

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
