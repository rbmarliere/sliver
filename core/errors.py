class BaseError(Exception):
    ...


class DisablingError(BaseError):
    ...


class PostponingError(BaseError):
    ...


class ModelDoesNotExist(Exception):
    ...


class ModelTooLarge(Exception):
    ...


class MarketAlreadySubscribed(Exception):
    ...
