from flask import Flask
from flask_restful import Api
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
#from resources.osc import OscAPI
from resources.places import PlacesAPI
from resources.country import CountryAPI
from resources.easter_egg import EasterEgg

app = Flask(__name__)
api = Api(app)

#api.add_resource(OscAPI, '/osc')
api.add_resource(PlacesAPI, '/places')
api.add_resource(CountryAPI, '/country')
api.add_resource(EasterEgg, '/easter_egg')


if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)
    IOLoop.instance().start()
