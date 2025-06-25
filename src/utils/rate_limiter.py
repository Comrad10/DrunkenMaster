import time
import random
from datetime import datetime
from src.config import config
from src.utils.logger import logger

class RateLimiter:
    def __init__(self, min_delay=None, max_delay=None):
        self.min_delay = min_delay or config.MIN_REQUEST_DELAY
        self.max_delay = max_delay or config.MAX_REQUEST_DELAY
        self.last_request_time = 0
        self.request_count = 0
        self.backoff_factor = 1.0
        
    def wait(self):
        current_hour = datetime.now().hour
        
        if config.AVOID_HOURS_START <= current_hour < config.AVOID_HOURS_END:
            wait_hours = config.AVOID_HOURS_END - current_hour
            logger.warning(f"Currently in restricted hours ({config.AVOID_HOURS_START}-{config.AVOID_HOURS_END}). Waiting {wait_hours} hours.")
            time.sleep(wait_hours * 3600)
        
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay) * self.backoff_factor
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
    def increase_backoff(self):
        self.backoff_factor = min(self.backoff_factor * 1.5, 5.0)
        logger.warning(f"Increasing backoff factor to {self.backoff_factor}")
        
    def reset_backoff(self):
        self.backoff_factor = 1.0
        
    def get_stats(self):
        return {
            "request_count": self.request_count,
            "backoff_factor": self.backoff_factor,
            "current_delay_range": (
                self.min_delay * self.backoff_factor,
                self.max_delay * self.backoff_factor
            )
        }