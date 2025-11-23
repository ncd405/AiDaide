import os
import logging
import requests
import time
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# --- CẤU HÌNH ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# --- KẾT NỐI AI (GEMINI) ---
import google.generativeai as genai
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    chat_session = model.start_chat(history=[])

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "💎 BOT V23 (COBALT ENGINE) ONLINE!"
def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run_web).start()

# --- HÀM TẢI MEDIA (DÙNG API COBALT - KHÔNG LO CHẶN IP) ---
def tai_media_cobalt(url, is_audio=False):
    print(f"⚡ Gửi yêu cầu Cobalt: {url}")
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "max",
        "aFormat": "mp3",
        "filenamePattern": "basic",
        "isAudioOnly": is_audio
    }
    
    try:
        response = requests.post(api_url, json=data, headers=headers).json()
        
        if 'url' in response:
            return response['url']
        elif 'picker' in response: # Nếu có nhiều video
            return response['picker'][0]['url']
        else:
            print(f"Lỗi Cobalt: {response}")
            return None
    except Exception as e:
        print(f"Lỗi kết nối API: {e}")
        return None

# --- XỬ LÝ TIN NHẮN ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    if "http" in text:
        context.user_data['current_link'] = text
        kb = [[InlineKeyboardButton("🎬 Video HD", callback_data='dl_video'), InlineKeyboardButton("🎵 Nhạc MP3", callback_data='dl_audio')]]
        await update.message.reply_text(f"🔗 Link nhận diện!\n👉 Chọn định dạng:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        if GOOGLE_API_KEY:
            try:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                response = chat_session.send_message(text)
                await update.message.reply_text(response.text, parse_mode=ParseMode.MARKDOWN)
            except: await update.message.reply_text("Lag rồi đại ca ơi!")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    link = context.user_data.get('current_link')
    
    if not link: return
    
    is_audio = (choice == 'dl_audio')
    type_str = "Nhạc" if is_audio else "Video"
    
    await query.edit_message_text(f"⚡ Đang nhờ Server Cobalt tải {type_str}...")
    
    # Lấy link tải trực tiếp từ API
    direct_url = tai_media_cobalt(link, is_audio)
    
    if direct_url:
        try:
            await query.edit_message_text(f"🚀 Đang bắn {type_str} qua...")
            
            if is_audio:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=direct_url, caption="🎵 Nhạc về!")
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=direct_url, caption="💎 Video sạch (No Watermark)!")
        
        except Exception as e:
            # Nếu file quá nặng không gửi được -> Gửi link tải
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ File quá nặng (>50MB)!\n🚀 **Bấm vào đây tải ngay:**\n{direct_url}",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await query.edit_message_text("❌ Lỗi: Link này Cobalt chưa hỗ trợ hoặc Server đang bận!")

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print(">>> BOT V23 (COBALT) STARTED...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(button_click))
        app.run_polling()
