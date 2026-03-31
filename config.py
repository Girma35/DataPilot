"""Application configuration loaded from environment variables."""

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", str(Path(__file__).resolve().parent / "chroma"))

SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
