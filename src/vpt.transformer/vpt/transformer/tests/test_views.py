import os
import cgi
import unittest

from pyramid import testing

from vpt.transformer.views import home_view
from vpt.transformer.views import import_view

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_home_view(self):
        request = testing.DummyRequest()
        info = home_view(request)
        self.assertEqual(info['project'], 'vpt.transformer')

    def test_import_view(self):
        current_path = os.path.abspath(os.path.dirname(__file__))
        parent_path = os.path.abspath(os.path.dirname(current_path))
        # get test file
        fp = open('%s/test_files/C1.doc' % current_path , 'rb')
        data = fp.read()
        # make FieldStorage for POST request
        fs = cgi.FieldStorage()
        fs.name = 'file'
        fs.filename = 'C1.doc'
        fs.file = fs.make_file()
        fs.file.write(data)
        fs.file.seek(0)
        # generate test request
        token = '123'
        cid = 'abc'
        request = testing.DummyRequest(post={'file': fs, 'token': token, 'cid': cid})
        # FIXME - manually add transform_dir to settings
        request.registry.settings['transform_dir'] = '%s/transforms' % parent_path
        # run the view and get response
        response = import_view(request)
        self.assertEqual(response.status_code, 200)
