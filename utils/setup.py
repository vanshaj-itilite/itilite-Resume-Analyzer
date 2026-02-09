import os
import dotenv

dotenv.load_dotenv()

REDIS_URL = os.getenv("REMOTE_REDIS_URL")

broker_url = f"{REDIS_URL}/0"
result_backend = f"{REDIS_URL}/1"
