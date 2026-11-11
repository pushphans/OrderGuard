class InvalidTokenError(Exception):
    pass

class CartEmptyError(Exception):
    pass

class InsufficientStockError(Exception):
    pass

class StockLimitExceededError(Exception):
    pass

class CatalogUnavailableError(Exception):
    pass
