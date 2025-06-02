import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime
from wordcloud import WordCloud, STOPWORDS
import requests
from bs4 import BeautifulSoup
import subprocess


# Koneksi MongoDB
client = MongoClient('mongodb+srv://capstone:Cap5t@capstone.khterpv.mongodb.net/')
db = client['db']
collection = db['pendaki']

# Ambil data dari MongoDB
data = list(collection.find({"source": "detik"}))
df = pd.DataFrame(data)


# Tangani kolom 'date' yang mungkin tidak ada
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
else:
    st.warning("Kolom 'date' tidak ditemukan di data MongoDB!")
    df['date'] = pd.NaT  # Tambahkan kolom 'date' kosong

# Tambahkan kolom tahun & bulan
df['tahun'] = df['date'].dt.year
df['bulan'] = df['date'].dt.month

# Judul aplikasi
st.title("Visualisasi Artikel Detik.com tentang MountainPrep")

# Tombol refresh scraping
if st.button("Scraping Terbaru (Update Data)"):
    with st.spinner("Menjalankan scraping..."):
        subprocess.run(["python", "scraper.py"])
    st.success("Scraping selesai! Silakan refresh halaman ini.")


# Statistik Umum
st.subheader("Statistik Umum")
st.metric("Jumlah Artikel", len(df))

# Periode data
if df['date'].notna().any():
    periode = f"{df['date'].min().date()} - {df['date'].max().date()}"
else:
    periode = "Data tidak lengkap"
st.metric("Periode Data", periode)

# Filter tahun dan bulan
tahun_pilihan = st.selectbox("Pilih Tahun:", sorted(df['tahun'].dropna().unique(), reverse=True))
bulan_pilihan = st.selectbox("Pilih Bulan (opsional):", ["Semua"] + [str(b) for b in sorted(df['bulan'].dropna().unique())])

# Filter data
if bulan_pilihan != "Semua":
    df_filtered = df[(df['tahun'] == tahun_pilihan) & (df['bulan'] == int(bulan_pilihan))]
else:
    df_filtered = df[df['tahun'] == tahun_pilihan]

# Jumlah Artikel per Bulan
st.subheader("Jumlah Artikel per Bulan")
if df['date'].notna().any():
    df['bulan_str'] = df['date'].dt.to_period('M').astype(str)
    df_bulan = df.groupby('bulan_str').size()
    st.bar_chart(df_bulan)
else:
    st.warning("Data tanggal tidak tersedia untuk chart ini.")

# Line Chart
st.subheader("Line Chart: Jumlah Artikel per Hari")
if not df_filtered.empty:
    df_line = df_filtered.groupby(df_filtered['date'].dt.date).size()
    st.line_chart(df_line)
else:
    st.warning("Data untuk line chart tidak tersedia di bulan & tahun ini.")

# Wordcloud dari Judul
st.subheader("Wordcloud dari Judul Artikel")

judul_kumpulan = []
for _, row in df.iterrows():
    if row.get("title"):
        judul_kumpulan.append(row['title'])
    else:
        try:
            res = requests.get(row['url'], timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            html_title = soup.find('title')
            if html_title:
                fetched = html_title.get_text(strip=True)
                judul_kumpulan.append(fetched)
        except:
            continue

if judul_kumpulan:
    text_raw = " ".join(judul_kumpulan)
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update([
        "yang", "dan", "untuk", "dalam", "dari", "pada", "oleh",
        "itu", "ini", "ada", "ke", "di", "akan", "dengan", "karena",
        "berita", "detik", "com", "video", "judul", "artikel", "warga"
    ])
    text_clean = re.findall(r'\b\w+\b', text_raw.lower())
    filtered_words = [word for word in text_clean if word not in custom_stopwords]
    final_text = " ".join(filtered_words)

    if final_text.strip():
        wordcloud = WordCloud(width=800, height=300, background_color='white').generate(final_text)
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("Tidak ada kata yang cukup untuk menampilkan Wordcloud.")
else:
    st.warning("Tidak ada judul artikel yang bisa digunakan.")

# Daftar Artikel
st.subheader("Daftar Artikel (klik judul untuk membuka)")

for _, row in df.sort_values("date", ascending=False).iterrows():
    title = row.get("title", "")
    if not title:
        try:
            res = requests.get(row['url'], timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else "Judul tidak ditemukan"
        except:
            title = "Judul gagal diambil"

    tanggal = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "Tanggal tidak diketahui"

    st.markdown(f"- [{title}]({row['url']}) — {tanggal}")
