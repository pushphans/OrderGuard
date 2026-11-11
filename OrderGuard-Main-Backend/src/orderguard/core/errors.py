class IncompleteCredentialsError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class InvalidTokenError(Exception):
    pass

class InvalidCredentialError(Exception):
    pass

class RefreshTokenExpired(Exception):
    pass

class NotOwnerError(Exception):
    pass

class InsufficientStockError(Exception):
    pass
