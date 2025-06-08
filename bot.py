import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup,
    CallbackQuery, BotCommand
)
from aiogram.client.default import DefaultBotProperties
from yt_dlp import YoutubeDL
import aiohttp
from collections import defaultdict

API_TOKEN = "8082756911:AAGRgAJ8yBz-UGuHQU00N0CABxSmyNM03F8"
SHAZAM_API_KEY = "6f730辺c904emsh5b4f04597554a44p14aa86jsn34b9024d2953"
ADMIN_ID = 1930843463
BOT_USERNAME = "DownTownmBot"

dp = Dispatcher()
router = Router()
user_lang = {}
user_links = {}
user_stats = defaultdict(lambda: {"videos": 0, "audios": 0})
known_users = set()
broadcast_data = {}

texts = {
    "choose_language": {
        "uz": "Iltimos, tilni tanlang:",
        "en": "Please choose your language:",
        "ru": "Пожалуйста, выберите язык:"
    },
    "language_set": {
        "uz": "Til muvaffaqiyatli o'zgartirildi!",
        "en": "Language has been changed!",
        "ru": "Язык был изменён!"
    },
    "send_media": {
        "uz": "Endi link yoki musiqa yuboring",
        "en": "Now send a link or music",
        "ru": "Теперь отправьте ссылку или музыку"
    },
    "searching_music": {
        "uz": "🔍 Musiqa qidirilmoqda...",
        "en": "🔍 Searching for music...",
        "ru": "🔍 Идёт поиск музыки..."
    },
    "music_not_found": {
        "uz": "❌ Musiqa aniqlanmadi.",
        "en": "❌ Music not recognized.",
        "ru": "❌ Музыка не распознана."
    },
    "music_found": {
        "uz": "🔍 Topildi:🎵 {title}👤 {artist}",
        "en": "🔍 Found:🎵 {title}👤 {artist}",
        "ru": "🔍 Найдено:🎵 {title}👤 {artist}"
    },
    "footer": {
        "uz": "@userbot TEZ VA OSON",
        "en": "@userbot FAST & EASY",
        "ru": "@userbot БЫСТРО И ЛЕГКО"
    },
    "link_not_found": {
        "uz": "❌ Link topilmadi.",
        "en": "❌ Link not found.",
        "ru": "❌ Ссылка не найдена."
    },
    "failed_download": {
        "uz": "❌ Yuklab bo‘lmadi.",
        "en": "❌ Failed to download.",
        "ru": "❌ Не удалось загрузить."
    },
    "downloading": {
        "uz": "📥 Yuklab olinmoqda...",
        "en": "📥 Downloading...",
        "ru": "📥 Загрузка..."
    },
    "choose_quality": {
        "uz": "📺 Qaysi sifatda yuklab olmoqchisiz?",
        "en": "📺 Which quality do you want to download?",
        "ru": "📺 В каком качестве загрузить?"
    }
}

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'zbek 🇺🇿", callback_data="lang_uz")],
        [InlineKeyboardButton(text="English 🇺🇸", callback_data="lang_en")],
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")]
    ])

def quality_keyboard(video_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{q}p", callback_data=f"yt_{video_id}_{q}")]
        for q in ["244", "360", "480", "720", "1080"]
    ] + [
        [InlineKeyboardButton(text="🎵 Audio", callback_data=f"yt_{video_id}_audio")],
        [InlineKeyboardButton(text="📄 Subtitle", callback_data=f"yt_{video_id}_subs")]
    ])
    return kb

def group_join_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Guruhga qo‘shish", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])

def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")]
    ])

@router.callback_query(F.data == "inline_yes")
async def inline_yes(callback: CallbackQuery):
    uid = callback.from_user.id
    broadcast_data[uid]["step"] = "inline_count"
    await callback.message.answer("Nechta tugma qo‘shmoqchisiz? (1–10):")
    await callback.answer()

