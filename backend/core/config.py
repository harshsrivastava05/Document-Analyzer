import os

class Settings:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    WORKERS = int(os.getenv("WORKERS", 1))
    ALLOWED_HOSTS = os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,*.vercel.app,*.netlify.app,*.railway.app"
    ).split(",")
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    ).split(",")
    DISABLE_FILE_LOGGING = os.getenv("DISABLE_FILE_LOGGING")

settings = Settings()