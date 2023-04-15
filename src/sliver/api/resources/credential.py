from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource, fields, marshal_with, reqparse

from sliver.api.exceptions import (
    CredentialDoesNotExist,
    CredentialExists,
    ExchangeDoesNotExist,
    InvalidArgument,
)
from sliver.credential import Credential as CredentialModel
from sliver.exchange import Exchange
from sliver.user import User

fields = {
    "exchange": fields.String,
    "exchange_id": fields.Integer,
    "api_key": fields.String,
    "active": fields.Boolean,
}


class Credential(Resource):
    @marshal_with(fields)
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        credentials = []
        for e in Exchange.select():
            cred = user.credential_set.where(
                CredentialModel.exchange == e
            ).get_or_none()

            if cred is None:
                cred = {
                    "exchange_id": e.id,
                    "exchange": e.name,
                    "api_key": "",
                    "active": False,
                }
            else:
                cred = {
                    "exchange_id": e.id,
                    "exchange": e.name,
                    "api_key": cred.api_key,
                    "active": cred.active,
                }

            credentials.append(cred)

        return credentials

    @marshal_with(fields)
    @jwt_required()
    def post(self):
        argp = reqparse.RequestParser()
        argp.add_argument("exchange_id", type=int, required=True)
        argp.add_argument("api_key", type=str, required=True)
        argp.add_argument("api_secret", type=str, required=True)
        argp.add_argument("api_password", type=str)
        argp.add_argument("active", type=bool, required=True)
        args = argp.parse_args()

        if not args.api_key or not args.api_secret:
            raise InvalidArgument

        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            exchange = Exchange.get_by_id(args.exchange_id)
        except Exchange.DoesNotExist:
            raise ExchangeDoesNotExist

        credential = user.get_exchange_credential(exchange).get_or_none()
        if credential:
            raise CredentialExists

        credential = CredentialModel(
            user=user,
            exchange=args.exchange_id,
            api_key=args.api_key,
            api_secret=args.api_secret,
            api_password=args.api_password,
            active=args.active,
        )

        credential.save()

        res = {
            "exchange": credential.exchange.name,
            "exchange_id": credential.exchange_id,
            "api_key": credential.api_key,
            "active": credential.active,
        }

        return res

    @marshal_with(fields)
    @jwt_required()
    def put(self):
        argp = reqparse.RequestParser()
        argp.add_argument("exchange_id", type=int, required=True)
        argp.add_argument("active", type=bool, required=True)
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            exchange = Exchange.get_by_id(args.exchange_id)
        except Exchange.DoesNotExist:
            raise ExchangeDoesNotExist

        credential = user.get_exchange_credential(exchange).get_or_none()
        if credential is None:
            raise CredentialDoesNotExist

        credential.active = args.active
        credential.save()

        res = {
            "exchange": credential.exchange.name,
            "exchange_id": credential.exchange_id,
            "api_key": credential.api_key,
            "active": credential.active,
        }

        return res

    @jwt_required()
    def delete(self):
        argp = reqparse.RequestParser()
        argp.add_argument("exchange_id", type=int, required=True)
        args = argp.parse_args()

        uid = int(get_jwt_identity())
        user = User.get_by_id(uid)

        try:
            exchange = Exchange.get_by_id(args.exchange_id)
        except Exchange.DoesNotExist:
            raise ExchangeDoesNotExist

        credential = user.get_exchange_credential(exchange).get_or_none()
        if credential is None:
            raise CredentialDoesNotExist

        credential.delete_instance()
        return "", 204
