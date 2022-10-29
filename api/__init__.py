import os

import flask
import flask_cors
import flask_jwt_extended
import flask_restful
import waitress

from . import errors, routes

app = flask.Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

flask_cors.CORS(app)

api = flask_restful.Api(app, prefix="/v1", errors=errors.dict)
routes.init(api)

jwt = flask_jwt_extended.JWTManager(app)


def serve():
    env = os.environ.get("ENV_NAME")

    print("env set to '" + env + "'")

    if env == "development":
        app.run(debug=True, port=5000)
    elif env == "production":
        waitress.serve(app, port=5000)
    else:
        print("possible values are 'development' or 'production', exiting...")
