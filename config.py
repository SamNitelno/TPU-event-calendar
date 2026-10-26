import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_ACCESS_TOKEN")  # нужен будет позже для сборщика
COMMUNITIES = [-12345678, -87654321]
API_VERSION = "5.131"

DB_URL = os.getenv("DATABASE_URL", "sqlite:///calendar.db")
PAGE_SIZE = 20
