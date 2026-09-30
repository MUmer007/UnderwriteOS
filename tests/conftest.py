from pathlib import Path

from dotenv import load_dotenv

# Automatically load .env file before any tests run
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)
