import os
import sys
import json
import asyncio
import platform
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive


init(autoreset=True)

CONFIG = {
    "status": "online",  # online/dnd/idle
    "custom_status": "sram do wora jak do jeziora",
    # "channel_id": "1412336608178343976",  # ID kanału do monitorowania
    "channel_id": "1423090162136645715",  # ID kanału do monitorowania
    "webhook_url": "https://discord.com/api/webhooks/1423082111623237765/mvXK0CnxxJ6gsRWx5L5-Zh_MgfWa9QdxbtEdEsyHO7-Mvp1G2HwX-8eXr5qDzwgp6L0Z",  # URL webhooka do przesyłania wiadomości
    "save_to_file": True,  # Czy zapisywać wiadomości do pliku JSON
    "send_to_webhook": True,  # Czy wysyłać wiadomości webhookiem
    "heartbeat_retry": 5,  # Czas oczekiwania przed ponownym połączeniem (sekundy)
}

usertoken = "MzU1Mzg3MzYzNTc0MTUzMjE2.Ge9YM5.p5lSNkRoQID1aaWI7XvAqM2GgOldgR6U_r2-Tc"
if not usertoken:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add a TOKEN inside Secrets.")
    sys.exit()

if not CONFIG["channel_id"]:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add a CHANNEL_ID inside Secrets.")
    sys.exit()

if CONFIG["send_to_webhook"] and not CONFIG["webhook_url"]:
    print(f"{Fore.WHITE}[{Fore.YELLOW}*{Fore.WHITE}] WEBHOOK_URL not set - webhook notifications disabled")
    CONFIG["send_to_webhook"] = False

headers = {"Authorization": usertoken, "Content-Type": "application/json"}

validate = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
if validate.status_code != 200:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Invalid token. Please check it again.")
    sys.exit()

userinfo = validate.json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

def save_message_to_json(message_data):
    """Zapisuje wiadomość do pliku JSON"""
    try:
        try:
            with open('messages.json', 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messages = []
        
        messages.append(message_data)
        
        with open('messages.json', 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)
            
        print(f"{Fore.WHITE}[{Fore.GREEN}✓{Fore.WHITE}] Saved message from {message_data.get('author', {}).get('username', 'Unknown')}")
        
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}✗{Fore.WHITE}] Error saving message: {e}")

