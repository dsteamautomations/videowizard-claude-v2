"""Server unit tests that need no database, no Docker and no live provider (design/40 §D). Run on any machine with the venv:
`.venv/bin/python -m pytest server/unit`. The database-backed tests stay in server/tests."""
import os
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
os.environ.setdefault('VW2_DATABASE_URL', '')   # settings load without a database
