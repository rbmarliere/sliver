#!/usr/bin/env python3

import argparse

import hypnox

description = """
              _        _
     |_| \\_/ |_) |\\ | / \\ \\/
     | |  |  |   | \\| \\_/ /\\

       sub noctem sapientia
    """

argp = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                               description=description)

sub_parsers = argp.add_subparsers(title="commands",
                                  dest="command",
                                  required=True)

backtest_parser = sub_parsers.add_parser(
    "backtest", help="backtest active strategies")
backtest_parser.set_defaults(func=hypnox.strategy.backtest)

replay_parser = sub_parsers.add_parser(
    "replay", help="use a trained model to replay a database")
replay_parser.add_argument("-m",
                           "--model",
                           help="name of the model to use",
                           required=True)
replay_parser.set_defaults(func=hypnox.db.replay)

stream_parser = sub_parsers.add_parser("stream",
                                       help="stream twitter in real time")
stream_parser.set_defaults(func=hypnox.twitter.stream)

watch_parser = sub_parsers.add_parser("watch",
                                      help="watch the market in real time")
watch_parser.set_defaults(func=hypnox.watchdog.watch)

args = argp.parse_args()
args.func(args)
