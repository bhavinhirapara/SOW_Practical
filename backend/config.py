import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Verify configuration
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY is not set in environment or .env file.")
