from flask_restful import HTTPException


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
    code = 204
    description = (
        "Credential for this exchange already exists."
    )


class CredentialDoesNotExist(HTTPException):
    code = 404
    description = (
        "Credential for this exchange does not exist."
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
