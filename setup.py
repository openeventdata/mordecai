from setuptools import setup

setup(name='mordecai',
      version='2.0.0a6',
      description='Full text geoparsing and event geocoding',
      url='http://github.com/openeventdata/mordecai/',
      author='Andy Halterman',
      author_email='ahalterman0@gmail.com',
      license='MIT',
      packages=['mordecai'],
      keywords = ['geoparsing', 'nlp', 'geocoding', 'toponym resolution'],
      install_requires = ['editdistance>=0.3.1',
                          'elasticsearch==5.4.0',
                          'elasticsearch-dsl==5.3.0',
                          'h5py>=2.6.0',
                          'Keras>=2.0.8',
                          'pandas>=0.19.2',
                          'spacy>=2.0.3',
                          'tensorflow>=1.3.0',
                          'numpy>=1.12',
                          'urllib3>=1.22'],
      dependency_links=['https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-2.0.0/en_core_web_lg-2.0.0.tar.gz'],
      include_package_data=True,
      package_data = {'data': ['admin1CodesASCII.json',
                             'countries.json',
                             'nat_df.csv',
                             'stopword_country_names.json'],
                    'models' : ['country_model.h5',
                                'rank_model.h5']}
     )
