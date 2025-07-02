import asyncio
import uvicorn
from bot import run_bot  # your Discord bot startup function
from api import app      # your FastAPI app

async def start_uvicorn():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    # Start both bot and FastAPI server concurrently
    await asyncio.gather(
        run_bot(),
        start_uvicorn()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
