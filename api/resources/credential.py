from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse

import api.errors
import core

fields = {
    "exchange_id": fields.Integer,
    "api_key": fields.String,
}


argp = reqparse.RequestParser()
argp.add_argument("api_key", type=str)
argp.add_argument("api_secret", type=str)


class Credentials(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        credentials = []
        for e in core.db.Exchange.select():
            cred = user.credential_set.where(
                core.db.Credential.exchange == e).get_or_none()
            if cred is None:
                cred = {
                    "exchange_id": e.id,
                    "api_key": ''
                }
            credentials.append(cred)

        return credentials


class Credential(Resource):
    @marshal_with(fields)
    @jwt_required()
    def post(self, exchange_id):
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)
        credential = user.get_credential_by_exchange(exchange_id)
        if credential:
            raise api.errors.CredentialExists

        credential = core.db.Credential(
            user=user,
            exchange=exchange_id,
            api_key=args.api_key,
            api_secret=args.api_secret)
        credential.save()

        return credential

    @jwt_required()
    def delete(self, exchange_id):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        try:
            credential = user.get_credential_by_exchange(exchange_id)
        except core.db.Credential.DoesNotExist:
            raise api.errors.CredentialDoesNotExist

        credential.delete_instance()
        return "", 204
