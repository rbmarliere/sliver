from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

import core


class Inventory(Resource):
    @jwt_required()
    def get(self):
        uid = int(get_jwt_identity())
        user = core.db.User.get_by_id(uid)

        core.inventory.sync_balances(user)
        inventory = core.inventory.get_inventory(user)

        return inventory
