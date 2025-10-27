import os

def verify_shared_secret(provided: str) -> bool:
    return bool(provided and provided == os.getenv("WEBHOOK_SHARED_SECRET"))
