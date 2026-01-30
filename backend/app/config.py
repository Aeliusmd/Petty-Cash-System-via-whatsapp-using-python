"""
Configuration management for the application
Centralized configuration using environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
for env_path in ['.env', '../.env', '../../.env', Path(__file__).parent.parent.parent.parent / '.env']:
    if Path(env_path).exists():
        load_dotenv(env_path)
        break
else:
    load_dotenv()


class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://localhost/petty_cash')
    
    # JWT
    JWT_SECRET: str = os.getenv('JWT_SECRET', 'your-secret-key')
    JWT_ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRY_HOURS: int = int(os.getenv('JWT_EXPIRY_HOURS', '24'))
    
    # WAHA (WhatsApp HTTP API)
    WAHA_BASE_URL: str = os.getenv('WAHA_BASE_URL', 'http://waha:3000')
    WAHA_SESSION: str = os.getenv('WAHA_SESSION', 'default')
    WAHA_API_KEY: str = os.getenv('WAHA_API_KEY', '')
    
    # AWS (for Textract)
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Application
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    RECEIPTS_DIR: Path = Path(__file__).parent.parent / 'receipts'
    
    @classmethod
    def get_receipts_dir(cls) -> Path:
        """Get receipts directory, creating if needed"""
        cls.RECEIPTS_DIR.mkdir(exist_ok=True)
        return cls.RECEIPTS_DIR


config = Config()
