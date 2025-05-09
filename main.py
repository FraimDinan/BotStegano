from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import os

# Ganti dengan token dari BotFather
BOT_TOKEN = 'ISI TOKEN BOT'

TEMP_DIR = 'temp_files'
os.makedirs(TEMP_DIR, exist_ok=True)

# Menyimpan status dan data user
user_states = {}
user_keys = {}
user_files = {}

# Fungsi menyisipkan dengan kunci
def embed_png_with_key(host_path, secret_path, output_path, key: str):
    with open(host_path, 'rb') as f:
        host_data = f.read()
    with open(secret_path, 'rb') as f:
        secret_data = f.read()
    key_bytes = key.encode()
    with open(output_path, 'wb') as f:
        f.write(host_data + key_bytes + secret_data + key_bytes)

# Fungsi ekstraksi berdasarkan kunci
def extract_png_with_key(stego_path, output_path, key: str):
    with open(stego_path, 'rb') as f:
        data = f.read()
    key_bytes = key.encode()
    start = data.find(key_bytes)
    end = data.rfind(key_bytes)
    if start == -1 or end == -1 or start == end:
        return False
    extracted = data[start + len(key_bytes):end]
    if not extracted.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    with open(output_path, 'wb') as f:
        f.write(extracted)
    return True

# Command handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Halo! Ketik /menu untuk memulai.")

def menu(update: Update, context: CallbackContext):
    update.message.reply_text("Pilih:\n1. /hide - Menyembunyikan gambar\n2. /extract - Mengekstrak gambar tersembunyi")

def hide(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_states[user_id] = 'awaiting_key_hide'
    update.message.reply_text("Masukkan kunci untuk menyisipkan gambar.")

def extract(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_states[user_id] = 'awaiting_key_extract'
    update.message.reply_text("Masukkan kunci untuk mengekstrak gambar.")

# Handler teks (kunci)
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    state = user_states.get(user_id)

    if state == 'awaiting_key_hide':
        user_keys[user_id] = text
        user_states[user_id] = 'hide'
        user_files[user_id] = []
        update.message.reply_text("Kunci disimpan. Kirim gambar yang akan disembunyikan.")
    elif state == 'awaiting_key_extract':
        user_keys[user_id] = text
        user_states[user_id] = 'extract'
        user_files[user_id] = []
        update.message.reply_text("Kunci disimpan. Kirim gambar stego yang ingin diekstrak.")
    else:
        update.message.reply_text("Gunakan perintah /menu terlebih dahulu.")

# Handler dokumen PNG
def handle_document(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    file = update.message.document

    if not file.file_name.lower().endswith('.png'):
        update.message.reply_text("❗ Hanya mendukung file .png")
        return

    file_path = os.path.join(TEMP_DIR, f"{user_id}_{file.file_name}")
    file.get_file().download(file_path)

    state = user_states.get(user_id)
    if not state:
        update.message.reply_text("Gunakan perintah /menu terlebih dahulu.")
        return

    user_files.setdefault(user_id, []).append(file_path)

    # Mode hide
    if state == 'hide':
        if len(user_files[user_id]) == 1:
            update.message.reply_text("Gambar yang akan disembunyikan diterima. Sekarang kirim gambar penampung.")
        elif len(user_files[user_id]) == 2:
            secret_path, host_path = user_files[user_id]
            output_path = os.path.join(TEMP_DIR, f"{user_id}_stego.png")
            key = user_keys.get(user_id, '')
            embed_png_with_key(host_path, secret_path, output_path, key)
            update.message.reply_document(open(output_path, 'rb'), filename="output_stego.png")
            reset_user(user_id)
        else:
            update.message.reply_text("Terlalu banyak file. Gunakan /hide untuk memulai ulang.")
            reset_user(user_id)

    # Mode extract
    elif state == 'extract':
        if len(user_files[user_id]) == 1:
            stego_path = user_files[user_id][0]
            output_path = os.path.join(TEMP_DIR, f"{user_id}_extracted.png")
            key = user_keys.get(user_id, '')
            success = extract_png_with_key(stego_path, output_path, key)
            if success:
                update.message.reply_document(open(output_path, 'rb'), filename="extracted.png")
            else:
                update.message.reply_text("❌ Gagal mengekstrak. Cek apakah kunci benar atau file valid.")
            reset_user(user_id)

def handle_photo(update: Update, context: CallbackContext):
    update.message.reply_text("Kirim sebagai dokumen, bukan sebagai foto.")

def reset_user(user_id):
    user_states[user_id] = None
    user_files[user_id] = []
    user_keys[user_id] = None

# MAIN
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("hide", hide))
    dp.add_handler(CommandHandler("extract", extract))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(MessageHandler(Filters.document.mime_type("image/png"), handle_document))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    updater.start_polling()
    print("Bot berjalan...")
    updater.idle()

if __name__ == '__main__':
    main()
