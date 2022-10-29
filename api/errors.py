from flask_restful import HTTPException


class Unauthorized(HTTPException):
    pass


dict = {
    "Unauthorized": {
        "message": "Invalid username or password",
        "status": 401
    }
}
