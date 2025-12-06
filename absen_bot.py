import os
from dotenv import load_dotenv
load_dotenv()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from datetime import datetime, timedelta

# Simpan data izin per user
# { user_id: { "label": str, "start": datetime, "limit": datetime|None } }
izin_data = {}

# Definisi aktivitas
ACTIVITIES = {
    "beli_makan":   {"label": "beli makan",   "minutes": 15},
    "ke_balkon":    {"label": "ke balkon",    "minutes": 5},
    "antar_barang": {"label": "antar barang", "minutes": None},
    "ke_toilet":    {"label": "ke toilet",    "minutes": None},
}

# ============= /start =============
async def start(update: Update, context):
    user = update.effective_user
    uid = user.id

    keyboard = [
        [InlineKeyboardButton("Beli Makan",   callback_data=f"ACT|{uid}|beli_makan")],
        [InlineKeyboardButton("Ke Balkon",    callback_data=f"ACT|{uid}|ke_balkon")],
        [InlineKeyboardButton("Antar Barang", callback_data=f"ACT|{uid}|antar_barang")],
        [InlineKeyboardButton("Ke Toilet",    callback_data=f"ACT|{uid}|ke_toilet")],
    ]

    await update.message.reply_text(
        f"Halo {user.full_name}, Mau kemana?:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ============= Handler semua tombol =============
async def handle_callback(update: Update, context):
    query = update.callback_query
    data = query.data or ""
    user = query.from_user
    uid = user.id
    nama = user.full_name

    print("Callback:", data, "dari", uid, nama)  # debug ke CMD
    await query.answer()

    # ---------- PILIH AKTIVITAS ----------
    if data.startswith("ACT|"):
        parts = data.split("|")
        if len(parts) != 3:
            await query.message.reply_text("Data tombol tidak valid.")
            return

        _, owner_str, act_key = parts
        try:
            owner_id = int(owner_str)
        except ValueError:
            await query.message.reply_text("Data tombol rusak.")
            return

        # Bukan pemilik tombol → tolak dan kasih tau di chat
        if uid != owner_id:
            await query.message.reply_text(
                f"❌ Tombol izin milik user ID {owner_id} diklik oleh {nama} (id {uid}) – DITOLAK."
            )
            return

        # Sudah punya izin aktif
        if uid in izin_data:
            await query.message.reply_text(
                f"❌ {nama} masih punya izin aktif '{izin_data[uid]['label']}'. Akhiri dulu."
            )
            return

        if act_key not in ACTIVITIES:
            await query.message.reply_text("Aktivitas tidak dikenali.")
            return

        info = ACTIVITIES[act_key]
        label = info["label"]
        minutes = info["minutes"]

        start_time = datetime.now()
        limit_time = start_time + timedelta(minutes=minutes) if minutes is not None else None

        izin_data[uid] = {
            "label": label,
            "start": start_time,
            "limit": limit_time,
        }

        # Tombol end
        end_button = InlineKeyboardButton("✅ Akhiri Izin", callback_data=f"END|{uid}")
        reply_markup = InlineKeyboardMarkup([[end_button]])

        if limit_time:
            text = (
                f"{nama} izin '{label}' dimulai pada {start_time.strftime('%H:%M:%S')}.\n"
                f"Harus kembali sebelum {limit_time.strftime('%H:%M:%S')}.\n\n"
                f"Udah balik? jangan lupa klik Akhiri Izin."
            )
        else:
            text = (
                f"{nama} izin '{label}' dimulai pada {start_time.strftime('%H:%M:%S')}.\n\n"
                f"Udah balik? jangan lupa klik Akhiri Izin."
            )

        await query.edit_message_text(text, reply_markup=reply_markup)
        return

    # ---------- AKHIRI IZIN ----------
    if data.startswith("END|"):
        parts = data.split("|")
        if len(parts) != 2:
            await query.message.reply_text("Data tombol tidak valid.")
            return

        _, owner_str = parts
        try:
            owner_id = int(owner_str)
        except ValueError:
            await query.message.reply_text("Data tombol rusak.")
            return

        # Bukan pemilik izin → tolak
        if uid != owner_id:
            await query.message.reply_text(
                f"❌ Tombol AKHIRI izin milik user ID {owner_id} diklik oleh {nama} (id {uid}) – DITOLAK."
            )
            return

        if uid not in izin_data:
            await query.message.reply_text("❌ Kamu tidak punya izin aktif.")
            return

        data_izin = izin_data[uid]
        start_time = data_izin["start"]
        label = data_izin["label"]
        end_time = datetime.now()

        durasi = end_time - start_time
        durasi_menit = durasi.total_seconds() / 60

        await query.edit_message_text(
            f"Izin '{label}' untuk {nama} selesai pada {end_time.strftime('%H:%M:%S')}.\n"
            f"Durasi: {durasi_menit:.2f} menit."
        )

        del izin_data[uid]
        return

    # Kalau pattern gak dikenal
    await query.message.reply_text("Tombol tidak dikenal.")


# ============= AUTO PING =============
async def auto_ping(context):
    # Ini cuma buat memastikan bot "bergerak" tiap beberapa menit
    # Supaya kalau nanti di-host di server (Railway/Render) tidak cepat sleep
    print("Auto-ping: bot masih hidup...")


# ============= MAIN =============
def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("ERROR: BOT_TOKEN belum diset di environment variable.")
        return

    application = (
        Application.builder()
        .token(bot_token)
        .updater(None)  # penting: jangan pakai Updater lama
        .build()
    )

    job_queue = application.job_queue
    if job_queue is not None:
        job_queue.run_repeating(auto_ping, interval=300, first=10)
    else:
        print("PERINGATAN: job_queue None, auto-ping tidak aktif.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

