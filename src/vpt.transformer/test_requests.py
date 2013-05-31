# required Requests library
import requests

if __name__ == '__main__':
    """
    Send HTTP POST requests to vpt apis to test.
    """
    host = 'dev.voer.vn'
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
    print r.text

    filename = 'test.zip'
    filedata = open('vpt/transformer/tests/test_files/C1.zip', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(export_url, files=files, data=payload)
    print '\nExporting ... \n'
    print r.status_code
