#!/usr/bin/env python3

import argparse
import getpass

import flask_bcrypt

import core

argp = argparse.ArgumentParser()
argp.add_argument("--email", required=True)
argp.add_argument("--name", required=True)
args = argp.parse_args()

passwd = getpass.getpass("enter user password: ")
passwd = flask_bcrypt.generate_password_hash(passwd)

core.db.User.create(email=args.email, password=passwd, name=args.name)
