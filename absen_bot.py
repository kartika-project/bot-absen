import os
from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from datetime import datetime, timedelta

# ================= DATA =================

izin_data = {}

ACTIVITIES = {
    "beli_makan":   {"label": "beli makan",   "minutes": 15},
    "ke_balkon":    {"label": "ke balkon",    "minutes": 5},
    "antar_barang": {"label": "antar barang", "minutes": None},
    "ke_toilet":    {"label": "ke toilet",    "minutes": None},
}

# ================= /START =================

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

# ================= CALLBACK =================

async def handle_callback(update: Update, context):
    query = update.callback_query
    data = query.data or ""
    user = query.from_user
    uid = user.id
    nama = user.full_name

    await query.answer()

    if data.startswith("ACT|"):
        _, owner_str, act_key = data.split("|")
        owner_id = int(owner_str)

        if uid != owner_id:
            await query.message.reply_text(
                f"❌ Tombol izin milik user ID {owner_id} diklik oleh {nama} (id {uid}) – DITOLAK."
            )
            return

        if uid in izin_data:
            await query.message.reply_text(
                f"❌ {nama} masih punya izin aktif '{izin_data[uid]['label']}'. Akhiri dulu."
            )
            return

        info = ACTIVITIES.get(act_key)
        if not info:
            await query.message.reply_text("Aktivitas tidak dikenali.")
            return

        label = info["label"]
        minutes = info["minutes"]

        start_time = datetime.now()
        limit_time = start_time + timedelta(minutes=minutes) if minutes else None

        izin_data[uid] = {
            "label": label,
            "start": start_time,
            "limit": limit_time
        }

        end_btn = InlineKeyboardButton("✅ Akhiri Izin", callback_data=f"END|{uid}")
        markup = InlineKeyboardMarkup([[end_btn]])

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

        await query.edit_message_text(text, reply_markup=markup)
        return

    if data.startswith("END|"):
        _, owner_str = data.split("|")
        owner_id = int(owner_str)

        if uid != owner_id:
            await query.message.reply_text(
                f"❌ Tombol AKHIRI izin milik user ID {owner_id} diklik oleh {nama} – DITOLAK."
            )
            return

        if uid not in izin_data:
            await query.message.reply_text("❌ Kamu tidak punya izin aktif.")
            return

        izin = izin_data[uid]
        start_time = izin["start"]
        label = izin["label"]
        end_time = datetime.now()

        durasi = (end_time - start_time).total_seconds() / 60

        await query.edit_message_text(
            f"Izin '{label}' untuk {nama} selesai pada {end_time.strftime('%H:%M:%S')}.\n"
            f"Durasi: {durasi:.2f} menit."
        )

        del izin_data[uid]
        return

# ================= AUTO PING =================

async def auto_ping(context):
    print("Auto-ping: bot masih hidup...")

# ================= MAIN =================

def main():
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("ERROR: BOT_TOKEN belum diset.")
        return

    application = Application.builder().token(bot_token).build()

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_ping, interval=300, first=10)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()


if __name__ == "__main__":
    main()

