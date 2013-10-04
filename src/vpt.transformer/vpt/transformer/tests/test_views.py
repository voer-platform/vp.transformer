import os
import cgi
import unittest

from pyramid import testing

from vpt.transformer.views import home_view
from vpt.transformer.views import import_view
from vpt.transformer.views import export_view

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.config.add_static_view('transforms', path='vpt.transformer:transforms')

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
        fs.filename = 'C1-test.doc'
        fs.file = fs.make_file()
        fs.file.write(data)
        fs.file.seek(0)
        # generate test request
        token = 'fc9eb9f9bad077998efcf1aae3049286'
        cid = 'vietdt'
        request = testing.DummyRequest(post={'file': fs, 'token': token, 'cid': cid})
        # FIXME - manually add transform_dir to settings
        request.registry.settings['transform_dir'] = '%s/transforms' % parent_path
        # run the view and get response
        response = import_view(request)
        self.assertEqual(response.status_code, 200)

#    def export_view(self, test_filename='C1.zip'):
    def test_export_view(self, test_filename='C1.zip'):
        current_path = os.path.abspath(os.path.dirname(__file__))
        parent_path = os.path.abspath(os.path.dirname(current_path))
        # get test file
        fp = open('%s/test_files/%s' % (current_path, test_filename), 'rb')
        data = fp.read()
        # make FieldStorage for POST request
        fs = cgi.FieldStorage()
        fs.name = 'file'
        fs.filename = test_filename
        fs.file = fs.make_file()
        fs.file.write(data)
        fs.file.seek(0)
        # generate test request
        token = 'a9af1d6ca60243a38eb7d52dd344f7cb'
        cid = 'vietdt'
        request = testing.DummyRequest(post={'file': fs, 'token': token, 'cid': cid})
        # FIXME - manually add transform_dir to settings
        request.registry.settings['transform_dir'] = '%s/transforms' % parent_path
        # run the view and get response
        response = export_view(request)
        self.assertEqual(response.status_code, 200)

    def test_export_colletion(self):
    	self.test_export_view(test_filename='collection.zip')
#    	self.export_view(test_filename='collection.zip')

