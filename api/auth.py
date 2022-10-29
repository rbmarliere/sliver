import datetime

import flask_bcrypt
import flask_jwt_extended
import peewee
from flask_restful import Resource, reqparse

import api.errors
import core

argp = reqparse.RequestParser()
argp.add_argument("email")
argp.add_argument("password")


class Auth(Resource):

    def post(self):
        args = argp.parse_args()

        try:
            user = core.db.User.get(email=args.email)
        except peewee.DoesNotExist:
            raise api.errors.Unauthorized

        authorized = flask_bcrypt.check_password_hash(user.password,
                                                      args.password)

        if not authorized:
            raise api.errors.Unauthorized

        delta = datetime.timedelta(days=1)
        exp_at = datetime.datetime.now() + delta
        token = flask_jwt_extended.create_access_token(
            identity=str(user.id), expires_delta=delta)

        user.token = token
        user.save()

        res = {"access_key": token, "expires_at": int(exp_at.timestamp())}

        return (res, 200)
