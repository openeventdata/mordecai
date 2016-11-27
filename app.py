from flask import Flask
from flask_restful import Api
from resources import utilities
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
#from resources.osc import OscAPI
from resources.places import PlacesAPI
from resources.country import CountryAPI
from resources.easter_egg import EasterEgg

app = Flask(__name__)
api = Api(app)


if __name__ == '__main__':
    print 'Starting up the service.'
    args = utilities.parse_args()
    configs = utilities.get_configs(args)

    print 'Setting up MITIE.'
    ner_model = utilities.setup_mitie(configs['mitie_directory'],
                                      configs['mitie_ner_model'])

    print 'Setting up Word2Vec.'
    location = os.path.realpath(os.path.join(os.getcwd(),
                                                 os.path.dirname(__file__)))
    w2v_data = utilities.setup_w2v(configs['word2vec_model'],
                                   location + '/resources/stopword_country_names.json')

    print 'Setting up Elasticsearch connection.'
    es_conn = utilities.setup_es(configs['es_host'], configs['es_port'])

    #api.add_resource(OscAPI, '/osc')
    api.add_resource(PlacesAPI, '/places', resource_class_kwargs={'ner_model': ner_model,
                                                                  'es_conn': es_conn})
    api.add_resource(CountryAPI, '/country', resource_class_kwargs={'ner_model': ner_model,
                                                                    'index': w2v_data['index'],
                                                                    'vocab_set': w2v_data['vocab_set'],
                                                                    'prebuilt': w2v_data['prebuilt'],
                                                                    'idx_country_mapping': w2v_data['idx_country_mapping']})
    api.add_resource(EasterEgg, '/easter_egg')

    print 'Starting server.'
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(configs['mordecai_port'])
    IOLoop.instance().start()
