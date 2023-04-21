class BaseError(Exception):
    ...


class DisablingError(BaseError):
    ...


class PostponingError(BaseError):
    ...


class MarketAlreadySubscribed(BaseError):
    ...


class AuthenticationError(BaseError):
    ...
