import os
import cgi
import unittest

from pyramid import testing


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_home_view(self):
        from vpt.transformer.views import home_view
        request = testing.DummyRequest()
        info = home_view(request)
        self.assertEqual(info['project'], 'vpt.transformer')

    def test_import_view(self):
        from vpt.transformer.views import import_view
        pkg_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        # get test file
        fp = open('%s/tests/test_files/C1.doc' % pkg_path , 'rb')
        data = fp.read()
        # make FieldStorage for POST request
        fs = cgi.FieldStorage()
        fs.name = 'file'
        fs.filename = 'views.py'
        fs.file = fs.make_file()
        fs.file.write(data)
        fs.file.seek(0)
        # generate test request
        request = testing.DummyRequest(post={'file': fs})
        # FIXME - manually add transform_dir to settings
        request.registry.settings['transform_dir'] = '%s/transforms' % pkg_path
        # run the view and get response
        response = import_view(request)
        self.assertEqual(response.status_code, 200)
