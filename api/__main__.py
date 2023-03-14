import argparse

import waitress

import api
import core


def main(args=None):
    if args is None:
        use_debug = True
    else:
        use_debug = not args.no_debug

    if core.config["ENV_NAME"] == "development":
        api.app.run(port=5000, debug=use_debug)

    elif core.config["ENV_NAME"] == "production":
        waitress.serve(api.app, port=5000)


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--no-debug", action="store_true")
    args = argp.parse_args()
    main(args)
