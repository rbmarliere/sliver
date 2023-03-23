class BaseError(Exception):
    ...


class DisablingError(BaseError):
    ...


class PostponingError(BaseError):
    ...


class ModelDoesNotExist(BaseError):
    ...


class ModelTooLarge(BaseError):
    ...


class MarketAlreadySubscribed(BaseError):
    ...
