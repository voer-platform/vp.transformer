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

Import
------

Send a POST request that contains the file to be import.

    POST $URL/import
    token = <your given token>
    cid = <your client id>
    file = <... binary data of your file here ...>

When imported successful, it returns a zip file of html and images.

Export
------

Send a POST request that contains the input file to be export.

    POST $URL/export
    token = <your given token>
    cid = <your client id>
    output = <your expected output type e.g. pdf>
    file = <... binary data of your file here ...>

When exported successful, it returns a file of your expected output (only pdf now supported).

Example code in python:

    import requests

    host = 'localhost'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)
    export_url = 'http://%s:%s/export' % (host, port)

    token = 'a9af1d6ca60243a38eb7d52dd344f7cb'
    cid = 'vietdt'
    payload = {'token': token, 'cid': cid}

    filename = 'test.doc'
    filedata = open('vpt/transformer/tests/test_files/C1.doc', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(import_url, files=files, data=payload)
    print 'Importing ... \n'
    print r.status_code

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
