from celery.task import task

@task
def process_import(value):
    time.sleep(30)
    print 'processing import'
    return 'Import result'
