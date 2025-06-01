import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime, timedelta
import random

# Koneksi ke MongoDB
client = MongoClient('mongodb+srv://capstone:Cap5t@capstone.khterpv.mongodb.net/')
db = client['db']
collection = db['pendaki']

detik_count = 0

def random_date():
    """Generate random datetime dalam 3 tahun terakhir (2023-2025)"""
    start = datetime(2023, 1, 1)
    end = datetime(2025, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)  # jumlah detik dalam sehari
    return start + timedelta(days=random_days, seconds=random_seconds)

def insert_article(title, date, url, source, keyword):
    if not collection.find_one({"url": url}):  # Cek agar tidak duplikat
        collection.insert_one({
            "title": title,
            "date": date,
            "url": url,
            "source": source,
            "keyword": keyword
        })
        print(f"[DEBUG] Disimpan: {title[:10]}... | Tanggal: {date} | URL: {url}")
        return True
    else:
        print(f"[DEBUG] Duplikat, tidak disimpan: {url}")
    return False

def scrape_detik_search():
    global detik_count
    headers = {'User-Agent': 'Mozilla/5.0'}
    keywords = ['pendaki', 'hipotermia', 'evakuasi gunung', 'gunung', 'cuaca ekstream', 'pendakiaan', 'pendaki gunung', 'petualangan', 'alam']

    for keyword in keywords:
        for page in range(1, 50):  # 49 halaman
            url = f"https://www.detik.com/search/searchall?query={keyword}&page={page}"
            print(f"Mengakses: {url}")
            try:
                r = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
            except Exception as e:
                print(f"Error request halaman: {e}")
                continue

            articles = soup.find_all('article')
            if not articles:
                print("Tidak ada artikel ditemukan di halaman ini.")
                break

            for item in articles:
                a_tag = item.find('a', href=True)
                title = a_tag.get('title', '').strip() if a_tag else 'No Title'
                link = a_tag['href'] if a_tag else ''

                time_tag = item.find('span', class_='date')
                if time_tag:
                    try:
                        date_str = time_tag.get_text(strip=True)
                        tanggal = date_str.split(',')[-1].replace('WIB', '').strip()
                        date = datetime.strptime(tanggal, "%d %B %Y %H:%M")
                    except Exception as e:
                        print(f"Error parsing date: {e}, menggunakan tanggal random")
                        date = random_date()
                        print(f"[DEBUG] Tanggal random dipakai: {date}")
                else:
                    date = random_date()
                    print(f"[DEBUG] Tidak ada tanggal, pakai tanggal random: {date}")

                # Filter artikel maksimal 5 tahun terakhir, dan URL valid
                if date >= datetime.now() - timedelta(days=1825) and link.startswith("https://"):
                    if insert_article(title, date, link, 'detik', keyword):
                        detik_count += 1

if __name__ == "__main__":
    print("Scraping dimulai...")
    scrape_detik_search()
    print("Scraping selesai.")
    print(f"Artikel Detik berhasil ditambahkan: {detik_count}")
