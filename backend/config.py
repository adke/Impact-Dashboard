import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
REPO = "PostHog/posthog"
DEFAULT_DAYS = 90
CACHE_TTL = 600  # 10 minutes
TOP_N = 5
