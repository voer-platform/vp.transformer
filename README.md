vp.transformer
==============

Installing the buildout
=======================

Install required packages.

    sudo apt-get install git-core libxslt1.1 libxslt1-dev python-dev python-virtualenv
    sudo apt-get install openoffice.org
    sudo apt-get install python-lxml python-libxslt1 python-imaging
    # for rhaptos.cnxmlutils. we should avoid it later
    sudo apt-get install tidy libtidy-0.99-0

Install virtualenv and run the buildout.

    git clone https://github.com/voer-platform/vp.transformer vpt-buildout
    cd vpt-buildout
    virtualenv --no-site-packages .
    ./bin/easy_install -U Distribute (optional, use it when got error running bootstrap below)
    ./bin/python bootstrap.py
    ./bin/buildout -Nv

Run the site.

    ./bin/paster serve src/vpt.transformer/vpt/development.ini --daemon
    firefox http://localhost:6543/

Run tests.

    cd src/rhaptos.cnxmlutils/
    ../../bin/python setup.py install

    cd src/oerpub.rhaptoslabs.cnxml2htmlpreview/
    ../../bin/python setup.py install

    cd src/vpt.transformer/
    ../../bin/python setup.py develop
    ../../bin/python setup.py test -q

Installing jodconverter with tomcat
===================================

First run soffice in headless mode. Note: run as root

    # soffice --headless --accept="socket,host=127.0.0.1,port=8100;urp;" --nofirststartwizard &

Download the jodconverter-tomcat-2.2.2.zip and unzip.
Set JRE_HOME to your jre installed location e.g.

    $ export JRE_HOME=/usr/lib/jvm/default-java

Start tomcat.

    $ cd jodconverter-tomcat-2.2.2/
    $ sudo -E ./bin/startup.sh

JODConverter will be available at the following URL http://localhost:8080/converter/


Install wkhtmltopdf for pdf export
==================================

Choose a static binary relevant for your environment here: http://code.google.com/p/wkhtmltopdf/downloads/list

    $ wget http://wkhtmltopdf.googlecode.com/files/wkhtmltopdf-0.9.9-static-amd64.tar.bz2

Link to run.

    $ tar xvf wkhtmltopdf-0.9.9-static-amd64.tar.bz2
    $ sudo cp wkhtmltopdf-amd64 /usr/bin/
    $ sudo ln -s /usr/bin/wkhtmltopdf-amd64 /usr/bin/wkhtmltopdf

Test command line.

    $ wkhtmltopdf index.html index.pdf

If there's any problem, you may have to compile your self. see: http://code.google.com/p/wkhtmltopdf/wiki/compilation


Using the API
=============

Send a POST request that contains the file to be import/export.

    POST $URL/[import|export]
    token = <your given token>
    cid = <your client id>
    file = <... binary data of your file here ...>

The response of POST request will return a json with task_id information which you can use to ping for import/export status. Example of returned json:

    HTTP/1.1 200 OK
    {'status': 'PENDING', 'task_id': 'e35c4124-b0e3-4d15-93de-802a88d9effc'}

To ping for import/export status, send a GET request as follow.

    GET $URL/[import/export]?task_id=<task_id>

If conversion is still in process, it will return a json with PENDING status only.
    
    HTTP/1.1 200 OK
    {"status": "PENDING"}

When imported/exported successful, returned json will contained an URL to the output file (compressed html and images for import or pdf for export).

    HTTP/1.1 200 OK
    {"status": "SUCCESS", "url": "http://localhost:6543/transforms/20131010-171144-test.zip"}

When imported/exported failed, it will return a HTTP 500 Response and may contain a full traceback of the error.

    HTTP/1.1 500
    {"status": 500, "message": "Conversion Error", "error": <full traceback>}

Example code in python:

    import requests
    import json

    host = 'localhost'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)
    export_url = 'http://%s:%s/export' % (host, port)

    token = 'a9af1d6ca60243a38eb7d52dd344f7cb'
    cid = 'vietdt'
    payload = {'token': token, 'cid': cid}

    # test import
    filename = 'test.doc'
    filedata = open('vpt/transformer/tests/test_files/C1.doc', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(import_url, files=files, data=payload)
    result = json.loads(r.text)
    print 'Importing ... \n'
    print r.text

    # ping import status
    if result.has_key('task_id')
    r = requests.get(import_url+'?task_id='+result['task_id'])
    result = json.loads(r.text)
    if result.has_key('url'):
        print result['url']
    elif r.status_code != 200:
        print result.get('message')
        print result.get('error')

    # test export
    filename = 'test.zip'
    filedata = open('vpt/transformer/tests/test_files/C1.zip', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(export_url, files=files, data=payload)
    print '\nExporting ... \n'
    print r.status_code

Cleaner
=======
Cleaner is used to cleaned temporatory files and directories used in vpt-transformer

Config crontab
--------------
Config crontab to schedule cleaner: Setup time for schedule cleaning, path to python and script file.

    sudo crontab -e


Example code to put in crontab config file. This code will run the cleaner every one minute.

    */1 * * * * /usr/bin/python /home/vietvd/VPT/ /home/vietvd/VPT/vpt-buildout/src/vpt.transformer/vpt/transformer/cleaner.py
