"""Configuration for Google Photos Archiver."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Archive settings
ARCHIVE_PATH = Path(os.getenv('ARCHIVE_PATH', '/mnt/data/google-archiver'))
CUTOFF_YEARS = int(os.getenv('CUTOFF_YEARS', '2'))
DRY_RUN = os.getenv('DRY_RUN', 'true').lower() == 'true'

# Google Photos API
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Ensure archive path exists
ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
