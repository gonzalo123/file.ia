import os
from datetime import timedelta
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENVIRONMENT = os.getenv('ENVIRONMENT', 'local')

load_dotenv(dotenv_path=Path(BASE_DIR).resolve().joinpath('env', ENVIRONMENT, '.env'))

DEBUG = os.getenv('DEBUG', 'False') == 'True'
FAKE_USER = os.getenv('FAKE_USER', False)
APP_ID = 'ai'
SECRET = 'a60fea8f093271791246f09cb1ee0e53'

JWT_EXPIRATION_TIMEDELTA = timedelta(minutes=1)
JWT_ALGORITHM = "HS256"

BASE_URL = APP_ID

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', False)
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', False)
AWS_PROFILE_NAME = os.getenv('AWS_PROFILE_NAME', False)
AWS_REGION = os.getenv('AWS_REGION')
AWS_ASSUME_ROLE = os.getenv('AWS_ASSUME_ROLE', False)


class Models(StrEnum):
    CLAUDE_45 = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'


MY_LATITUDE = float(os.getenv('MY_LATITUDE'))
MY_LONGITUDE = float(os.getenv('MY_LONGITUDE'))

MIME_MAP = {
    "application/pdf": "pdf",
    "text/csv": "csv",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/html": "html",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/x-markdown": "md"
}
