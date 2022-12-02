from flask_restful import HTTPException


class InvalidArgument(HTTPException):
    code = 400
    description = (
        "Missing required fields."
    )


class AuthenticationFailed(HTTPException):
    code = 401
    description = (
        "User or password invalid."
    )


class WrongPassword(HTTPException):
    code = 401
    description = (
        "Old password does not match."
    )


class CredentialExists(HTTPException):
    code = 400
    description = (
        "Credential for this exchange already exists."
    )


class PositionDoesNotExist(HTTPException):
    code = 404
    description = (
        "Position does not exist."
    )


class StrategyDoesNotExist(HTTPException):
    code = 404
    description = (
        "Strategy does not exist."
    )


class StrategyNotEditable(HTTPException):
    code = 400
    description = (
        "Unable to edit a strategy created by another user."
    )
