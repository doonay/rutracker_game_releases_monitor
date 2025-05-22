import os
import aiofiles
import asyncio
import aiohttp
import sys
from dotenv import load_dotenv
import bs4
import time
import re
from datetime import datetime
import json
from urllib.parse import unquote
import logging

from sqlite3_db_crud_methods import create_table, insert_data, is_topic_id_in_db

load_dotenv()
login_username = os.getenv("LOGIN_USERNAME")
login_password = os.getenv("LOGIN_PASSWORD")
login = os.getenv("LOGIN")
proxy = os.getenv("PROXY")

def get_clean_filename(filename):
	clean_name = filename \
		.replace("[Антология]", "") \
		.replace('\\', '-') \
		.replace('/', '-') \
		.replace(':', '-') \
		.replace('*', '') \
		.replace('?', '') \
		.replace('"', '') \
		.replace('<', '') \
		.replace('>', '') \
		.replace('|', '-') \
		.replace("'", '') \
		.strip(' .')
	if not clean_name:
		clean_name = "unnamed_file"
	return clean_name


async def download_torrent(session, torrent_file_url, data):
    os.makedirs('torrent_files', exist_ok=True)

    async with session.post(torrent_file_url, data=data, proxy=proxy) as r:
        r.raise_for_status()
        
        content_disposition = r.headers.get('Content-Disposition', '')
        if "filename*=UTF-8''" in content_disposition:
            filename = unquote(content_disposition.split("filename*=UTF-8''")[-1])
        else:
            filename = torrent_file_url.split('/')[-1] or 'unnamed.torrent'

        clean_filename = get_clean_filename(filename)
        save_path = os.path.join('torrent_files', clean_filename)
        
        async with aiofiles.open(save_path, 'wb') as f:
            while True:
                chunk = await r.content.read(1024)
                if not chunk:
                    break
                await f.write(chunk)
        
        print(f"Файл сохранён как: {save_path}")
        return save_path

async def get_pagination(session, headers):
	url = "https://rutracker.org/forum/tracker.php?f=635"
	max_retries = 5
	retry_delay = 4
	
	for attempt in range(max_retries):
		try:
			async with session.get(url, proxy=proxy, headers=headers) as r:
				text = await r.text()
				soup = bs4.BeautifulSoup(text, 'lxml')
				page_link = soup.find("a", {"class": "pg"})
				
				if page_link:
					pages = int(page_link.text.strip())
					print("pages:", pages)
					return pages
				
				# Если не нашли пагинацию, возвращаем 1
				return 1
				
		except AttributeError as e:
			print(f'Attempt {attempt + 1} failed. Error: {str(e)}. Retrying in {retry_delay} sec...')
			await asyncio.sleep(retry_delay)
	
	# Если все попытки исчерпаны
	print(f'Failed after {max_retries} attempts. Returning default 1 page.')
	return 1

def title_parser(title_string):
	parts = title_string.split("] (", 1)
	if len(parts) < 2:
		return {'title': title_string.strip(), 'year': '', 'genre': []}
	first_part, second_part = parts
	title = first_part.replace("[DL]", "").strip()
	title = title.split(" [")[0].strip()
	title = title.replace("/", "-")
	year_genres_part = second_part.split(") ", 1)[0]
	year_genres = [x.strip() for x in year_genres_part.split(",")]
	year = ''
	genres = []
	possible_years = []
	for item in year_genres:
		if re.fullmatch(r'\d{4}', item.strip()):
			possible_years.append(item.strip())
		elif re.fullmatch(r'\d{4}\s*—\s*\d{4}', item.strip()):
			start, end = re.findall(r'\d{4}', item)
			possible_years.extend([start, end])
		elif item and not any(char.isdigit() for char in item):
			genres.append(item)
	if possible_years:
		year = max(possible_years)
	return {
		'title': title,
		'year': year,
		'genre': genres
	}

def parse_size(size_str):
	"""
	Преобразует строку с размером (например, "12.22 GB" или "296.8 MB") в мегабайты (float).
	"""
	size_str = size_str.replace('↓', '').strip().upper()
	for unit in ["GB", "MB", "KB"]:
		if size_str.endswith(unit):
			num_part = size_str[:-len(unit)].strip()
			try:
				size = float(num_part)
			except ValueError:
				raise ValueError(f"Неверный числовой формат: {num_part}")
			# Конвертируем в мегабайты
			if unit == "GB":
				return size * 1024
			elif unit == "MB":
				return size
			elif unit == "KB":
				return size / 1024
	raise ValueError(f"Неверный формат размера или неизвестная единица: {size_str}")

