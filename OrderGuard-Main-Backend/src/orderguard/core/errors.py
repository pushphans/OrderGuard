class IncompleteCredentialsError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class InvalidCredentialError(Exception):
    pass

class RefreshTokenExpired(Exception):
    pass

class NotOwnerError(Exception):
    pass

class CartEmptyError(Exception):
    pass

class InsufficientStockError(Exception):
    pass

class StockLimitExceededError(Exception):
    pass

class ProductInUseError(Exception):
    pass
