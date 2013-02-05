vp.transformer
==============

Installing the buildout
=======================

Install required packages.

    sudo apt-get install git-core libxslt1.1 libxslt1-dev python-dev python-virtualenv
    sudo apt-get install openoffice.org
    sudo apt-get install python-lxml python-libxslt1 python-imaging

You need to copy the macro file Module1.xba to your Libre-/OpenOffice config folder from

https://github.com/voer-platform/vp.transformer/tree/master/src/vpt.transformer

to this OpenOffice subfolder (xxxx = libre/open):

    .XXXXXXoffice/3/user/basic/Standard/.

Example:

    cp Module1.xba ~/.libreoffice/3/user/basic/Standard/.

Install virtualenv and run the buildout.

    git clone https://github.com/voer-platform/vp.transformer vpt-buildout
    cd vpt-buildout
    virtualenv --no-site-packages .
    ./bin/python bootstrap.py
    ./bin/buildout -Nv

Run the site.

    ./bin/paster serve src/vpt.transformer/vpt/development.ini --reload
    firefox http://localhost:6543/

Run tests.

    cd src/vpt.transformer/
    ../../bin/python setup.py develop
    ../../bin/python setup.py test -q

Using the API
=============

Import
------

Send a POST request that contains the file to be import.

    POST $URL/import
    file = <... binary data of your file here ...>

When imported successful, a zip file of VDP is returned.

Example code in python:

    import requests

    host = 'localhost'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)

    filename = 'test.doc'
    filedata = open('path/to/test.doc', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(import_url, files=files)
    result = r.body