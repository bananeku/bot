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

# =======================
# Wczytanie zapisanych respawnów
# =======================
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        legend_respawns = json.load(f)
        for k in legend_respawns:
            legend_respawns[k]["respawn_time"] = datetime.fromisoformat(legend_respawns[k]["respawn_time"])
            legend_respawns[k]["respawn_seconds"] = DEFAULT_RESPAWN_TIME
else:
    legend_respawns = {}

def save_respawns():
    data_to_save = {k: {
        "respawn_time": v["respawn_time"].isoformat(),
        "respawn_seconds": v["respawn_seconds"],
        "mapa": v.get("mapa", ""),
        "kanal": v.get("kanal", ""),
        "sent_reminders": v.get("sent_reminders", [])
    } for k, v in legend_respawns.items()}
    with open(JSON_FILE, "w") as f:
        json.dump(data_to_save, f)

# =======================
# Funkcje do Embed
# =======================
def create_embed(title, legenda, mapa, kanal, color=0xff0000):
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Legenda", value=f"**{legenda}**", inline=False)
    embed.add_field(name="Mapa", value=f"**{mapa}**", inline=True)
    embed.add_field(name="Kanał", value=f"**{kanal}**", inline=True)
    return embed

# =======================
# FUNKCJE BOTA
# =======================
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
    check_respawns.start()

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.id != LOG_CHANNEL_ID:
        return

    # Regex dopasowujący nazwę bossa, mapę i kanał
    pattern = r"zniszczył \[(.*?)\].*?Miejsce zdarzenia: (.*?), Kanał: (\d+)"
    match = re.search(pattern, message.content)
    if match:
        legenda = match.group(1)
        mapa = match.group(2)
        kanal = match.group(3)
        now = datetime.utcnow()

        alert_channel = bot.get_channel(ALERT_CHANNEL_ID)

        if legenda not in legend_respawns:
            legend_respawns[legenda] = {
                "respawn_time": now + timedelta(seconds=DEFAULT_RESPAWN_TIME),
                "respawn_seconds": DEFAULT_RESPAWN_TIME,
                "mapa": mapa,
                "kanal": kanal,
                "sent_reminders": []
            }
            embed = create_embed("🔔 Wykryto nową legendę!", legenda, mapa, kanal, color=0x00ff00)
            await alert_channel.send("@everyone", embed=embed)
        else:
            legend_respawns[legenda]["respawn_time"] = now + timedelta(seconds=DEFAULT_RESPAWN_TIME)
            legend_respawns[legenda]["mapa"] = mapa
            legend_respawns[legenda]["kanal"] = kanal
            embed = create_embed("🔔 Legenda została zabita!", legenda, mapa, kanal, color=0xffa500)
            await alert_channel.send("@everyone", embed=embed)

        save_respawns()

# =======================
# PĘTLA SPRAWDZAJĄCA RESPAWNY
# =======================
@tasks.loop(seconds=5)
async def check_respawns():
    now = datetime.utcnow()
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    to_remove = []

    for legenda, info in legend_respawns.items():
        respawn = info["respawn_time"]
        seconds_left = (respawn - now).total_seconds()

        # Przypomnienia przed respawnem
        for reminder in REMINDERS:
            reminder_sec = reminder * 60
            if reminder not in info.get("sent_reminders", []) and reminder_sec >= seconds_left > (reminder_sec - REMINDER_WINDOW):
                embed = create_embed(f"⏳ {legenda} odrodzi się za {reminder} minut!", legenda,
                                     info['mapa'], info['kanal'], color=0xffff00)
                await channel.send("@everyone", embed=embed)
                info.setdefault("sent_reminders", []).append(reminder)
                save_respawns()

        # Powiadomienie o odrodzeniu
        if seconds_left <= 0:
            embed = create_embed(f"⚡ {legenda} odrodziła się!", legenda,
                                 info['mapa'], info['kanal'], color=0xff0000)
            await channel.send("@everyone", embed=embed)
            to_remove.append(legenda)

    for legenda in to_remove:
        legend_respawns.pop(legenda)
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

