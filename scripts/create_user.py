#!/usr/bin/env python3

import argparse
import getpass

import flask_bcrypt

import core


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--email",
                      "-u",
                      required=True)
    args = argp.parse_args()

    passwd = getpass.getpass("enter user password: ")
    passwd = flask_bcrypt.generate_password_hash(passwd)

    core.db.User.create(email=args.email.lower(), password=passwd)
