import httplib, urllib, urllib2
import os
import itertools
import sys
import mimetools
import mimetypes
import socket
import time
import base64
from urllib2 import urlopen
#from keepalive import HTTPHandler
from cStringIO import StringIO

'''
 This class definition was taken from http://www.doughellmann.com/PyMOTW/urllib2/#uploading-files. 
    It automates the creation of HTTP MIME messages 
'''
class MultiPartForm(object):
    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return
    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_file(self, fieldname, filename, file_handle, mimetype=None):
        """Add a file to be uploaded."""
        file_handle.seek(0)
        body = file_handle.read()
	#body = base64.b64encode(body)
	#body = body.decode('ISO_8859_1')
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary

         # Add the form fields
        parts.extend(
            [ part_boundary,
             'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )
         # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


class DocumentConverterClient:

    def convert(self, filename, output_type, output_file):
        # Sets the timeout for the socket. JOD has a default timeout
        timeout = 9000000
        socket.setdefaulttimeout(timeout)
        # Create the form with simple fields
        multi_form = MultiPartForm()
        # Adds the Document location and the output format
        file_handle = open(filename,  'rb')
        multi_form.add_file('inputDocument', filename, 
                file_handle)
        multi_form.add_field('outputFormat', output_type)
        body = str(multi_form)
        # Build the request
        # TODO: set the host as config variable
        url = 'http://localhost:8080/converter/converted/document.' + output_type
        request= urllib2.Request(url, data=body)
        # Header to specify that the request contains multipart/form  data
        request.add_header('Content-type', multi_form.get_content_type())
        try:
            # Records the conversion time
            t1 = time.time()
            # Reads and writes converted data to a file
            response = urllib2.urlopen(request).read()
            # oerpub use 'w' only, I fixed it with 'wb' - @vietdt
            result_file = open(output_file, 'wb')
            result_file.write(response)
            t2 = time.time()  
            print 'Conversion Successful! \nConversion took %0.3f ms' % ((t2-t1)*1000.0)
            return True
        except urllib2.HTTPError as e:
            t2 = time.time()
            print 'Conversion Unsuccessful \nConversion took %0.3f ms' % ((t2-t1)*1000.0)
            print e.code
            message = e.read()
            print message
            return False
    