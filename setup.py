from setuptools import setup

setup(name='nano_api',
      version='0.1',
      description='Custom and simple API utils to be used in conjunction with Flask and Flask-Restful',
      url='http://github.com/merfrei/nano_api',
      author='Emiliano M. Rudenick',
      author_email='emr.frei@gmail.com',
      license='MIT',
      packages=['flask_api', 'flask_serializer'],
      install_requires=[
          'flask',
          'flask-restful',
      ],
      zip_safe=False)
