from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with

import core

fields = {"description": fields.String}


class Strategy(Resource):

    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = get_jwt_identity()

        strategies = [
            st for st in core.db.User.get(uid).get_strategies().dicts()
        ]

        return strategies

    def post(self):
        pass

    def put(self):
        pass

    def delete(self):
        pass
