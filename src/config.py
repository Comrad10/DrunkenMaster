import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/lcbo_products.db")
    
    MIN_REQUEST_DELAY = float(os.getenv("MIN_REQUEST_DELAY", "2"))
    MAX_REQUEST_DELAY = float(os.getenv("MAX_REQUEST_DELAY", "5"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    CONCURRENT_REQUESTS = int(os.getenv("CONCURRENT_REQUESTS", "1"))
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "crawler.log"))
    
    ROTATE_USER_AGENTS = os.getenv("ROTATE_USER_AGENTS", "true").lower() == "true"
    
    AVOID_HOURS_START = int(os.getenv("AVOID_HOURS_START", "17"))
    AVOID_HOURS_END = int(os.getenv("AVOID_HOURS_END", "20"))
    
    LCBO_BASE_URL = "https://www.lcbo.com"
    LCBO_PRODUCTS_URL = f"{LCBO_BASE_URL}/en/products"
    
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    CATEGORIES = [
        "wine",
        "beer-cider", 
        "spirits",
        "coolers",
        "non-alcoholic"
    ]
    
    @classmethod
    def create_directories(cls):
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

config = Config()