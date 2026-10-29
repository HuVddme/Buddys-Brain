from pathlib import Path

from dotenv import load_dotenv

# Host environment variables take precedence over local development settings.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
