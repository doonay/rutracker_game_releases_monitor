import os
import sys
import asyncio
from dotenv import load_dotenv
from aiogram.types import URLInputFile, FSInputFile
from sqlite3_db_crud_methods import get_unsent_torrents_dict, mark_as_sent
from rutracker_parser import rutracker_parser

load_dotenv()
GROUP_ID = os.getenv('GROUP_ID')
if not GROUP_ID:
    raise ValueError("GROUP_ID не найден в .env!")
THREADS = {
    "general": 1, # "general": int(os.getenv("THREAD_GENERAL", 1)),
    "hots": 780 # "hots": int(os.getenv("THREAD_HOTS", 780))
}

async def send_scheduled_message(bot):
    await rutracker_parser()
    try:
        unsent_games = await get_unsent_torrents_dict()
        if not unsent_games:
            return
        for game in unsent_games:
            torrent_path = game['output_torrent_file']
            img_message = await bot.send_photo(
                chat_id=GROUP_ID,                
                message_thread_id=THREADS["hots"],
                photo=URLInputFile(game["img"]),
                caption=f'<a href="{game["detail_page"]}">{game["title"]}</a>\n\n'
                        f'🗓 {game["year"]} | 🎮 {", ".join(game["genre"])} | 📦 {game["mb_size"]/1024:.2f} GB',
            )
            await asyncio.sleep(1)
            await bot.send_document(
                chat_id=GROUP_ID,
                message_thread_id=THREADS["hots"],  # ⚡
                document=FSInputFile(game["output_torrent_file"]),
                caption="📥 Торрент-файл для загрузки",
            )
            await mark_as_sent(game['topic_id'])
            await asyncio.sleep(5)
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")

async def start_scheduler(bot):
    while True:
        await send_scheduled_message(bot)
        await asyncio.sleep(300)