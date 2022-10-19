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
    "backtest", help="backtest a given strategy")
backtest_parser.add_argument("-s",
                           "--strategy_id",
                           help="id of the strategy to backtest",
                           required=True)
backtest_parser.set_defaults(func=hypnox.strategy.backtest)

stream_parser = sub_parsers.add_parser("stream",
                                       help="stream twitter in real time")
stream_parser.set_defaults(func=hypnox.twitter.stream)

watch_parser = sub_parsers.add_parser("watch",
                                      help="watch the market in real time")
watch_parser.set_defaults(func=hypnox.watchdog.watch)

args = argp.parse_args()

try:
    args.func(args)
except Exception as e:
    hypnox.watchdog.exception_log.exception(e, exc_info=True)
