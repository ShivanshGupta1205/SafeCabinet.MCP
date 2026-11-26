class NotFoundError(Exception):
    """Exception raised when a requested resource is not found.""" 
    pass

class RateLimitExceededError(Exception):
    """Exception raised when the API rate limit is exceeded."""
    pass

class UpstreamError(Exception):
    """Exception raised for upstream server errors (5xx) and request errors."""
    pass

