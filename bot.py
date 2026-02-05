import asyncio
import logging
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp

# --- КОНФИГУРАЦИЯ ---
# Токен бота (вставлен автоматически)
API_TOKEN = ''
# --------------------

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
# .strip() удаляет случайные пробелы, которые могли попасть при копировании
bot = Bot(token=API_TOKEN.strip())
dp = Dispatcher()

# Внутренняя функция для скачивания через yt-dlp (синхронная)
def _download_internal(opts, url):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

# Асинхронная обертка для скачивания
async def download_video_task(url, message: types.Message):
    # Генерируем уникальное имя файла
    output_filename = f"video_{message.from_user.id}_{int(time.time())}.mp4"
    
    # Настройки для yt-dlp с обходом защиты (403 Forbidden)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'noplaylist': True,
        'quiet': True,
        # Важные опции для обхода блокировок YouTube
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'nocheckcertificate': True,
        # Используем Android клиент, так как веб-клиент часто получает 403
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
            }
        }
    }

    status_msg = await message.answer("⏳ <b>Начинаю скачивание видео...</b>\nЭто может занять некоторое время.", parse_mode="HTML")

    try:
        # Запускаем блокирующую функцию скачивания в отдельном потоке
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _download_internal(ydl_opts, url))
        
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            # Лимит Telegram Bot API для отправки файлов — 50 МБ
            limit_mb = 50
            if file_size > limit_mb * 1024 * 1024:
                await status_msg.edit_text(
                    f"⚠️ <b>Файл слишком большой!</b>\n"
                    f"Размер: {file_size / (1024*1024):.2f} MB\n"
                    f"Telegram боты могут отправлять файлы только до {limit_mb} МБ.\n"
                    f"Попробуйте видео покороче.",
                    parse_mode="HTML"
                )
                os.remove(output_filename)
                return

            await status_msg.edit_text("📤 <b>Загружаю видео в Telegram...</b>", parse_mode="HTML")
            
            # Отправка видео
            video_file = FSInputFile(output_filename)
            await message.answer_video(video_file, caption="✅ Вот ваше видео!")
            
            # Удаляем сообщение о статусе и файл
            await status_msg.delete()
            os.remove(output_filename)
        else:
            await status_msg.edit_text("❌ Ошибка: Не удалось скачать файл (403 Forbidden или другая ошибка).")

    except Exception as e:
        logger_err = logging.getLogger(__name__)
        logger_err.error(f"Error downloading: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при скачивании:\n{str(e)}\n\nПопробуйте другую ссылку.")
        if os.path.exists(output_filename):
             os.remove(output_filename)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет!\n"
        "Я бот для скачивания видео с YouTube.\n\n"
        "Просто отправь мне <b>ссылку</b> на видео, и я постараюсь его скачать и отправить тебе файлом.\n"
        "<i>Учти, что я могу отправлять файлы только до 50 МБ.</i>",
        parse_mode="HTML"
    )

@dp.message()
async def handle_text(message: types.Message):
    text = message.text.strip()
    # Простая проверка на ссылку
    if "youtube.com" in text or "youtu.be" in text:
        await download_video_task(text, message)
    else:
        await message.answer("🤔 Это не похоже на ссылку YouTube. Попробуйте отправить ссылку (например, https://youtu.be/...).")

async def main():
    print("Бот запущен...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(main())
