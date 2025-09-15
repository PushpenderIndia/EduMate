import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for EduMate Agentic System"""

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'VeryVeryComify#@666')

    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # Gemini 2.0 Flash Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # TiDB Serverless Configuration
    TIDB_SERVERLESS_HOST = os.getenv('TIDB_SERVERLESS_HOST')
    TIDB_SERVERLESS_PORT = int(os.getenv('TIDB_SERVERLESS_PORT', '4000'))
    TIDB_SERVERLESS_USER = os.getenv('TIDB_SERVERLESS_USER')
    TIDB_SERVERLESS_PASSWORD = os.getenv('TIDB_SERVERLESS_PASSWORD')
    TIDB_SERVERLESS_DATABASE = os.getenv('TIDB_SERVERLESS_DATABASE')
    TIDB_CLOUD_EMAIL = os.getenv('TIDB_CLOUD_EMAIL')

    # Image Generation Configuration (Google Gemini)
    IMAGE_GENERATION_PROVIDER = 'google_gemini'  # Changed to Google Gemini
    GEMINI_IMAGE_MODEL = 'gemini-2.5-flash-image-preview'  # Gemini image generation model

    # Agent System Configuration
    AGENT_TIMEOUT_SECONDS = int(os.getenv('AGENT_TIMEOUT_SECONDS', '120'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    PARALLEL_WORKERS = int(os.getenv('PARALLEL_WORKERS', '3'))

    # File Paths
    STATIC_FOLDER = os.getenv('STATIC_FOLDER', 'static')
    PDF_OUTPUT_FOLDER = os.path.join(STATIC_FOLDER, 'pdfs')
    IMAGE_OUTPUT_FOLDER = os.path.join(STATIC_FOLDER, 'img', 'comic')
    FONT_FOLDER = os.path.join(STATIC_FOLDER, 'font')

    # Comic Generation Settings
    DEFAULT_CFG = int(os.getenv('DEFAULT_CFG', '8'))
    DEFAULT_STEPS = int(os.getenv('DEFAULT_STEPS', '25'))
    DEFAULT_AGE_GROUP = os.getenv('DEFAULT_AGE_GROUP', 'child')

    # Supported Languages
    SUPPORTED_LANGUAGES = {
        "English": "en",
        "Spanish": "es",
        "French": "fr",
        "Hindi": "hi",
        "Arabic": "ar",
        "Bengali": "bn",
        "Telugu": "te",
        "Marathi": "mr",
        "Tamil": "ta",
        "Urdu": "ur",
        "Gujarati": "gu",
        "Kannada": "kn",
        "Odia": "or",
        "Punjabi": "pa"
    }

    # Agent Configuration
    AGENT_CONFIG = {
        'content_intelligence': {
            'timeout': AGENT_TIMEOUT_SECONDS,
            'max_retries': MAX_RETRIES,
            'priority': 1
        },
        'educational_planning': {
            'timeout': AGENT_TIMEOUT_SECONDS,
            'max_retries': MAX_RETRIES,
            'priority': 2
        },
        'visual_generation': {
            'timeout': AGENT_TIMEOUT_SECONDS,
            'max_retries': MAX_RETRIES,
            'priority': 3
        },
        'quality_assurance': {
            'timeout': AGENT_TIMEOUT_SECONDS,
            'max_retries': MAX_RETRIES,
            'priority': 4
        }
    }

    @classmethod
    def validate_config(cls):
        """Validate that all required configuration values are present"""
        required_vars = [
            'GEMINI_API_KEY',
            'TIDB_SERVERLESS_HOST',
            'TIDB_SERVERLESS_USER',
            'TIDB_SERVERLESS_PASSWORD',
            'TIDB_SERVERLESS_DATABASE'
        ]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Note: GEMINI_API_KEY is already included in required_vars, so image generation will work
        print("✅ All required configuration validated. Google Gemini image generation ready.")

        return True

    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist"""
        directories = [
            cls.PDF_OUTPUT_FOLDER,
            cls.IMAGE_OUTPUT_FOLDER,
            cls.FONT_FOLDER
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def get_agent_config(cls, agent_name):
        """Get configuration for a specific agent"""
        return cls.AGENT_CONFIG.get(agent_name, {
            'timeout': cls.AGENT_TIMEOUT_SECONDS,
            'max_retries': cls.MAX_RETRIES,
            'priority': 5
        })

# Validate configuration on import
try:
    Config.validate_config()
    Config.create_directories()
    print("✅ EduMate configuration validated successfully")
except Exception as e:
    print(f"⚠️ Configuration warning: {e}")
    print("Please ensure all required environment variables are set in your .env file")