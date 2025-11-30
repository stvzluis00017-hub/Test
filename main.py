import os
import time
import asyncio
from telethon import TelegramClient, events
from imageio_ffmpeg import get_ffmpeg_exe

API_ID = "13876032"
API_HASH = "c87c88faace9139628f6c7ffc2662bff"
BOT_TOKEN = "7660988574:AAHMZ9BU45PudZ5XMgJD4f4_OzSQoadRbRc"

client = TelegramClient(
    "bot_session",
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)

MAX_SIZE_MB = 2000    # límite lógico, no API (puedes subirlo)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def human(b):
    return f"{b/1024/1024:.2f}MB"


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🎥 Bot compresor activo.\n"
        "📥 Envíame un video y lo comprimiré a 360p con H265."
    )


@client.on(events.NewMessage)
async def handle_video(event):
    if not event.video and not event.document:
        return

    media = event.video or event.document
    size = media.size

    if size > MAX_SIZE_MB * 1024 * 1024:
        await event.reply(f"❌ Muy grande (máx {MAX_SIZE_MB}MB)")
        return

    status = await event.reply(
        f"📥 Recibido. Tamaño: {human(size)}"
        "\n🔻 Descargando..."
    )

    file_path = f"{DOWNLOAD_DIR}/{media.id}.mp4"
    await client.download_media(media, file_path)

    await status.edit(
        "📦 Descarga completada\n"
        "🔧 Comprimiendo a 360p..."
    )

    compressed = f"{DOWNLOAD_DIR}/compressed_{int(time.time())}.mp4"

    ffmpeg = get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", file_path,
        "-vf", "scale=-2:360",
        "-c:v", "libx265",
        "-preset", "slow",
        "-crf", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "64k",
        compressed
    ]

    start_t = time.time()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()

    if not os.path.exists(compressed):
        await status.edit("❌ Error al comprimir.")
        return

    dur = time.time() - start_t
    new_size = os.path.getsize(compressed)

    await status.edit(
        f"✔️ Listo!\n"
        f"⏱ {dur:.1f}s\n"
        f"📉 Final: {human(new_size)}"
    )

    await client.send_file(
        event.chat_id,
        compressed,
        caption=f"🎥 Tamaño: {human(new_size)}",
    )

    os.remove(file_path)
    os.remove(compressed)


print("🤖 Bot Telethon ejecutándose...")
client.run_until_disconnected()
