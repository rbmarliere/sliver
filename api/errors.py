from flask_restful import HTTPException


class InvalidArgument(HTTPException):
    code = 400

    def __init__(self, description=None, response=None):
        if description is None:
            description = "Missing required fields."
        self.description = description
        super(InvalidArgument, self).__init__(description, response)


class AuthenticationFailed(HTTPException):
    code = 401
    description = "User or password invalid."


class WrongPassword(HTTPException):
    code = 401
    description = "Old password does not match."


class CredentialExists(HTTPException):
    code = 400
    description = "Credential for this exchange already exists."


class CredentialDoesNotExist(HTTPException):
    code = 400
    description = "Credential does not exist."


class CredentialInvalid(HTTPException):
    code = 400
    description = "Credential is invalid."


class PositionDoesNotExist(HTTPException):
    code = 404
    description = "Position does not exist."


class StrategyDoesNotExist(HTTPException):
    code = 404
    description = "Strategy does not exist."


class StrategyNotEditable(HTTPException):
    code = 400
    description = "Unable to edit a strategy created by another user."


class StrategyIsActive(HTTPException):
    code = 400
    description = "Strategy has active users."


class ExchangeDoesNotExist(HTTPException):
    code = 404
    description = "Exchange does not exist."


class MarketAlreadySubscribed(HTTPException):
    code = 400
    description = "Can only subscribe to one strategy per market."


class EngineDoesNotExist(HTTPException):
    code = 404
    description = "Engine does not exist."


class EngineInUse(HTTPException):
    code = 400
    description = "Engine is in use."
