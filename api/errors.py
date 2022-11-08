from flask_restful import HTTPException


class AuthenticationFailed(HTTPException):
    code = 401
    description = (
        "User or password invalid."
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


class PositionNotFound(HTTPException):
    code = 404
    description = (
        "Position not found."
    )
