from setuptools import setup

setup(name='mordecai',
      version='2.0.0a2',
      description='Full text geoparsing and event geocoding',
      url='http://github.com/openeventdata/mordecai/',
      author='Andy Halterman',
      author_email='ahalterman0@gmail.com',
      license='MIT',
      packages=['mordecai'],
      keywords = ['geoparsing', 'nlp', 'geocoding', 'toponym resolution'],
      include_package_data=True,
      package_data = {'data': ['admin1CodesASCII.json',
                             'countries.json',
                             'nat_df.csv',
                             'stopword_country_names.json'],
                    'models' : ['country_model.h5',
                                'rank_model.h5']}
     )
