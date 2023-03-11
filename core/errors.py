class BaseError(Exception):
    pass


class ModelDoesNotExist(Exception):
    pass


class ModelTooLarge(Exception):
    pass


class MarketAlreadySubscribed(Exception):
    pass
