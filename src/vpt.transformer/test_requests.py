# required Requests library
import requests

if __name__ == '__main__':
    """
    Send HTTP POST requests to vpt apis to test.
    """
    host = 'dev.voer.vn'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)

    token = 'd7851542aa207f1eef5c5da2149a9c06'
    cid = 'vpweb'
    payload = {'token': token, 'cid': cid}
    filename = 'test.doc'
    filedata = open('vpt/transformer/tests/test_files/C1.doc', 'rb').read()
    files = {'file': (filename, filedata)}
    r = requests.post(import_url, files=files, data=payload)
    print r.status_code