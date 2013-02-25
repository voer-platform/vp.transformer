import httplib, urllib, urllib2
import os
import itertools
import subprocess
import sys
import mimetools
import mimetypes
import socket
import time
import base64
from urllib2 import urlopen
#from keepalive import HTTPHandler
from cStringIO import StringIO
from multiprocessing import Process
import threading

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
        url = 'http://localhost:8080/converter/converted/document.' + output_type
        request= urllib2.Request(url, data=body)
        # Header to specify that the request contains multipart/form  data
        request.add_header('Content-type', multi_form.get_content_type())
        try:
            # Records the conversion time
            t1 = time.time()
            # Reads and writes converted data to a file
            response = urllib2.urlopen(request).read()
            result_file = open(output_file, 'w')
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
    

if __name__ == '__main__':
    argv = sys.argv
    output_types = ['odt', 'pdf', 'sxw', 'doc', 'rtf', 'txt', 'wiki']
    help_file = open('help.txt', 'r')
    help = help_file.read()
    #Batch conversion control logic
    #Example code is: #python convert.py '-b' "testbed directory"  "output_directory" 3 doc pdf
    if len(argv) == 7 and argv[1] == '-b':
        testbed_directory = argv[2]
        output_directory = argv[3] 
        if argv[4].isdigit():
            num_docs = int(argv[4]) 
        else:
            print help
            sys.exit()
        input_type = argv[5]
        output_type = argv[6]
       
        if output_type not in output_types or input_type not in output_types:
            print help
            sys.exit()
        converter = DocumentConverterClient()
        # Grabs all the documents listed in the directory. testbed_directory should refer to the testbed location of the google docs 
	#ls_output = subprocess.check_output(["ls", testbed_directory])
	ls_output = subprocess.Popen(['ls', testbed_directory], stdout=subprocess.PIPE).communicate()[0]
        # Splits all the filenames using new lines as the delimiter
        files_in_directory = ls_output.split('\n')
        # Gets the number of documents which will be useful for iterations
        total_num_docs = len(files_in_directory)
        num_iterations = num_docs 
        try:
            ps = [ ]
            #Starts the conversion of each document in separate processes
            for i in range(0, num_docs):
                converter = DocumentConverterClient()
                #To Do: Check that the file in the directory is actually of the input_type
                output_file = files_in_directory[i].split('.' + input_type)[0] + '.' + output_type
                input_file = testbed_directory + files_in_directory[i]
                output_file = output_directory + output_file
                p = Process(target=converter.convert, args=(input_file,output_type,output_file,))
                p.start()
                ps.append(p)
            # Joins on all the processes
            for p in ps:
                p.join()

        except IOError as io:
            print "File not found"
        except Exception as e:
                    print e
    # Conversion of a single file 
    # Example: python convert.py ~/foo  ~/outputdir doc pdf
    elif len(argv) == 5:
        input_file = argv[1]
        output_directory = argv[2]
        input_type = argv[3]
        output_type = argv[4] #'odt'
        if output_type not in output_types or input_type not in output_types:
            print help
            sys.exit()
        converter = DocumentConverterClient()
        #Gets the filename
        filename = input_file.split('/')
        filename = filename[len(filename) - 1]


        try:
            #Starts the conversion of the document
            converter = DocumentConverterClient()
            output_file = filename.split(input_type)[0] + output_type 
            output_file = output_directory + output_file
            #To Do: Check that the file is actually of the input_type
            p = Process(target=converter.convert, args=(input_file,output_type,output_file,))
            p.start()
            p.join()
        except IOError as io:
            print "File not found"
        except Exception as e:
                    print e

    elif len(argv) == 2 and argv[1] == '-help':
        print help
    else: 
        print help


