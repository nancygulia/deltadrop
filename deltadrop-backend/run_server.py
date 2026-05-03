import sys
import asyncio
import uvicorn
from dotenv import load_dotenv

# 1. Load environment variables from .env EXACTLY like the uvicorn CLI does
load_dotenv()

# 2. Force the correct Windows Event Loop BEFORE anything else starts
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    # 3. Launch Uvicorn programmatically
    # Do NOT use --reload to prevent the SelectorEventLoop fallback bug
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
