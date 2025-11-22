import os
import logging
import yt_dlp
import requests
import time
import shutil
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# --- CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0)) # ID của bạn để làm Admin

# --- WEB SERVER GIỮ SỐNG ---
app = Flask(__name__)
@app.route('/')
def home(): return "💎 SIÊU BOT ĐA NĂNG ĐANG HOẠT ĐỘNG 24/7!"
def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run_web).start()

# --- HÀM TẢI MEDIA (CORE) ---
def tai_media(url, type='video'):
    print(f"⚡ Đang tải {type}: {url}")
    filename = f"media_{int(time.time())}"
    
    ydl_opts = {
        'outtmpl': filename + '.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'geo_bypass': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    if type == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3',}]
        final_name = filename + ".mp3"
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'
        final_name = filename + ".mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return final_name
    except Exception as e:
        print(f"❌ Lỗi tải: {e}")
        return None

# --- XỬ LÝ TIN NHẮN ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Kiểm tra Link
    if "http" in text:
        # Lưu link vào context để dùng cho nút bấm
        context.user_data['current_link'] = text
        
        # Tạo bàn phím chọn
        keyboard = [
            [
                InlineKeyboardButton("🎬 Tải Video (HD)", callback_data='dl_video'),
                InlineKeyboardButton("🎵 Tải Nhạc (MP3)", callback_data='dl_audio')
            ],
            [InlineKeyboardButton("❌ Hủy", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚡ **PHÁT HIỆN LIÊN KẾT!**\n🔗 `{text}`\n\n👉 **Đại ca muốn tải cái gì?**", 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    else:
        # Chat vui vẻ (Nếu không phải link)
        if "chào" in text.lower():
            await update.message.reply_text("👑 **TRỢ LÝ ĐẠI ĐẾ** xin chào chủ nhân!")

# --- XỬ LÝ NÚT BẤM ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Phản hồi đã bấm
    
    choice = query.data
    link = context.user_data.get('current_link')
    
    if choice == 'cancel':
        await query.edit_message_text("❌ Đã hủy lệnh.")
        return

    if not link:
        await query.edit_message_text("⚠️ Lỗi: Link đã hết hạn.")
        return

    # Xử lý tải
    msg_type = "Video" if choice == 'dl_video' else "Nhạc"
    await query.edit_message_text(f"⚡ **Đang hút {msg_type} về... (Chờ 5s)**")
    
    file_type = 'video' if choice == 'dl_video' else 'audio'
    file_path = tai_media(link, file_type)
    
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        
        try:
            # NẾU FILE QUÁ NẶNG (>49MB) -> CẮT HOẶC GỬI LINK
            if file_size > 49:
                 await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ File nặng {file_size:.1f}MB! Telegram không cho gửi free. (Đang nâng cấp tính năng cắt/drive...)")
            else:
                await query.edit_message_text(f"🚀 **Đang bắn {msg_type} qua...**")
                with open(file_path, 'rb') as f:
                    if file_type == 'video':
                        await context.bot.send_video(chat_id=query.message.chat_id, video=f, caption="💎 **Hàng về!**")
                    else:
                        await context.bot.send_audio(chat_id=query.message.chat_id, audio=f, caption="🎵 **Nhạc Chill!**")
            
            os.remove(file_path) # Dọn rác
        except Exception as e:
            await query.edit_message_text(f"💀 Lỗi gửi: {e}")
    else:
        await query.edit_message_text("❌ Không tải được (Link lỗi hoặc Server chặn).")

# --- LỆNH ADMIN (QUẢN LÝ) ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("📊 **THỐNG KÊ:** Bot đang chạy ổn định trên Render!")
    else:
        await update.message.reply_text("⛔ Bạn không phải Admin!")

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print(">>> SUPER BOT STARTED...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(button_click))
        app.add_handler(CommandHandler("stats", admin_stats))
        
        app.run_polling()
