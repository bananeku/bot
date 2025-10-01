import discord
from discord.ext import tasks, commands
import re
from datetime import datetime, timedelta
import json
import os

# =======================
# KONFIGURACJA BOTA
# =======================
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("Nie ustawiono tokena bota! Ustaw zmienną środowiskową DISCORD_TOKEN")

LOG_CHANNEL_ID = 1412336608178343976  # ID kanału z logami z gry
ALERT_CHANNEL_ID = 1422798704674345002 # ID kanału, gdzie bot ma wysyłać powiadomienia
JSON_FILE = "respawns.json"

DEFAULT_RESPAWN_TIME = 10800  # 1 minuta do testów
REMINDERS = [10, 5, 1]            # przypomnienie 1 minutę przed respawnem
REMINDER_WINDOW = 10       # okienko ochronne w sekundach
# =======================
# INICJALIZACJA BOTA
# =======================
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Wczytanie tokena z zmiennej środowiskowej
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Nie ustawiono tokena bota! Ustaw zmienną środowiskową DISCORD_TOKEN")

# Wczytanie zapisanych respawnów
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        legend_respawns = json.load(f)
        for k in legend_respawns:
            legend_respawns[k]["respawn_time"] = datetime.fromisoformat(legend_respawns[k]["respawn_time"])
else:
    legend_respawns = {}

def save_respawns():
    data_to_save = {k: {
        "respawn_time": v["respawn_time"].isoformat(),
        "respawn_seconds": v.get("respawn_seconds", 0),
        "sent_reminders": v.get("sent_reminders", [])
    } for k, v in legend_respawns.items()}
    with open(JSON_FILE, "w") as f:
        json.dump(data_to_save, f)

# =======================
# EVENTY BOTA
# =======================
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")
    check_respawns.start()

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.id != LOG_CHANNEL_ID:
        return

    # Regex dopasowujący log Metin2
    match = re.search(
        r"\[Legenda Zniszczona\] Gracz (.*?) zniszczył \[(.*?)\]\. Miejsce zdarzenia: (.*?), Kanał: (\d+)\. Kolejny respawn: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        message.content
    )

    if match:
        player = match.group(1)
        boss_name = match.group(2)
        map_name = match.group(3)
        channel_num = match.group(4)
        respawn_str = match.group(5)
        respawn_time = datetime.strptime(respawn_str, "%Y-%m-%d %H:%M:%S")

        # Zapisywanie respawnu legendy
        legend_respawns[boss_name] = {
            "respawn_time": respawn_time,
            "respawn_seconds": int((respawn_time - datetime.utcnow()).total_seconds()),
            "sent_reminders": []
        }
        save_respawns()

        # Wysyłanie alertu na Discord z @everyone
        alert_channel = bot.get_channel(ALERT_CHANNEL_ID)
        await alert_channel.send(
            f"@everyone 🔔 **{boss_name}** został zabity przez **{player}**!\n"
            f"**Mapa:** {map_name}\n"
            f"**Kanał:** {channel_num}\n"
            f"**Kolejny respawn:** {respawn_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

# =======================
# PĘTLA SPRAWDZAJĄCA RESPAWNY
# =======================
@tasks.loop(seconds=5)
async def check_respawns():
    now = datetime.utcnow()
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    to_remove = []

    for boss_name, info in legend_respawns.items():
        respawn = info["respawn_time"]
        seconds_left = (respawn - now).total_seconds()

        # Przypomnienia przed respawnem (tylko raz)
        for reminder in REMINDERS:
            reminder_sec = reminder * 60
            if reminder not in info.get("sent_reminders", []) and reminder_sec >= seconds_left > (reminder_sec - REMINDER_WINDOW):
                await channel.send(f"@everyone ⏳ **{boss_name}** odrodzi się za {reminder} minut!")
                info.setdefault("sent_reminders", []).append(reminder)
                save_respawns()

        # Powiadomienie o odrodzeniu
        if seconds_left <= 0:
            await channel.send(f"@everyone ⚡ **{boss_name}** odrodziła się na mapie **{map_name}**, kanał: **{channel_num}**!")
            to_remove.append(boss_name)

    for boss_name in to_remove:
        legend_respawns.pop(boss_name)
        save_respawns()

# =======================
# KOMENDA TESTOWA
# =======================
@bot.command()
async def test(ctx):
    await ctx.send("Bot działa! ✅")

# =======================
# URUCHOMIENIE BOTA
# =======================
bot.run(TOKEN)
