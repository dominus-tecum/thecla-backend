# config.py
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration - centralized settings management"""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./theclamed.db")
    
    # WhatsApp Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    WHATSAPP_FROM_NUMBER: str = os.getenv("WHATSAPP_FROM_NUMBER", "")
    WHATSAPP_ADMIN_NUMBER: str = os.getenv("WHATSAPP_ADMIN_NUMBER", "")
    
    # Email Configuration
    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "800"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # AI Rate Limits
    MAX_AI_QUESTIONS_PER_DAY: int = int(os.getenv("MAX_AI_QUESTIONS_PER_DAY", "100"))
    AI_QUESTION_TIMEOUT: int = int(os.getenv("AI_QUESTION_TIMEOUT", "10"))
    
    # Feature Flags
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production-12345")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @classmethod
    def validate_ai_config(cls) -> dict:
        """Validate AI configuration and return status"""
        status = {
            "openai_configured": bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY != "sk-your-actual-openai-api-key-here"),
            "ai_enabled": cls.AI_ENABLED,
            "model": cls.OPENAI_MODEL,
            "daily_limit": cls.MAX_AI_QUESTIONS_PER_DAY
        }
        
        if not status["openai_configured"]:
            print("⚠️ OpenAI API key not configured in .env file")
            print("⚠️ AI quiz features will be disabled")
            print("🔑 Get your API key from: https://platform.openai.com/api-keys")
        
        return status
    
    @classmethod
    def get_all_config(cls, hide_secrets: bool = True) -> dict:
        """Get all configuration (for debugging, hides secrets by default)"""
        config_dict = {
            "database": {
                "url": cls.DATABASE_URL
            },
            "whatsapp": {
                "account_sid_configured": bool(cls.TWILIO_ACCOUNT_SID),
                "auth_token_configured": bool(cls.TWILIO_AUTH_TOKEN),
                "from_number": cls.WHATSAPP_FROM_NUMBER if not hide_secrets else "***",
                "admin_number": cls.WHATSAPP_ADMIN_NUMBER if not hide_secrets else "***"
            },
            "email": {
                "user_configured": bool(cls.EMAIL_USER),
                "password_configured": bool(cls.EMAIL_PASSWORD)
            },
            "openai": {
                "api_key_configured": bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY != "sk-your-actual-openai-api-key-here"),
                "model": cls.OPENAI_MODEL,
                "max_tokens": cls.OPENAI_MAX_TOKENS,
                "temperature": cls.OPENAI_TEMPERATURE,
                "daily_limit": cls.MAX_AI_QUESTIONS_PER_DAY,
                "timeout": cls.AI_QUESTION_TIMEOUT,
                "enabled": cls.AI_ENABLED
            },
            "security": {
                "secret_key_configured": bool(cls.SECRET_KEY and cls.SECRET_KEY != "your-super-secret-key-change-this-in-production-12345"),
                "algorithm": cls.ALGORITHM,
                "token_expire_minutes": cls.ACCESS_TOKEN_EXPIRE_MINUTES
            }
        }
        
        return config_dict

# Global config instance
config = Config()