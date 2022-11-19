import os

import flask
import flask_cors
import flask_jwt_extended
import flask_restful
import waitress

import core

from . import routes

app = flask.Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

flask_cors.CORS(app)

api = flask_restful.Api(app, prefix="/v1", catch_all_404s=True)
routes.init(api)

jwt = flask_jwt_extended.JWTManager(app)


def serve():
    core.watchdog.set_logger("api")

    if core.config["HYPNOX_ENV_NAME"] == "development":
        app.run(debug=True, port=5000)
    elif core.config["HYPNOX_ENV_NAME"] == "production":
        waitress.serve(app, port=5000)