@router.callback_query(F.data == "inline_no")
async def inline_no(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    text = broadcast_data[uid].get("text", "")
    count = 0
    for user in known_users:
        try:
            await bot.send_message(user, text)
            count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to {user}: {e}")
    await callback.message.answer(f"✅ {count} foydalanuvchiga yuborildi.")
    broadcast_data.pop(uid, None)
    await callback.answer()

@router.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in known_users:
        known_users.add(user_id)
        await message.answer("Tilni tanlang:", reply_markup=language_keyboard())
    else:
        lang = user_lang.get(user_id, "uz")
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(texts["send_media"][lang])

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_lang[callback.from_user.id] = lang
    await callback.message.answer(texts["language_set"][lang])
    await callback.message.answer(texts["send_media"][lang])
    await callback.answer()

@router.message(Command("settings"))
async def settings_command(message: Message):
    await message.answer("🌐 Qayta til tanlang:", reply_markup=language_keyboard())

@router.message(Command("admin"))
async def admin_command(message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("🔐 Admin panel:", reply_markup=admin_panel_keyboard())
    else:
        lang = user_lang.get(user_id, "uz")
        await message.answer("❌ Siz admin emassiz.")

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    total_users = len(known_users)
    await callback.message.answer(f"👥 Botdan foydalanuvchilar soni: {total_users}")
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    user_id = callback.from_user.id
    broadcast_data[user_id] = {"step": "text"}
    await callback.message.answer("📢 Xabar matnini yuboring:")
    await callback.answer()

@router.callback_query(F.data.startswith("yt_"))
async def handle_youtube(callback: CallbackQuery):
    _, msg_id, opt = callback.data.split("_")
    url = user_links.get(int(msg_id))
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "uz")

    if not url:
        await callback.message.answer(texts["link_not_found"][lang])
        await callback.answer()
        return

    await callback.answer("⏳ Yuklanmoqda...")
    file = None
    if opt == "audio":
        file = await download_audio(url)
        user_stats[user_id]["audios"] += 1
    elif opt == "subs":
        file = await download_subtitle(url)
    else:
        file = await download_video(url, opt)
        user_stats[user_id]["videos"] += 1

    if file and os.path.exists(file):
        await callback.message.answer_document(types.FSInputFile(file))
        os.remove(file)
        await callback.message.answer(texts["footer"][lang], reply_markup=group_join_button())
    else:
        await callback.message.answer(texts["failed_download"][lang])
    await callback.answer()

@router.message(F.voice | F.audio)
async def recognize_music(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "uz")
    file = await bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
    audio_bytes = await bot.download_file(file.file_path)

    await message.answer("🎶 Shazam orqali aniqlanmoqda...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://shazam.p.rapidapi.com/songs/v2/detect",
                headers={
                    "X-RapidAPI-Key": SHAZAM_API_KEY,
                    "X-RapidAPI-Host": "shazam.p.rapidapi.com"
                },
                params={"timezone": "UTC", "locale": "en-US"},
                data=audio_bytes.read()
            ) as resp:
                result = await resp.json()
                track = result.get("track")
                if track:
                    title = track["title"]
                    artist = track["subtitle"]
                    await message.answer(texts["music_found"][lang].format(title=title, artist=artist))
                else:
                    await message.answer(texts["music_not_found"][lang])
    except Exception as e:
        logging.error(f"Shazam error: {e}")
        await message.answer(texts["music_not_found"][lang])

@router.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "uz")
    text = message.text.lower() if message.text else ""

    data = broadcast_data.get(user_id)
    if data:
        step = data.get("step")
        if step == "text":
            data["text"] = message.text
            data["step"] = "inline_ask"
            await message.answer("Inline tugma qo‘shasizmi?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Ha", callback_data="inline_yes"),
                 InlineKeyboardButton(text="❌ Yo‘q", callback_data="inline_no")]
            ]))
            return
        elif step == "inline_count":
            try:
                count = int(message.text)
                if 1 <= count <= 10:
                    data["btn_count"] = count
                    data["buttons"] = []
                    data["step"] = "inline_label"
                    await message.answer("Tugmalar uchun nomlarni yuboring:")
                else:
                    await message.answer("❗ 1 dan 10 gacha bo‘lgan sonni yuboring.")
            except ValueError:
                await message.answer("❗ Raqam yuboring.")
            return
        elif step == "inline_label":
            data["buttons"].append({"text": message.text})
            if len(data["buttons"]) == data["btn_count"]:
                data["step"] = "inline_url"
                await message.answer("Endi har bir tugmaga URL yuboring:")
            return
        elif step == "inline_url":
            index = len([b for b in data["buttons"] if "url" in b])
            data["buttons"][index]["url"] = message.text
            if len([b for b in data["buttons"] if "url" in b]) == data["btn_count"]:
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=b["text"], url=b["url"])] for b in data["buttons"]
                ])
                count = 0
                for user in known_users:
                    try:
                        await bot.send_message(user, data["text"], reply_markup=markup)
                        count += 1
                    except Exception as e:
                        logging.error(f"Failed to send broadcast to {user}: {e}")
                await message.answer(f"✅ {count} foydalanuvchiga yuborildi.")
                broadcast_data.pop(user_id, None)
            return

    if "youtube.com" in text or "youtu.be" in text:
        user_links[message.message_id] = text
        await message.answer(texts["choose_quality"][lang], reply_markup=quality_keyboard(message.message_id))
    elif "instagram.com" in text or "tiktok.com" in text:
        await message.answer(texts["downloading"][lang])
        file = await download_media(text)
        if file and os.path.exists(file):
            await message.answer_document(types.FSInputFile(file))
            os.remove(file)
            await message.answer(texts["footer"][lang], reply_markup=group_join_button())
        else:
            await message.answer(texts["failed_download"][lang])
    else:
        if message.reply_to_message:
            try:
                await message.reply_to_message.delete()
            except Exception:
                pass
        await message.answer(texts["searching_music"][lang])

async def download_video(url, quality):
    filename = f"yt_{quality}.mp4"
    opts = {
        'outtmpl': filename,
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'quiet': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': 'web'}},
        'user_agent': 'Mozilla/5.0'
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        logging.error(f"Video download error: {e}")
        return None

async def download_audio(url):
    filename = "yt_audio.mp3"
    opts = {
        'outtmpl': filename,
        'format': 'bestaudio/best',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3'
        }]
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        logging.error(f"Audio download error: {e}")
        return None

async def download_subtitle(url):
    opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'outtmpl': 'subtitle',
        'skip_download': True,
        'quiet': True
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        filename = "subtitle.en.vtt"
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        logging.error(f"Subtitle download error: {e}")
        return None

async def download_media(url):
    filename = "media.mp4"
    opts = {
        'outtmpl': filename,
        'format': 'best',
        'quiet': True
    }
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([url])
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        logging.error(f"Media download error: {e}")
        return None

async def main():
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands([
        BotCommand(command="settings", description="🌐 Tilni o‘zgartirish")
    ])
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
