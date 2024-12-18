import argparse
import getpass

import flask_bcrypt

import sliver.database as db
from sliver.user import User

if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument("--email", "-u", required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter user password: ")
    passwd = flask_bcrypt.generate_password_hash(passwd)

    User.create(email=args.email.lower(), password=passwd)
