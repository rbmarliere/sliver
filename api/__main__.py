import waitress

import api
import core


def main():
    if core.config["ENV_NAME"] == "development":
        import debugpy
        import werkzeug
        if werkzeug.serving.is_running_from_reloader():
            debugpy.listen(33333)

        api.app.run(port=5000,
                    debug=True,
                    use_debugger=False,
                    use_reloader=True)

    elif core.config["ENV_NAME"] == "production":
        waitress.serve(api.app, port=5000)


if __name__ == '__main__':
    main()
