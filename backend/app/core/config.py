import os

from dotenv import load_dotenv

# F:\sevadilse\backend\.env load करें
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL .env file me set nahi hai. "
        "F:\\sevadilse\\backend\\.env check karein."
    )

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60