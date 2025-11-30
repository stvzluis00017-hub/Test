import os
import time
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from imageio_ffmpeg import get_ffmpeg_exe


TOKEN = os.getenv("TELEGRAM_TOKEN")  # define en variables de entorno
MAX_SIZE = 900 * 1024 * 1024         # 900 MB


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 Bienvenido!\nEnvía un video y lo comprimiré automáticamente\n📉 Resolución: 360p\n📦 Codec: H.265"
    )


def human_size(b):
    return f"{b/1024/1024:.2f}MB"


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video

    if video.file_size > MAX_SIZE:
        await update.message.reply_text("❌ Archivo demasiado grande (máx. 900MB)")
        return

    processing_msg = await update.message.reply_text("📥 Descargando video...")

    file = await video.get_file()
    os.makedirs("downloads", exist_ok=True)
    input_path = f"downloads/{video.file_name or 'video.mp4'}"
    output_path = f"downloads/compressed_{int(time.time())}.mp4"

    await file.download_to_drive(input_path)

    await processing_msg.edit_text(
        f"📦 Original: {human_size(video.file_size)}\n🔧 Comprimiendo a 360p..."
    )

    start_time = time.time()
    ffmpeg = get_ffmpeg_exe()

    # ✨ PARÁMETROS ÓPTIMOS (muy agresivo)
    # x265 + crf alto + preset slow
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", "scale=-2:360",
        "-c:v", "libx265",
        "-preset", "slow",
        "-crf", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "64k",
        output_path
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    if proc.returncode != 0 or not os.path.exists(output_path):
        await processing_msg.edit_text("❌ Error al comprimir video")
        return

    duration = time.time() - start_time
    compressed_size = os.path.getsize(output_path)

    await processing_msg.edit_text(
        f"✔️ Finalizado\n⏱ Tiempo: {duration:.1f}s\n"
        f"📦 Original: {human_size(video.file_size)}\n"
        f"📉 Comprimido: {human_size(compressed_size)}"
    )

    await context.bot.send_video(
        chat_id=update.message.chat.id,
        video=InputFile(output_path),
        caption=f"🎥 Tamaño final: {human_size(compressed_size)}"
    )

    os.remove(input_path)
    os.remove(output_path)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.run_polling()


if __name__ == "__main__":
    main()
