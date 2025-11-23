import os
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from flask import Flask
from threading import Thread
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, vfx

# --- CẤU HÌNH ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHO_ANH = 1 # Trạng thái chờ gửi ảnh

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "🎬 BOT EDIT VIDEO IS LIVE!"
def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run_web).start()

# --- HÀM DỰNG PHIM (MOVIE MAKER) ---
def make_beat_video(user_id, photo_paths):
    output_path = f"video_{user_id}_{int(time.time())}.mp4"
    try:
        # Cấu hình mẫu: 2 Ảnh, mỗi ảnh 3 giây, nhạc nền
        clips = []
        for p in photo_paths:
            # Tạo clip từ ảnh, dài 3s, resize chuẩn TikTok
            clip = ImageClip(p).set_duration(3).resize(height=960)
            # Hiệu ứng Zoom nhẹ (Ken Burns) - Giả lập bằng code
            # (MoviePy cơ bản, để render nhanh trên Free Tier)
            clips.append(clip)
        
        # Ghép lại
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Thêm nhạc (Cắt đúng độ dài video)
        if os.path.exists("beat.mp3"):
            audio = AudioFileClip("beat.mp3").subclip(0, final_video.duration)
            final_video = final_video.set_audio(audio)
            
        # Xuất file (Preset ultrafast để render nhanh)
        final_video.write_videofile(output_path, fps=24, codec="libx264", preset="ultrafast", audio_codec="aac")
        return output_path
    except Exception as e:
        print(f"Lỗi Render: {e}")
        return None

# --- XỬ LÝ LỆNH ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Tạo Video Beat (Cần 2 Ảnh)", callback_data='mau_1')]]
    await update.message.reply_text(
        "👑 **XƯỞNG PHIM AI ĐẠI ĐẾ**\nChọn mẫu muốn làm:", 
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )
    return ConversationHandler.END

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'mau_1':
        await query.edit_message_text("⚡ **Đã chọn Mẫu Beat!**\n👉 Hãy gửi cho anh **2 Tấm Ảnh** (Gửi từng tấm một).")
        context.user_data['photos'] = []
        return CHO_ANH

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"photo_{update.message.message_id}.jpg"
    await photo_file.download_to_drive(file_path)
    
    context.user_data['photos'].append(file_path)
    count = len(context.user_data['photos'])
    
    if count < 2:
        await update.message.reply_text(f"📸 Đã nhận {count}/2 ảnh. Gửi tiếp đi em!")
        return CHO_ANH
    else:
        msg = await update.message.reply_text("⏳ **Đủ ảnh rồi! Đang dựng phim... (Đợi 10s)**")
        
        # Render Video
        video_path = make_beat_video(update.effective_user.id, context.user_data['photos'])
        
        if video_path and os.path.exists(video_path):
            await update.message.reply_video(video=open(video_path, 'rb'), caption="💎 **Video của em đây!**")
            os.remove(video_path)
        else:
            await update.message.reply_text("❌ Render lỗi rồi đại ca ơi!")
            
        # Dọn dẹp ảnh
        for p in context.user_data['photos']:
            if os.path.exists(p): os.remove(p)
        context.user_data['photos'] = []
        
        await msg.delete()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy.")
    return ConversationHandler.END

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_click)],
            states={
                CHO_ANH: [MessageHandler(filters.PHOTO, receive_photo)]
            },
            fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)]
        )
        
        app.add_handler(CommandHandler('start', start))
        app.add_handler(conv_handler)
        app.run_polling()
