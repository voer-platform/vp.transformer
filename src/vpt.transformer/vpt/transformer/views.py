import os
import datetime
import shutil

from pyramid.view import view_config
from pyramid.response import Response

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
    import pdb; pdb.set_trace()

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
    upload_dir_path = os.path.join(
        request.registry.settings['transform_dir'],
        'upload'
        )
    download_dir_path = os.path.join(
        request.registry.settings['transform_dir'],
        'download'
        )

    # save the original file so that we can convert, plus keep it.
    now_string = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    original_filename = '%s-%s' % (now_string, fs.filename)
    original_filepath = str(os.path.join(upload_dir_path, original_filename))
    saved_file = open(original_filepath, 'wb')
    input_file = fs.file
    shutil.copyfileobj(input_file, saved_file)
    saved_file.close()
    input_file.close()

    # convert from other office format to odt
    filename, extension = os.path.splitext(original_filename)
    odt_filename = '%s.odt' % filename
    odt_filepath = str(os.path.join(download_dir_path, odt_filename))
    # run openoffice command
    command = '/usr/bin/soffice --headless --nologo --nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + escape_system(original_filepath)[1:-1] + ',' + odt_filename + ')"'
    #command = 'cp ' + original_filepath + ' ' + odt_filepath
    os.system(command)

    # check file existed
    try:
        fp = open(odt_filepath, 'r')
        fp.close()
    except IOError as io:
        # TODO: raise exception
        return Response('Conversion Error', 500)

    return Response(odt_filepath)