async def detail_page_parser(session, headers, detail_page_url, title, year):
	"""Асинхронный парсер страницы с деталями"""
	while True:
		try:
			async with session.get(detail_page_url, proxy=proxy) as r:
				text = await r.text()
				soup = bs4.BeautifulSoup(text, 'lxml')
				
				form_token = soup.find("script")
				if form_token is None:
					continue
					
				form_token = form_token.text
				x = form_token.find("form_token: '") + 13
				y = form_token.find("opt_js")
				form_token = form_token[x:y].replace("',", "").strip()
				break
				
		except Exception as e:
			print(f"Ошибка при запросе: {e}")
			continue

	torrent_file_url = detail_page_url.replace("viewtopic.php", "dl.php")
	data = f'form_token={form_token}'
	
	try:
		torrent_filename = await download_torrent(session, torrent_file_url, data)
		
		post_body = soup.find("div", {"class": "post_body"})
		img = (post_body.find("var", {"class": "img-right"}) or 
			   post_body.find("var", {"class": "img-left"})).get("title")
		
		if img is None:
			raise ValueError(f"Постер не найден на странице: {detail_page_url}")

		return {
			"torrent_filename": torrent_filename,
			"img": img
		}
		
	except Exception as e:
		print(f"Ошибка в detail_page_parser: {e}")
		raise

async def base_list_runner(session, headers, tr):
	topic_id = int(tr.get("data-topic_id"))
	if await is_topic_id_in_db(topic_id):
		print(topic_id)
		return None

	try:
		tds = tr.find_all("td")
	except Exception as e:
		print(f"Ошибка обработки: {e}")
		sys.exit(1)

	status = tds[1].span.text
	detail_page = f'https://rutracker.org/forum/{tds[3].div.a.get("href")}'
	title_data = title_parser(tds[3].div.a.text) #title_data: {'title': 'Revenge of the Savage Planet', 'year': '2025', 'genre': ['Action']}
	title = title_data['title']
	year = title_data['year']
	genre = title_data['genre']
	author = tds[4].div.a.text
	dirty_size = tds[5].a.text
	mb_size = parse_size(dirty_size)
	seeds = tds[6].b.text
	leech = tds[7].text
	downloads = tds[8].text
	topic_date = tds[9].p.text
	detail_page_data = await detail_page_parser(session, headers, f'https://rutracker.org/forum/{tds[3].div.a.get("href")}', title, year)
	torrent_filename = detail_page_data['torrent_filename']
	img = detail_page_data['img']
		
	data = {
		"topic_id": topic_id,
		"status": status,
		"detail_page": detail_page,
		"img": img,
		"title": title,
		"year": year,
		"genre": json.dumps(genre),
		"author": author,
		"mb_size": mb_size,
		"seeds": seeds,
		"leech": leech,
		"downloads": downloads,
		"topic_date": topic_date,
		"output_torrent_file": torrent_filename,
	}

	if await insert_data(data):
		print(f"Добавлено: {data['title']}")

async def rutracker_parser():
	print('rutracker_parser запущен!')
	await create_table()
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
	}
	async with aiohttp.ClientSession(headers=headers) as session:
		# Аутентификация
		auth_data = {
			'login_username': login_username,
			'login_password': login_password,
			'login': login
		}
		
		async with session.post('https://rutracker.org/forum/login.php', data=auth_data, proxy=proxy) as r:
			await r.read()

		# Получаем количество страниц
		total_pages = await get_pagination(session, headers)
		stopfactor = total_pages * 50

		for start in range(0, stopfactor, 50):
			url = f'https://rutracker.org/forum/tracker.php?f=635&start={start}'
			while True:
				try:
					async with session.get(url, proxy=proxy) as r:
						text = await r.text()
						soup = bs4.BeautifulSoup(text, 'lxml')
						search_results = soup.find('div', {'id': 'search-results'})
						tbody = search_results.find('tbody')
						trs = tbody.find_all('tr')
						for tr in trs:
							result = await base_list_runner(session, headers, tr)
							if result is None:
								continue
						break
				except (AttributeError, ValueError) as e:
					retry_count += 1
					if retry_count >= max_retries:
						logging.error(f"Не удалось обработать страницу {url} после {max_retries} попыток")
						break
					await asyncio.sleep(3)
					continue

if __name__ == '__main__':
	asyncio.run(rutracker_parser())