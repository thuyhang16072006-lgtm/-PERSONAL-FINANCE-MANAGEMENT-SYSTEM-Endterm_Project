"""
db_config.py — Database configuration
FIX: Credentials are loaded from environment variables.
     Copy .env.example to .env and fill in your values.
"""
import os
from dotenv import load_dotenv

load_dotenv()   # reads .env file if present

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "finance_app"),
    "password": os.getenv("DB_PASSWORD", ""),      # NEVER hardcode passwords
    "database": os.getenv("DB_NAME",     "moneymate"),
    "charset":  "utf8mb4",
}