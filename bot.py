import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- KONFIGURASI ---
TOKEN = "7985432586:AAFOmmVvheKyVBu7HrL4Kag1KZvChynlQyg"
OWNER = "@petinggiakhirat"

# Database sederhana dalam RAM
# Struktur: { chat_id: { 'message_id': id, 'data': { 'hadir': [], 'izin': [], 'sakit': [] } } }
db_absen = {}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def generate_absensi_text(chat_id):
    """Menghasilkan teks daftar absen sesuai format yang diminta."""
    data = db_absen[chat_id]['data']
    today = datetime.now().strftime("%A, %d %B %Y")
    
    text = f"📊 **DAFTAR ABSEN**\n📅 {today}\n\n"
    
    # Bagian HADIR
    text += "✅ **HADIR**\n"
    if not data['hadir']:
        text += "  (Belum ada)\n"
    for i, entry in enumerate(data['hadir'], 1):
        text += f"{i}. {entry['name']} ({entry['time']})\n"
    
    # Bagian IZIN
    text += "\n📝 **IJIN**\n"
    if not data['izin']:
        text += "  (Belum ada)\n"
    for i, entry in enumerate(data['izin'], 1):
        text += f"{i}. {entry['name']} ({entry['reason']})\n"
    
    # Bagian SAKIT
    text += "\n🤒 **SAKIT**\n"
    if not data['sakit']:
        text += "  (Belum ada)\n"
    for i, entry in enumerate(data['sakit'], 1):
        text += f"{i}. {entry['name']} (CEPET SEMBUH GESS)\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━\n👇 **Silakan klik tombol di bawah untuk absen**"
    return text

async def start_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Reset/Inisialisasi data untuk chat ini
    db_absen[chat_id] = {
        'message_id': None,
        'users_done': {}, # Untuk blokir absen 2x
        'data': {'hadir': [], 'izin': [], 'sakit': []}
    }
    
    keyboard = [
        [InlineKeyboardButton("Hadir ✅", callback_data='h'),
         InlineKeyboardButton("Sakit 🤒", callback_data='s')],
        [InlineKeyboardButton("Ijin 📝 (Isi Alasan)", callback_data='i_start')]
    ]
    
    text = generate_absensi_text(chat_id)
    sent_message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    db_absen[chat_id]['message_id'] = sent_message.message_id
    
    try:
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id)
    except:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = update.effective_chat.id
    data = query.data

    if chat_id not in db_absen:
        await query.answer("Sesi absen tidak ditemukan. Mulai lagi dengan /absen", show_alert=True)
        return

    # Cek apakah user sudah absen
    if user.id in db_absen[chat_id]['users_done']:
        await query.answer("Kamu sudah absen hari ini!", show_alert=True)
        return

    jam = datetime.now().strftime("%H:%M")

    if data == 'h':
        db_absen[chat_id]['data']['hadir'].append({'name': user.first_name, 'time': jam})
        db_absen[chat_id]['users_done'][user.id] = True
        await query.answer("Berhasil absen hadir!")
        await update_absen_message(context, chat_id)
        
    elif data == 's':
        db_absen[chat_id]['data']['sakit'].append({'name': user.first_name})
        db_absen[chat_id]['users_done'][user.id] = True
        await query.answer("Semoga cepat sembuh!")
        await update_absen_message(context, chat_id)
        
    elif data == 'i_start':
        await query.answer()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 @{user.username or user.first_name}, ketik **alasan ijin** kamu:",
            reply_markup=ForceReply(selective=True)
        )

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return
    
    if "ketik alasan ijin kamu" in update.message.reply_to_message.text:
        user = update.message.from_user
        chat_id = update.effective_chat.id
        alasan = update.message.text
        
        if chat_id not in db_absen or user.id in db_absen[chat_id]['users_done']:
            return

        db_absen[chat_id]['data']['izin'].append({'name': user.first_name, 'reason': alasan})
        db_absen[chat_id]['users_done'][user.id] = True
        
        await update.message.delete() # Hapus pesan alasan agar grup bersih
        await update_absen_message(context, chat_id)

async def update_absen_message(context, chat_id):
    """Mengupdate pesan utama dengan list terbaru."""
    text = generate_absensi_text(chat_id)
    keyboard = [
        [InlineKeyboardButton("Hadir ✅", callback_data='h'),
         InlineKeyboardButton("Sakit 🤒", callback_data='s')],
        [InlineKeyboardButton("Ijin 📝 (Isi Alasan)", callback_data='i_start')]
    ]
    
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=db_absen[chat_id]['message_id'],
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Owner: {OWNER}\n/absen - Mulai Absen\n/start - Cek Bot")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_absen))
    app.add_handler(CommandHandler('absen', start_absen))
    app.add_handler(CommandHandler('info', info))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_reply))
    
    print("Bot Berjalan...")
    app.run_polling()
