from fastapi import FastAPI
import aiosqlite
from datetime import datetime
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/punishment")
async def get_punishment(username: str):  # <-- now using query param
    result = []
    async with aiosqlite.connect("punishments.db") as db:
        async with db.execute(
            "SELECT type, reason, duration, expires_at FROM punishments WHERE username = ?", (username,)
        ) as cursor:
            async for row in cursor:
                expires_unix = None
                try:
                    if row[3]:
                        expires_unix = int(datetime.fromisoformat(row[3]).timestamp())
                except Exception:
                    expires_unix = None  # fallback

                result.append({
                    "type": row[0],
                    "reason": row[1],
                    "duration": row[2],
                    "expires_unix": expires_unix
                })
    return JSONResponse(result)

@app.get("/")
async def root():
    return {"message": "Punishment API is active!"}
