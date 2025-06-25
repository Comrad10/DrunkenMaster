import asyncio
import time
from functools import wraps
from typing import Callable, Any, Union, Tuple, Type
from src.exceptions import CrawlerError, NetworkError, RateLimitError
from src.utils.logger import logger
from src.config import config

class RetryConfig:
    def __init__(
        self,
        max_attempts: int = None,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = None
    ):
        self.max_attempts = max_attempts or config.MAX_RETRIES
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            NetworkError,
            RateLimitError,
            ConnectionError,
            TimeoutError
        )

def retry_async(retry_config: RetryConfig = None):
    """Decorator for async functions with retry logic"""
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(retry_config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == retry_config.max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        break
                    
                    delay = calculate_delay(
                        attempt,
                        retry_config.base_delay,
                        retry_config.max_delay,
                        retry_config.exponential_base,
                        retry_config.jitter
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_attempts} failed "
                        f"for {func.__name__}: {e}. Retrying in {delay:.2f}s"
                    )
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator

def retry_sync(retry_config: RetryConfig = None):
    """Decorator for sync functions with retry logic"""
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(retry_config.max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == retry_config.max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        break
                    
                    delay = calculate_delay(
                        attempt,
                        retry_config.base_delay,
                        retry_config.max_delay,
                        retry_config.exponential_base,
                        retry_config.jitter
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_attempts} failed "
                        f"for {func.__name__}: {e}. Retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator

def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool
) -> float:
    """Calculate delay for retry with exponential backoff"""
    delay = base_delay * (exponential_base ** attempt)
    
    delay = min(delay, max_delay)
    
    if jitter:
        import random
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay

class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker logic"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise CrawlerError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker logic"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise CrawlerError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")