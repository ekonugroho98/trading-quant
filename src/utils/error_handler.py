"""
Error Handling Module
Retry mechanism, timeout, dan circuit breaker untuk API calls
"""

import time
import functools
from typing import Callable, Optional, TypeVar, Any, Dict
from enum import Enum
import logging

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern untuk API calls"""
    
    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger('circuit_breaker')
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function dengan circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) < self.recovery_timeout:
                raise Exception(f"Circuit breaker is OPEN. Too many failures.")
            else:
                # Try to recover
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker entering HALF_OPEN state")
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.logger.info("Circuit breaker recovered, entering CLOSED state")
            self.failure_count = 0
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            raise


def retry(max_attempts: int = 3,
          delay: float = 1.0,
          backoff: float = 2.0,
          exceptions: tuple = (Exception,),
          logger: Optional[logging.Logger] = None) -> Callable:
    """
    Retry decorator dengan exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
        logger: Logger instance
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        if logger:
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                                f"Retrying in {current_delay:.2f}s..."
                            )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        if logger:
                            logger.error(f"All {max_attempts} attempts failed")
                        raise
        
        return wrapper
    return decorator


def with_timeout(timeout: float, default_value: Any = None,
                 logger: Optional[logging.Logger] = None) -> Callable:
    """
    Timeout decorator untuk function calls
    
    Args:
        timeout: Timeout in seconds
        default_value: Value to return if timeout
        logger: Logger instance
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")
            
            # Set signal handler (Unix only)
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except TimeoutError:
                    if logger:
                        logger.error(f"Function {func.__name__} timed out")
                    if default_value is not None:
                        return default_value
                    raise
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # Windows - use threading approach
                import threading
                result_container = [None]
                exception_container = [None]
                
                def target():
                    try:
                        result_container[0] = func(*args, **kwargs)
                    except Exception as e:
                        exception_container[0] = e
                
                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()
                thread.join(timeout)
                
                if thread.is_alive():
                    if logger:
                        logger.error(f"Function {func.__name__} timed out")
                    if default_value is not None:
                        return default_value
                    raise TimeoutError(f"Function {func.__name__} timed out after {timeout}s")
                
                if exception_container[0]:
                    raise exception_container[0]
                
                return result_container[0]
        
        return wrapper
    return decorator


class APIErrorHandler:
    """Centralized API error handling dengan retry dan circuit breaker"""
    
    def __init__(self, max_retries: int = 3,
                 retry_delay: float = 1.0,
                 timeout: float = 30.0,
                 circuit_breaker_threshold: int = 5):
        """
        Initialize API error handler
        
        Args:
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries
            timeout: Request timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger('api_error_handler')
    
    def get_circuit_breaker(self, api_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for API"""
        if api_name not in self.circuit_breakers:
            self.circuit_breakers[api_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0
            )
        return self.circuit_breakers[api_name]
    
    def execute(self, api_name: str, func: Callable[..., T], 
                *args, **kwargs) -> T:
        """
        Execute API call dengan error handling
        
        Args:
            api_name: Name of API (for circuit breaker)
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        """
        circuit_breaker = self.get_circuit_breaker(api_name)
        
        @retry(max_attempts=self.max_retries,
               delay=self.retry_delay,
               logger=self.logger)
        @with_timeout(timeout=self.timeout, logger=self.logger)
        def _execute():
            return circuit_breaker.call(func, *args, **kwargs)
        
        return _execute()


# Global API error handler instance
_default_error_handler = APIErrorHandler()


def handle_api_call(api_name: str, func: Callable[..., T], 
                   *args, **kwargs) -> T:
    """
    Execute API call dengan centralized error handling
    
    Args:
        api_name: Name of API
        func: Function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        Function result
    """
    return _default_error_handler.execute(api_name, func, *args, **kwargs)

