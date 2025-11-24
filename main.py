import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import google.generativeai as genai
import PIL.Image

# --- CẤU HÌNH ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
# Link bán đồ phong thủy (Affiliate của bạn)
LINK_PHONG_THUY = "https://shope.ee/..." 

# --- KẾT NỐI NÃO BỘ VISION ---
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

# --- WEB SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "🔮 THẦY BÓI AI ONLINE!"
def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run_web).start()

# --- NHÂN CÁCH THẦY BÓI ---
PROMPT_BOI = """
Hãy đóng vai một "Thầy Bói AI" đanh đá, hài hước và cực kỳ phũ phàng (Toxic nhưng vui).
Nhiệm vụ: Nhìn vào bức ảnh người dùng gửi và "phán" về tính cách, tương lai hoặc tình duyên của họ dựa trên chi tiết trong ảnh.
Quy tắc:
1. Ngôn ngữ: Tiếng Việt, dùng từ lóng giới trẻ (Gen Z).
2. Độ dài: Khoảng 3-4 câu.
3. Kết thúc: Luôn khuyên họ nên tu tâm dưỡng tính hoặc mua đồ giải hạn.
"""

# --- XỬ LÝ ẢNH (XEM TƯỚNG) ---
async def xem_tuong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return

    msg = await update.message.reply_text("🔮 **Thầy đang soi... Đừng có rung!**", parse_mode='Markdown')
    
    try:
        # Tải ảnh về
        photo_file = await update.message.photo[-1].get_file()
        file_path = "temp.jpg"
        await photo_file.download_to_drive(file_path)
        
        # Gửi sang Google Gemini Vision
        img = PIL.Image.open(file_path)
        response = model.generate_content([PROMPT_BOI, img])
        loi_phan = response.text
        
        # Gửi kết quả kèm nút bán hàng
        kb = [[InlineKeyboardButton("📿 Mua Bùa Giải Hạn (Giảm 50%)", url=LINK_PHONG_THUY)]]
        
        await msg.edit_text(
            f"⚡ **THẦY PHÁN:**\n\n{loi_phan}\n\n👇 **Muốn đổi vận thì bấm dưới:**",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='Markdown'
        )
        
        os.remove(file_path)
    except Exception as e:
        await msg.edit_text(f"❌ Thầy bị che mắt rồi (Lỗi: {e})")

# --- XỬ LÝ TEXT ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 **Gửi ảnh Selfie hoặc Bàn Tay vào đây để Thầy xem tướng cho!**")

if __name__ == '__main__':
    keep_alive()
    if TELEGRAM_TOKEN:
        print(">>> THAY BOI STARTED...")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.PHOTO, xem_tuong))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.run_polling()
