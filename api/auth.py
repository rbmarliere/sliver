import datetime

import flask_bcrypt
import flask_jwt_extended
import peewee
from flask_restful import Resource, reqparse

import core

argp = reqparse.RequestParser()
argp.add_argument("email")
argp.add_argument("password")


class Auth(Resource):

    def post(self):
        error = {"error": "email or password invalid"}, 401

        args = argp.parse_args()

        try:
            user = core.db.User.get(email=args.email)
        except peewee.DoesNotExist:
            return error

        authorized = flask_bcrypt.check_password_hash(user.password,
                                                      args.password)
        if not authorized:
            return error

        token = flask_jwt_extended.create_access_token(
            identity=str(user.id), expires_delta=datetime.timedelta(days=7))

        user.token = token
        user.save()

        return {"token": token}, 200
