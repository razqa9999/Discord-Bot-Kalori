import discord
from discord.ext import commands
import sqlite3
from datetime import datetime

# Setup Intents (Wajib aktifkan Message Content Intent di Discord Developer Portal)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
DB_NAME = "discord_kalori_v2.db"

def init_db():
    """Inisialisasi database dan semua tabel yang diperlukan."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabel Profil User
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            discord_id INTEGER PRIMARY KEY,
            target_calories INTEGER
        )
    ''')
    
    # 2. Tabel Master Menu Referensi (Makanan/Minuman)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_referensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT UNIQUE,
            calories INTEGER
        )
    ''')
    
    # 3. Tabel Log Harian User (id, discord_id, food_name, calories, date)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER,
            food_name TEXT,
            calories INTEGER,
            date TEXT
        )
    ''')
    
    # Isi beberapa contoh makanan/minuman awal jika tabel masih kosong
    contoh_menu = [
        ("Nasi Goreng", 500),
        ("Ayam Goreng", 260),
        ("Mie Instan", 400),
        ("Es Teh Manis", 120),
        ("Kopi Susu", 180),
        ("Jus Alpukat", 250)
    ]
    cursor.executemany("INSERT OR IGNORE INTO menu_referensi (food_name, calories) VALUES (?, ?)", contoh_menu)
    
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    init_db()
    print(f'🤖 Bot {bot.user.name} siap digunakan!')

# ==================== 1. COMMAND TAMBAH MENU BARU ====================
@bot.command()
async def info(ctx):
    """Menampilkan informasi bot dan cara penggunaannya."""
    pesan = (
        "🤖 **Bot Penghitung Kalori**\n"
        "==================================\n"
        "✅ **Cara Penggunaan:**\n"
        "- `!tambahmenu <kalori> <nama_item>`: Menambahkan makanan/minuman baru\n"
        "- `!menu`: Melihat daftar makanan & minuman\n"
        "- `!makan <nama>`: Mencatat konsumsi makanan\n"
        "- `!minum <nama>`: Mencatat konsumsi minuman\n"
        "- `!target <kalori>`: Menetapkan target kalori harian\n"
        "- `!log`: Melihat log konsumsi harian\n"
        "=================================="
    )
    await ctx.send(pesan)
    
@bot.command()
async def tambahmenu(ctx, kalori: int, *, nama_item: str):
    """Menambahkan makanan/minuman baru ke database referensi. Contoh: !tambahmenu 300 Sate Ayam"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO menu_referensi (food_name, calories)
            VALUES (?, ?)
        ''', (nama_item, kalori))
        conn.commit()
        await ctx.send(f"✨ Berhasil menambahkan ke menu master: **{nama_item}** (**{kalori} kkal**). Sekarang menu ini sudah bisa dipesan lewat `!makan` atau `!minum`!")
    except sqlite3.integrityError:
        await ctx.send(f"⚠️ **{nama_item}** sudah ada di database menu!")
    finally:
        conn.close()

# ==================== 2. COMMAND LIHAT DAFTAR MENU ====================
@bot.command()
async def menu(ctx):
    """Menampilkan semua daftar makanan & minuman yang terdaftar."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT food_name, calories FROM menu_referensi")
    daftar = cursor.fetchall()
    conn.close()
    
    if not daftar:
        await ctx.send("📋 Database menu kosong. Yuk tambah pakai `!tambahmenu`!")
        return
        
    pesan = "📖 **DAFTAR REFERENSI KALORI**\n==================================\n"
    for idx, (nama, kal) in enumerate(daftar, 1):
        pesan += f"{idx}. {nama} — **{kal} kkal**\n"
    pesan += "==================================\n💡 *Ketik `!makan <nama>` atau `!minum <nama>` untuk mencatat!*"
    await ctx.send(pesan)

# ==================== 3. COMMAND LOG MAKANAN / MINUMAN (OTOMATIS) ====================
def catat_konsumsi_otomatis(discord_id, nama_item):
    """Fungsi pembantu untuk mencari kalori di menu master dan menyimpannya ke log harian."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Cari yang namanya mirip
    cursor.execute("SELECT food_name, calories FROM menu_referensi WHERE food_name LIKE ?", (f"%{nama_item}%",))
    hasil = cursor.fetchone()
    
    if hasil:
        nama_resmi, kalori = hasil
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # Simpan ke food_logs sesuai struktur: id, discord_id, food_name, calories, date
        cursor.execute('''
            INSERT INTO food_logs (discord_id, food_name, calories, date)
            VALUES (?, ?, ?, ?)
        ''', (discord_id, nama_resmi, kalori, today_date))
        conn.commit()
        conn.close()
        return nama_resmi, kalori
    
    conn.close()
    return None

@bot.command()
async def makan(ctx, *, nama_makanan: str):
    """Mencatat makanan otomatis dari database menu. Contoh: !makan Nasi Goreng"""
    hasil = catat_konsumsi_otomatis(ctx.author.id, nama_makanan)
    if hasil:
        await ctx.send(f"🍔 {ctx.author.mention} mencatat makanan: **{hasil[0]}** (**{hasil[1]} kkal**).")
    else:
        await ctx.send(f"❌ **'{nama_makanan}'** belum terdaftar. Daftarkan dulu lewat `!tambahmenu <kalori> {nama_makanan}`.")

@bot.command()
async def minum(ctx, *, nama_minuman: str):
    """Mencatat minuman otomatis dari database menu. Contoh: !minum Kopi Susu"""
    hasil = catat_konsumsi_otomatis(ctx.author.id, nama_minuman)
    if hasil:
        await ctx.send(f"🥤 {ctx.author.mention} mencatat minuman: **{hasil[0]}** (**{hasil[1]} kkal**).")
    else:
        await ctx.send(f"❌ **'{nama_minuman}'** belum terdaftar. Daftarkan dulu lewat `!tambahmenu <kalori> {nama_minuman}`.")

# ==================== 4. COMMAND PROFIL & RINGKASAN ====================
@bot.command()
async def setprofil(ctx, berat: float, tinggi: float, usia: int, gender: str):
    """Set profil awal. Contoh: !setprofil 65 168 22 P"""
    gender = gender.upper()
    if gender not in ['L', 'P']:
        await ctx.send("❌ Gunakan L untuk Laki-laki atau P untuk Perempuan.")
        return
        
    bmr = (10 * berat) + (6.25 * tinggi) - (5 * usia) + (5 if gender == 'L' else -161)
    target = round(bmr * 1.55)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (discord_id, target_calories) VALUES (?, ?)", (ctx.author.id, target))
    conn.commit()
    conn.close()
    await ctx.send(f"✅ Profil {ctx.author.mention} disimpan! Target harian Anda: **{target} kkal**.")

@bot.command()
async def ringkasan(ctx):
    """Melihat log konsumsi hari ini."""
    today_date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT target_calories FROM users WHERE discord_id = ?", (ctx.author.id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        await ctx.send(f"⚠️ {ctx.author.mention}, isi profil dulu dengan `!setprofil <berat> <tinggi> <usia> <L/P>`")
        conn.close()
        return
        
    target = user_data[0]
    cursor.execute("SELECT id, food_name, calories FROM food_logs WHERE discord_id = ? AND date = ?", (ctx.author.id, today_date))
    logs = cursor.fetchall()
    conn.close()
    
    pesan = f"📊 **JURNAL KALORI HARI INI** — {ctx.author.mention}\n==================================\n"
    total = 0
    if not logs:
        pesan += "_Belum ada konsumsi hari ini._\n"
    else:
        for log_id, name, cal in logs:
            pesan += f"🔹 [ID: {log_id}] {name} — **{cal} kkal**\n"
            total += cal
            
    pesan += f"==================================\n🎯 Target: **{target} kkal**\n🍽️ Total: **{total} kkal**\n"
    pesan += f"🟢 Sisa: **{target - total} kkal**\n" if target >= total else f"🔴 Kelebihan: **{total - target} kkal (Surplus!)**\n"
    await ctx.send(pesan)

# Masukkan Token Anda di sini
bot.run('Your Bot Discord Token')
