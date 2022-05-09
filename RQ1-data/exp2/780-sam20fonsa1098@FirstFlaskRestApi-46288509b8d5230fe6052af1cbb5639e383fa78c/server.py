from datetime import timedelta
from flask import Flask
from flask_restful import Api
from flask_jwt import JWT
from resources.item import Item
from resources.item_list import ItemList
from resources.users_register import UserRegister
from resources.store import Store
from resources.store_list import StoreList
from auth.auth import authenticate, identity

server = Flask(__name__)
server.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/data.db'
server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
server.secret_key = 'secret_key'
server.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=3600)

jwt = JWT(server, authenticate, identity)

api = Api(server)
api.add_resource(Item, '/item/<string:name>')
api.add_resource(ItemList, '/items')
api.add_resource(Store, '/store/<string:name>')
api.add_resource(StoreList, '/stores')
api.add_resource(UserRegister, '/signup')


@server.before_first_request
def create_tables():
    db.create_all()


if __name__ == '__main__':
    from data.db import db
    db.init_app(server)
    server.run(port=3333, debug=True)