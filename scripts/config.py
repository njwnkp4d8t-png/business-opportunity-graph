"""
Secure Configuration Management
Loads credentials from environment variables and .env files
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Determine the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()


def load_env_file(env_file: str = ".env") -> dict:
    """
    Load environment variables from a .env file

    Args:
        env_file: Path to .env file (relative to project root)

    Returns:
        Dictionary of environment variables
    """
    env_path = PROJECT_ROOT / env_file
    env_vars = {}

    if not env_path.exists():
        logger.warning(f"Environment file not found: {env_path}")
        logger.info("Using system environment variables only")
        return env_vars

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        env_vars[key] = value

        logger.info(f"Loaded {len(env_vars)} variables from {env_path}")
        return env_vars

    except Exception as e:
        logger.error(f"Error loading {env_path}: {e}")
        return env_vars


class Config:
    """
    Configuration class that loads from environment variables
    Provides secure access to credentials
    """

    def __init__(self):
        # Load .env file if exists
        load_env_file()

        # Environment
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'

        # PostgreSQL / PostGIS
        self.postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port = int(os.getenv('POSTGRES_PORT', '5432'))
        self.postgres_db = os.getenv('POSTGRES_DB', 'business_opportunity_graph')
        self.postgres_user = os.getenv('POSTGRES_USER', 'postgres')
        self.postgres_password = os.getenv('POSTGRES_PASSWORD', '')

        # Neo4j
        self.neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD', '')
        self.neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')

        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.openai_timeout = int(os.getenv('OPENAI_TIMEOUT', '30'))

        self.esri_api_key = os.getenv('ESRI_API_KEY', '')

        # Application settings
        self.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')

        # CORS
        cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:8888')
        self.cors_origins = [origin.strip() for origin in cors_origins.split(',')]

        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_file = os.getenv('LOG_FILE', 'logs/app.log')

        # Data paths
        self.data_dir = Path(os.getenv('DATA_DIR', PROJECT_ROOT / 'data'))
        self.export_dir = Path(os.getenv('EXPORT_DIR', PROJECT_ROOT / 'exports'))

        # Validate critical settings
        self._validate()

    def _validate(self):
        """Validate critical configuration settings"""
        warnings = []

        # Check for missing critical credentials
        if not self.postgres_password and self.environment == 'production':
            warnings.append("POSTGRES_PASSWORD is not set in production!")

        if not self.neo4j_password and self.environment == 'production':
            warnings.append("NEO4J_PASSWORD is not set in production!")

        if self.secret_key == 'dev-secret-key-change-in-production' and self.environment == 'production':
            warnings.append("SECRET_KEY is using default value in production!")

        # Log warnings
        for warning in warnings:
            logger.warning(f"⚠️  Security Warning: {warning}")

        if warnings and self.environment == 'production':
            logger.error("Critical security issues detected in production!")

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        password = f":{self.postgres_password}" if self.postgres_password else ""
        return f"postgresql://{self.postgres_user}{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def neo4j_auth(self) -> tuple:
        """Get Neo4j authentication tuple"""
        return (self.neo4j_user, self.neo4j_password)

    def mask_sensitive(self, value: str, show_chars: int = 4) -> str:
        """
        Mask sensitive values for logging

        Args:
            value: The sensitive string to mask
            show_chars: Number of characters to show at the end

        Returns:
            Masked string
        """
        if not value or len(value) <= show_chars:
            return "***"
        return "*" * (len(value) - show_chars) + value[-show_chars:]

    def __repr__(self):
        """Safe representation of config (masks sensitive data)"""
        return f"""Config(
    environment={self.environment}
    debug={self.debug}
    postgres_host={self.postgres_host}
    postgres_user={self.postgres_user}
    postgres_password={self.mask_sensitive(self.postgres_password)}
    neo4j_uri={self.neo4j_uri}
    neo4j_user={self.neo4j_user}
    neo4j_password={self.mask_sensitive(self.neo4j_password)}
    openai_api_key={self.mask_sensitive(self.openai_api_key)}
)"""


# Singleton instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get or create the singleton Config instance

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()

        # Log configuration status (masked)
        if _config.debug:
            logger.debug("Configuration loaded:")
            logger.debug(_config)

    return _config


# Example usage functions
def get_postgres_connection():
    """
    Example: Get PostgreSQL connection using psycopg2

    Returns:
        Database connection
    """
    try:
        import psycopg2

        config = get_config()
        conn = psycopg2.connect(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password
        )
        logger.info("✅ PostgreSQL connection established")
        return conn
    except ImportError:
        logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
        raise
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise


def get_neo4j_driver():
    """
    Example: Get Neo4j driver

    Returns:
        Neo4j driver
    """
    try:
        from neo4j import GraphDatabase

        config = get_config()
        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=config.neo4j_auth
        )

        # Test connection
        driver.verify_connectivity()
        logger.info("✅ Neo4j connection established")
        return driver
    except ImportError:
        logger.error("neo4j not installed. Install with: pip install neo4j")
        raise
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        raise


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test configuration
    print("=" * 60)
    print("Testing Configuration")
    print("=" * 60)

    config = get_config()
    print(config)

    print("\n" + "=" * 60)
    print("Connection Strings (masked)")
    print("=" * 60)
    print(f"PostgreSQL URL: {config.postgres_url}")
    print(f"Neo4j Auth: ({config.neo4j_user}, {config.mask_sensitive(config.neo4j_password)})")
