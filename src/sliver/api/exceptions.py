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


class StrategyIsInactive(HTTPException):
    code = 400
    description = "Strategy is inactive."


class StrategyMixedIn(HTTPException):
    code = 400
    description = "Strategy is mixed in."


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


class OrderDoesNotExist(HTTPException):
    code = 404
    description = "Order does not exist."


class StrategyRefreshing(HTTPException):
    code = 500
    description = "Strategy is still refreshing."


class EngineNotEditable(HTTPException):
    code = 400
    description = "Unable to edit an engine created by another user."
