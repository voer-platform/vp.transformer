vp.transformer
==============

Installing the buildout
=======================

Install required packages.

    sudo apt-get install git-core libxslt1.1 libxslt1-dev python-dev python-virtualenv
    sudo apt-get install openoffice.org
    sudo apt-get install python-lxml python-libxslt1 python-imaging

Install virtualenv and run the buildout.

    git clone https://github.com/voer-platform/vp.transformer vpt-buildout
    cd vpt-buildout
    virtualenv --no-site-packages .
    ./bin/easy_install -U Distribute (optional, use it when got error running bootstrap below)
    ./bin/python bootstrap.py
    ./bin/buildout -Nv

Run the site.

    ./bin/paster serve src/vpt.transformer/vpt/development.ini --reload
    firefox http://localhost:6543/

Run tests.

    cd src/rhaptos.cnxmlutils/
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

Using the API
=============

Import
------

Send a POST request that contains the file to be import.

    POST $URL/import
    token = <your given token>
    cid = <your client id>
    file = <... binary data of your file here ...>

When imported successful, a zip file of html and images.

Example code in python:

    import requests

    host = 'localhost'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)

    token = '123456'
    cid = 'abc'
    payload = {'token': token, 'cid': cid}
    filename = 'test.doc'
    filedata = open('path/to/test.doc', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(import_url, files=files, data=payload)
    result = r.body