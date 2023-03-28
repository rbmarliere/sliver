import flask_bcrypt
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse

from sliver.api.exceptions import WrongPassword
from sliver.user import User as UserModel

fields = {
    "email": fields.String,
    "max_risk": fields.Float,
    "cash_reserve": fields.Float,
    "telegram_username": fields.String,
}

argp = reqparse.RequestParser()
argp.add_argument("old_password", type=str)
argp.add_argument("password", type=str)
argp.add_argument("telegram_username", type=str)
argp.add_argument("max_risk", type=float)
argp.add_argument("cash_reserve", type=float)


class User(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = UserModel.get_by_id(uid)

        return user

    @marshal_with(fields)
    @jwt_required()
    def put(self):
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = UserModel.get_by_id(uid)

        if args.password and args.old_password:
            authorized = flask_bcrypt.check_password_hash(
                user.password, args.old_password
            )
            if authorized:
                user.password = flask_bcrypt.generate_password_hash(args.password)
            else:
                raise WrongPassword

        if args.telegram_username:
            user.telegram_username = args.telegram_username
            user.telegram_chat_id = None

        if args.max_risk:
            user.max_risk = args.max_risk

        if args.cash_reserve:
            user.cash_reserve = args.cash_reserve

        user.save()

        return user
