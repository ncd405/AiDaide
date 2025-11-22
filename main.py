import os
import asyncio
import time
from flask import Flask
from threading import Thread
from telethon import TelegramClient
from colorama import Fore, Style, init

init(autoreset=True)

# --- CẤU HÌNH ---
API_ID = os.environ.get('API_ID')
API_HASH = os.environ.get('API_HASH')
PHONE = os.environ.get('PHONE_NUMBER')
BOT_USERNAME = "@BlumCryptoBot" # Bot muốn đào

# --- TIM NHÂN TẠO (WEB SERVER) ---
# Cái này giúp Render nhận diện app đang chạy và không tắt nó
app = Flask(__name__)

@app.route('/')
def home():
    return "💎 MÁY ĐÀO COIN ĐANG CHẠY 24/7!"

def run_web():
    # Render cung cấp cổng qua biến PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- LOGIC ĐÀO COIN ---
client = TelegramClient('session_miner', API_ID, API_HASH)

async def miner():
    print(f"{Fore.YELLOW}🚀 ĐANG KẾT NỐI TELEGRAM...{Style.RESET_ALL}")
    await client.start(phone=PHONE)
    print(f"{Fore.GREEN}✅ ĐĂNG NHẬP THÀNH CÔNG!{Style.RESET_ALL}")
    
    while True:
        try:
            print(f"\n{Fore.CYAN}🔨 Gõ cửa {BOT_USERNAME}...{Style.RESET_ALL}")
            await client.send_message(BOT_USERNAME, '/start')
            print(f"{Fore.GREEN}✅ Đã gửi lệnh!{Style.RESET_ALL}")
            
            print(f"{Fore.BLUE}💤 Ngủ 1 tiếng...{Style.RESET_ALL}")
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            await asyncio.sleep(60)

if __name__ == '__main__':
    keep_alive() # Bật tim nhân tạo
    client.loop.run_until_complete(miner()) # Chạy máy đào
