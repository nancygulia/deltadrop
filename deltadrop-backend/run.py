import sys
import asyncio
import uvicorn

# -------------------------------------------------------------------------
# MANDATORY FIX FOR WINDOWS: Playwright NotImplementedError subprocess crash
# -------------------------------------------------------------------------
if sys.platform == 'win32':
    # Force the event loop to Proactor, which is required for subprocesses
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Monkey-patch Uvicorn so it absolutely cannot override us back to SelectorEventLoop
    try:
        if hasattr(uvicorn, "config"):
            uvicorn.config.setup_event_loop = lambda *args, **kwargs: None
    except ImportError:
        pass

if __name__ == "__main__":
    print("Starting Server via run.py (Windows Safe Asyncio Loop & Reload Disabled)...")
    # We run uvicorn programmatically. We MUST disable reload=True, because the reloader
    # spawns a new python subprocess that ignores our custom policy and defaults back to
    # the broken WindowsSelectorEventLoop.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
