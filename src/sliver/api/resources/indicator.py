import time
import peewee
from flask_jwt_extended import jwt_required
from flask_restful import Resource, marshal

from sliver.api.exceptions import StrategyDoesNotExist, StrategyRefreshing
from sliver.strategies.factory import StrategyFactory
from sliver.strategy import BaseStrategy
from flask_restful import reqparse


class Indicator(Resource):
    @jwt_required()
    def get(self, strategy_id):
        parser = reqparse.RequestParser()
        parser.add_argument("since", type=int, default=None, location="args")
        parser.add_argument("until", type=int, default=None, location="args")
        args = parser.parse_args()

        join_type = None

        if args.since and args.until:
            join_type = peewee.JOIN.INNER

        try:
            strategy = StrategyFactory.from_base(BaseStrategy.get_by_id(strategy_id))
            if strategy.deleted:
                raise StrategyDoesNotExist
        except BaseStrategy.DoesNotExist:
            raise StrategyDoesNotExist

        if join_type:
            timeout = 240
            start = time.time()
            timedout = False
            while True:
                if time.time() - start > timeout:
                    timedout = True
                    break
                if strategy.get_indicators(join_type=join_type).count() > 0:
                    break
                time.sleep(5)
            if timedout:
                raise StrategyRefreshing

        ind = strategy.get_indicators_df(
            join_type=join_type, since=args.since, until=args.until
        )

        if not ind.empty:
            ind.replace({float("nan"): None}, inplace=True)

        return marshal(ind.to_dict("list"), strategy.get_indicator_fields())
