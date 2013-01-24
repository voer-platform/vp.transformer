# required Requests library
import requests

if __name__ == '__main__':
    """
    Send HTTP POST requests to vpt apis to test.
    """
    host = 'localhost'
    port = '6543'
    import_url = 'http://%s:%s/import' % (host, port)

    files = {'file': ('report.csv', 'some,data,to,send\nanother,row,to,send\n')}
    r = requests.post(import_url, files=files)
    print r.text