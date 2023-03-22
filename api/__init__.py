import os

import flask
import flask_cors
import flask_jwt_extended
import flask_restful

import core
from . import routes


app = flask.Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
app.config["BUNDLE_ERRORS"] = True
app.config["PROPAGATE_EXCEPTIONS"] = True

flask_cors.CORS(app)

api = flask_restful.Api(app, prefix="/v1", catch_all_404s=True)
routes.init(api)

jwt = flask_jwt_extended.JWTManager(app)

core.watchdog.Watchdog(log="api")
