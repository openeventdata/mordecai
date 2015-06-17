from flask import Flask
from flask_restful import Api
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from mordecai.resources.osc import OscAPI
from mordecai.resources.locate import EasterEgg
from mordecai.resources.places import PlacesAPI
from mordecai.resources.country import CountryAPI
from mordecai.resources.easter_egg import LocateAPI

app = Flask(__name__)
api = Api(app)

api.add_resource(OscAPI, '/osc')
api.add_resource(PlacesAPI, '/places')
api.add_resource(CountryAPI, '/country')
api.add_resource(LocateAPI, '/locate')
api.add_resource(EasterEgg, '/easter_egg')


if __name__ == '__main__':
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)
    IOLoop.instance().start()
