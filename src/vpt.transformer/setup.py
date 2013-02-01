import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'pyramid_zodbconn',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'lxml',
    'libxml2-python',
    'ZODB3',
    'waitress',
    'requests',
    'rhaptos.cnxmlutils'
    ]

setup(name='vpt.transformer',
      version='0.0',
      description='VOER Platform - Transformer',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="vpt.transformer",
      entry_points="""\
      [paste.app_factory]
      main = vpt.transformer:main
      """,
      )
