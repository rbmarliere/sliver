import flask
import flask_cors
import flask_jwt_extended
import flask_restful

from sliver.config import Config

from . import routes

app = flask.Flask("sliver_api")
app.config["JWT_SECRET_KEY"] = Config().JWT_SECRET_KEY
app.config["BUNDLE_ERRORS"] = True
app.config["PROPAGATE_EXCEPTIONS"] = True

flask_cors.CORS(app)
flask_jwt_extended.JWTManager(app)

api = flask_restful.Api(app, prefix="/v1", catch_all_404s=True)
routes.init(api)
