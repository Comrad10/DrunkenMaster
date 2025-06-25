class CrawlerError(Exception):
    """Base exception for crawler-related errors"""
    pass

class NetworkError(CrawlerError):
    """Network-related errors (timeouts, connection issues)"""
    pass

class ParseError(CrawlerError):
    """Data parsing errors"""
    pass

class RateLimitError(CrawlerError):
    """Rate limiting errors"""
    pass

class AuthenticationError(CrawlerError):
    """Authentication or authorization errors"""
    pass

class DataValidationError(CrawlerError):
    """Data validation errors"""
    pass

class StorageError(CrawlerError):
    """Database or storage-related errors"""
    pass

class CrawlInterruptedError(CrawlerError):
    """Crawl process was interrupted"""
    pass