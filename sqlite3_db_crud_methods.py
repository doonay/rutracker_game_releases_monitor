import aiosqlite
import json


async def create_table():
    """
    Создает таблицу в базе данных, если её ещё не существует.
    """
    async with aiosqlite.connect('hot_new_releases.db') as conn:
        cursor = await conn.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS torrents (
            topic_id INTEGER PRIMARY KEY,
            status TEXT,
            detail_page TEXT,
            img TEXT,
            title TEXT,
            year INTEGER,
            genre TEXT,  -- Храним JSON как строку
            author TEXT,
            mb_size REAL,
            seeds INTEGER,
            leech INTEGER,
            downloads INTEGER,
            topic_date TEXT,
            output_torrent_file TEXT,
            sent INTEGER DEFAULT 0
        )
        """
        await cursor.execute(create_table_query)
        await conn.commit()


async def is_topic_id_in_db(topic_id: int) -> bool:
    """
    Проверяет, существует ли запись с указанным topic_id в базе данных.
    Args: topic_id: Идентификатор темы для проверки
    Returns: bool: True если запись существует, False если нет
    """
    async with aiosqlite.connect('hot_new_releases.db') as conn:
        cursor = await conn.cursor()
        query = "SELECT 1 FROM torrents WHERE topic_id = ? LIMIT 1"
        await cursor.execute(query, (topic_id,))
        result = await cursor.fetchone()
        return result is not None


async def get_unsent_torrents_dict():
    """
    Асинхронно получает все торренты с sent = 0 из базы данных
    Returns: Список словарей с данными торрентов
    """
    async with aiosqlite.connect('hot_new_releases.db') as conn:
        conn.row_factory = aiosqlite.Row # Устанавливаем row_factory для возврата словарей
        async with conn.cursor() as cursor:
            await cursor.execute("""SELECT * FROM torrents WHERE sent = 0""")
            rows = await cursor.fetchall()
            torrents = []
            for row in rows:
                torrent = dict(row)
                if torrent['genre']:
                    torrent['genre'] = json.loads(torrent['genre'])
                torrents.append(torrent)
            return torrents


async def mark_as_sent(topic_id):
    """
    Обновляет поле sent на 1 для указанного topic_id
    Args: ID торрента для пометки как отправленного
    """
    try:
        # Подключаемся к базе данных асинхронно
        async with aiosqlite.connect('hot_new_releases.db') as conn:
            async with conn.cursor() as cursor:
                update_query = """UPDATE torrents SET sent = 1 WHERE topic_id = ?"""
                await cursor.execute(update_query, (topic_id,))
                await conn.commit()

                #пусть пока так побудет, пока логирование не сделал, но потом эту проверку убрать
                if cursor.rowcount > 0:
                    print(f"Запись с topic_id={topic_id} успешно помечена как отправленная")
                else:
                    print(f"Запись с topic_id={topic_id} не найдена")
                
    except aiosqlite.Error as e:
        print(f"Ошибка при обновлении записи: {e}")


async def insert_data(data):
    """
    Добавляет данные в базу
    Args: data - это словарь данных одной позиции 
    """
    async with aiosqlite.connect('hot_new_releases.db') as conn:
        cursor = await conn.cursor()
        
        insert_query = """
        INSERT OR IGNORE INTO torrents (
            topic_id, status, detail_page, img, 
            title, year, genre, author, mb_size, 
            seeds, leech, downloads, topic_date, output_torrent_file
        ) VALUES (
            :topic_id, :status, :detail_page, :img, 
            :title, :year, :genre, :author, :mb_size, 
            :seeds, :leech, :downloads, :topic_date, :output_torrent_file
        )
        """
        
        await cursor.execute(insert_query, data)
        await conn.commit()
