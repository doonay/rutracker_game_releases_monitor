# rutracker_game_releases_monitor
A TG bot that scrapes rutracker's 'Hot New Releases' every 6h and shares them in a Telegram group.
(Бот просто зеркалит раздел "Горящие новинки" из рутрекера)
Сам парсер старый, надёжный, хоть и данные собирает из HTML, но где то с 19 года он точно не ломался ни разу.

Install:
1. Создать виртуальное окружение и установить в него requirements.txt

2. Создать файл ".env", в него поместить:
BOT_TOKEN="токен бота"
GROUP_ID="айдишник группы, в которой этот бот админ"
LOGIN_USERNAME="логин на рутрекер"
LOGIN_PASSWORD="пароль на рутрекер"
LOGIN="секретный параметр для входа на рутрекер"
PROXY="http://<ваша прокся> (префикс http:// важен, ибо это не для requests, а для aiohttp)"

Важное замечание:
Прокси, понятное дело, нужны только в том случае, если мы запускаем бота из РФ. Если сервер под боевой вариант находится за границей - все упоминания о прокси можно из кода удалить, там рутрекер никем не блокируется.

======================= Далее я пишу для себя, что бы не забыть:
Допилить:
- добавить удаление торрент-файлов после отправки их ботом! 100 файлов уже весят 8Мб!
- сделать нормальное логирование с loguru
- добавить эхо-функцию "ты живой?/ты работаешь?"
- создать службу и добавить в автозагрузку (сейчас бот просто руками запущен)
- переделать модуль rutracker_parser в класс
- модуль sqlite3_db_crud_methods можно тоже сделать классом

Не обязательно:
- переделать парсинг так, что бы "brackets-pair" собирать отдельно 
<div class="wbr t-title">
	<span class="ttp-label ttp-hot">горячая</span>
	<a data-topic_id="6695479" class="med tLink tt-text ts-text hl-tags bold tags-initialized" href="viewtopic.php?t=6695479">RoadCraft
		<span class="brackets-pair">[P]</span>
		<span class="brackets-pair">[RUS + ENG + 12 / ENG]</span>
		<span class="brackets-pair">(2025, Simulation, Adventure)</span>
		<span class="brackets-pair">(0.<wbr>1.<wbr>D1.<wbr>1.<wbr>429865/430509 + 3 DLC)</span>
		<span class="brackets-pair">[Portable]</span>
	</a>
</div>
- Так же можно забирать шильду "горячая", когда она есть