async def send_webhook(message_data):
    """Wysyła wiadomość przez webhook Discord"""
    if not CONFIG["send_to_webhook"] or not CONFIG["webhook_url"]:
        return
    
    try:
        content = message_data.get('content', 'No content') or "Empty message"
        
        payload = {
            # "embeds": [embed],
            "content": f"{content}",
            "username": "ctnn.xyz",
            "avatar_url": "https://ctnn.xyz/meow.gif"
        }
        
        response = requests.post(CONFIG["webhook_url"], json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print(f"{Fore.WHITE}[{Fore.BLUE}↗{Fore.WHITE}] Sent webhook for message from {message_data.get('author', {}).get('username', 'Unknown')}")
        else:
            print(f"{Fore.WHITE}[{Fore.RED}✗{Fore.WHITE}] Webhook error: {response.status_code}")
            
    except Exception as e:
        print(f"{Fore.WHITE}[{Fore.RED}✗{Fore.WHITE}] Webhook send error: {e}")

def process_message(message_data):
    print(f"{Fore.YELLOW}[DEBUG] Full message data: {json.dumps(message_data, indent=2)}")

    """Przetwarza otrzymaną wiadomość"""
    print(f"{Fore.YELLOW}[DEBUG] Full message data: {json.dumps(message_data, indent=2)}")
    content = message_data.get('content')
    if content is None:
        print(f"{Fore.RED}❌ BRAK TREŚCI WIADOMOŚCI!")
        content = "No content available"
    elif content == "":
        content = "Empty message"
    
    message_to_save = {
        'id': message_data.get('id'),
        'content': content,
        'timestamp': message_data.get('timestamp'),
        'author': {
            'id': message_data.get('author', {}).get('id'),
            'username': message_data.get('author', {}).get('username'),
            'discriminator': message_data.get('author', {}).get('discriminator'),
            'global_name': message_data.get('author', {}).get('global_name')
        },
        'channel_id': message_data.get('channel_id'),
        'guild_id': message_data.get('guild_id'),
        'attachments': len(message_data.get('attachments', [])),
        'embeds': len(message_data.get('embeds', []))
    }

    if CONFIG["save_to_file"]:
        save_message_to_json(message_to_save)

    asyncio.create_task(send_webhook(message_to_save))

    author = message_data.get('author', {})
    author_name = f"{author.get('username', 'Unknown')}#{author.get('discriminator', '0000')}"
    
    print(f"{Fore.WHITE}[{Fore.CYAN}💬{Fore.WHITE}] {Fore.YELLOW}{author_name}{Fore.WHITE}: {content}")
async def discord_connection():
    """Główna funkcja połączenia z Discord Gateway"""
    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                print(f"{Fore.WHITE}[{Fore.GREEN}→{Fore.WHITE}] Connected to Discord Gateway")
                
                hello = json.loads(await ws.recv())
                heartbeat_interval = hello['d']['heartbeat_interval'] / 1000
                
                identify = {
                    "op": 2,
                    "d": {
                        "token": usertoken,
                        "properties": {
                            "$os": platform.system(),
                            "$browser": "Python",
                            "$device": "Python"
                        },
                        "intents": 32767 + 32768 + 524288,
                        "presence": {
                            "status": CONFIG["status"],
                            "afk": False,
                            "activities": [{
                                "type": 4,
                                "state": CONFIG["custom_status"],
                                "name": "Custom Status",
                                "id": "custom"
                            }]
                        }
                    }
                }
                await ws.send(json.dumps(identify))

                async for message in ws:
                    data = json.loads(message)

                    if data['op'] == 1:
                        await ws.send(json.dumps({"op": 1, "d": None}))

                    elif data.get('t') == 'MESSAGE_CREATE':
                        message_data = data['d']
                        if message_data.get('channel_id') == CONFIG["channel_id"]:
                            process_message(message_data)

                    elif data.get('t') == 'READY':
                        print(f"{Fore.WHITE}[{Fore.GREEN}✓{Fore.WHITE}] Bot is ready and monitoring channel {CONFIG['channel_id']}")
                        
        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.WHITE}[{Fore.RED}⚠{Fore.WHITE}] Connection closed, reconnecting in {CONFIG['heartbeat_retry']}s...")
            await asyncio.sleep(CONFIG["heartbeat_retry"])
        
        except Exception as e:
            print(f"{Fore.WHITE}[{Fore.RED}⚠{Fore.WHITE}] Connection error: {e}, reconnecting in {CONFIG['heartbeat_retry']}s...")
            await asyncio.sleep(CONFIG["heartbeat_retry"])

async def main():
    """Główna funkcja"""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    
    print(f"{Fore.CYAN}╔══════════════════════════════════════╗")
    print(f"{Fore.CYAN}║                ctnn.xyz              ║")
    print(f"{Fore.CYAN}╚══════════════════════════════════════╝")
    print(f"{Fore.WHITE}Logged in as: {Fore.GREEN}{username}#{discriminator}")
    print(f"{Fore.WHITE}User ID: {Fore.GREEN}{userid}")
    print(f"{Fore.WHITE}Monitoring channel: {Fore.GREEN}{CONFIG['channel_id']}")
    print(f"{Fore.WHITE}Save to file: {Fore.GREEN if CONFIG['save_to_file'] else Fore.RED}{CONFIG['save_to_file']}")
    print(f"{Fore.WHITE}Webhook notifications: {Fore.GREEN if CONFIG['send_to_webhook'] else Fore.RED}{CONFIG['send_to_webhook']}")
    print(f"{Fore.CYAN}┌──────────────────────────────────────┐")
    
    await discord_connection()

    await send

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}")
        print(f"{Fore.YELLOW}Restarting in 10 seconds...")
        asyncio.sleep(10)
        asyncio.run(main())
