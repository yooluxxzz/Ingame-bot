import discord
from discord.ext import commands
import os
import aiosqlite
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1380462777881071637
CHANNEL_ID = 1389278872037494784
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("?"), intents=intents)
bot.remove_command("help")


def parse_duration(duration_str):
    total = 0
    units = {"h": 3600, "m": 60, "s": 1}
    num = ""
    for c in duration_str:
        if c.isdigit():
            num += c
        elif c in units and num:
            total += int(num) * units[c]
            num = ""
    return total


def check_channel(interaction):
    return interaction.channel.id == CHANNEL_ID


async def log_punishment(username, ptype, reason, duration=None):
    now = datetime.utcnow()
    expires_at = (now + timedelta(seconds=parse_duration(duration))) if duration else None
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("""
            INSERT INTO punishments (username, type, reason, duration, expires_at, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, ptype, reason, duration, expires_at.isoformat() if expires_at else None, now.isoformat()))
        await db.commit()


# --- SLASH COMMANDS --- #
@bot.tree.command(name="status", description="Check punishment status of a Roblox user")
async def status(interaction: discord.Interaction, username: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return

    now = datetime.utcnow().timestamp()
    muted = False
    banned = False
    reasons = []

    async with aiosqlite.connect("punishments.db") as db:
        async with db.execute("SELECT type, reason, expires_at FROM punishments WHERE username = ?", (username,)) as cursor:
            async for row in cursor:
                ptype, reason, expires_at = row
                if expires_at:
                    try:
                        if datetime.fromisoformat(expires_at).timestamp() < now:
                            continue  # Skip expired
                    except:
                        pass

                if ptype == "MUTE":
                    muted = True
                if ptype in ("PBAN", "TBAN"):
                    banned = True
                reasons.append(f"• **{ptype}** - {reason}" + (f" (until {expires_at})" if expires_at else ""))

    if not muted and not banned:
        await interaction.response.send_message(f"✅ `{username}` has no active punishments.")
    else:
        msg = f"🚫 `{username}` is currently:"
        if banned:
            msg += "\n🔨 Banned"
        if muted:
            msg += "\n🔇 Muted"
        msg += "\n\n**Reasons:**\n" + "\n".join(reasons)
        await interaction.response.send_message(msg)

@bot.tree.command(name="tban", description="Temporarily ban a user (Roblox username)")
async def tban(interaction: discord.Interaction, username: str, reason: str, duration: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return
    await log_punishment(username, "TBAN", reason, duration)
    await interaction.response.send_message(f"✅ Temporarily banned `{username}` for `{duration}`.\nReason: {reason}")

@bot.tree.command(name="pban", description="Permanently ban a user (Roblox username)")
async def pban(interaction: discord.Interaction, username: str, reason: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return
    await log_punishment(username, "PBAN", reason)
    await interaction.response.send_message(f"✅ Permanently banned `{username}`.\nReason: {reason}")

@bot.tree.command(name="untban", description="Unban a temporary banned user (Roblox username)")
async def untban(interaction: discord.Interaction, username: str, reason: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("DELETE FROM punishments WHERE username=? AND type='TBAN'", (username,))
        await db.commit()
    await interaction.response.send_message(f"✅ Unbanned `{username}` from temporary ban.\nReason: {reason}")

@bot.tree.command(name="unpban", description="Unban a permanently banned user (Roblox username)")
async def unpban(interaction: discord.Interaction, username: str, reason: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("DELETE FROM punishments WHERE username=? AND type='PBAN'", (username,))
        await db.commit()
    await interaction.response.send_message(f"✅ Unbanned `{username}` from permanent ban.\nReason: {reason}")

@bot.tree.command(name="mute", description="Mute a user (Roblox username)")
async def mute(interaction: discord.Interaction, username: str, reason: str, duration: str):
    if not check_channel(interaction):
        await interaction.response.send_message("❌ Use this in the punishment channel only.", ephemeral=True)
        return
    await log_punishment(username, "MUTE", reason, duration)
    await interaction.response.send_message(f"✅ Muted `{username}` for `{duration}`.\nReason: {reason}")


# --- TEXT COMMANDS --- #

@bot.command(name="tban")
async def tban_text(ctx, username: str = None, duration: str = None, *, reason: str = None):
    if ctx.channel.id != CHANNEL_ID:
        return
    if not username or not duration or not reason:
        await ctx.send("❌ Usage: `?tban <roblox_username> <duration> <reason>`")
        return
    await log_punishment(username, "TBAN", reason, duration)
    await ctx.send(f"✅ Temporarily banned `{username}` for `{duration}`.\nReason: {reason}")

@bot.command(name="pban")
async def pban_text(ctx, username: str = None, *, reason: str = None):
    if ctx.channel.id != CHANNEL_ID:
        return
    if not username or not reason:
        await ctx.send("❌ Usage: `?pban <roblox_username> <reason>`")
        return
    await log_punishment(username, "PBAN", reason)
    await ctx.send(f"✅ Permanently banned `{username}`.\nReason: {reason}")

@bot.command(name="untban")
async def untban_text(ctx, username: str = None, *, reason: str = None):
    if ctx.channel.id != CHANNEL_ID:
        return
    if not username or not reason:
        await ctx.send("❌ Usage: `?untban <roblox_username> <reason>`")
        return
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("DELETE FROM punishments WHERE username=? AND type='TBAN'", (username,))
        await db.commit()
    await ctx.send(f"✅ Unbanned `{username}` from temporary ban.\nReason: {reason}")

@bot.command(name="unpban")
async def unpban_text(ctx, username: str = None, *, reason: str = None):
    if ctx.channel.id != CHANNEL_ID:
        return
    if not username or not reason:
        await ctx.send("❌ Usage: `?unpban <roblox_username> <reason>`")
        return
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("DELETE FROM punishments WHERE username=? AND type='PBAN'", (username,))
        await db.commit()
    await ctx.send(f"✅ Unbanned `{username}` from permanent ban.\nReason: {reason}")

@bot.command(name="mute")
async def mute_text(ctx, username: str = None, duration: str = None, *, reason: str = None):
    if ctx.channel.id != CHANNEL_ID:
        return
    if not username or not duration or not reason:
        await ctx.send("❌ Usage: `?mute <roblox_username> <duration> <reason>`")
        return
    await log_punishment(username, "MUTE", reason, duration)
    await ctx.send(f"✅ Muted `{username}` for `{duration}`.\nReason: {reason}")

@bot.command(name="help")
async def help_text(ctx):
    if ctx.channel.id != CHANNEL_ID:
        return
    await ctx.send("""
📘 **Punishment Commands (WORKS IN-GAME ONLY.):**

`?tban <roblox_username> <duration> <reason>` – Temporarily ban a user (in-game only)  
`?pban <roblox_username> <reason>` – Permanently ban a user (in-game only)  
`?untban <roblox_username> <reason>` – Unban a temporary ban (in-game only)  
`?unpban <roblox_username> <reason>` – Unban a permanent ban (in-game only)  
`?mute <roblox_username> <duration> <reason>` – Mute a user from chat (in-game only)
""")


# --- STARTUP EVENT --- #
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    async with aiosqlite.connect("punishments.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                type TEXT,
                reason TEXT,
                duration TEXT,
                expires_at TEXT,
                timestamp TEXT
            )
        """)
        await db.commit()
    
    async def cleanup_expired_punishments():
        while True:
            now = datetime.utcnow().isoformat()
            async with aiosqlite.connect("punishments.db") as db:
                await db.execute("DELETE FROM punishments WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
                await db.commit()
            await asyncio.sleep(300)  # every 5 minutes

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(f"✅ {bot.user.name} is online and commands are synced!")

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("✅ Slash commands synced successfully.")

# --- BOT RUN --- #
async def run_bot():
    await bot.start(TOKEN)
