import random
import time
import logging
import aiohttp
import asyncio
from colorama import Fore, Style
from datetime import datetime, timedelta
from tqdm import tqdm

# Konfigurasi logging ke file
logging.basicConfig(
    filename="activity.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_message(level, message):
    """Log pesan ke file dan konsol dengan format warna-warni"""
    color_map = {"info": Fore.GREEN, "warning": Fore.YELLOW, "error": Fore.RED}
    color = color_map.get(level, Style.RESET_ALL)

    logging.log(getattr(logging, level.upper()), message)
    print(f"{color}{message}{Style.RESET_ALL}")

async def cek_token(session, nama_token, token):
    """Mengecek apakah token valid dengan mencoba request ke API Discord."""
    headers = {"Authorization": token}
    async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as response:
        if response.status == 200:
            log_message("info", f"{nama_token}: ✅ Token valid")
            return True
        else:
            log_message("error", f"{nama_token}: ❌ Token tidak valid (Status: {response.status})")
            return False

async def validasi_token(tokens):
    """Memeriksa semua token sebelum melanjutkan program."""
    async with aiohttp.ClientSession() as session:
        hasil_validasi = await asyncio.gather(
            *(cek_token(session, nama_token, token) for nama_token, token in tokens)
        )
    return all(hasil_validasi)  # Jika ada token yang salah, return False

async def main():
    try:
        # Baca file pesan
        with open("pesan.txt", "r") as f:
            pesan_list = [line.strip() for line in f.readlines()]
        if not pesan_list:
            raise ValueError("⚠️ File pesan.txt kosong!")

        # Baca file token
        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines() if ":" in line]
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong!")

        log_message("info", "🔍 Memeriksa validitas token...")

        # Validasi token sebelum lanjut ke input berikutnya
        if not await validasi_token(tokens):
            log_message("error", "🚨 Beberapa token tidak valid. Harap perbaiki token.txt dan coba lagi.")
            return

        # Input pengguna setelah token valid
        channel_id = input("🔹 Masukkan ID channel: ").strip()
        if not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka!")

        waktu_hapus = float(input("⌛ Set Waktu Hapus Pesan (min 0.01 detik): "))
        waktu_kirim = float(input("📨 Set Waktu Kirim Pesan (min 0.01 detik): "))
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

        # Minta waktu mulai dan waktu berhenti untuk setiap token
        waktu_mulai_dict = {}
        waktu_stop_dict = {}
        counter = {nama_token: 0 for nama_token, _ in tokens}

        for nama_token, _ in tokens:
            waktu_mulai_menit = int(input(f"⏳ Masukkan waktu mulai untuk {nama_token} (menit dari sekarang): "))
            waktu_berhenti_menit = int(input(f"⏰ Masukkan waktu berhenti untuk {nama_token} (menit setelah mulai): "))

            waktu_mulai = datetime.now() + timedelta(minutes=waktu_mulai_menit)
            waktu_stop = waktu_mulai + timedelta(minutes=waktu_berhenti_menit)

            waktu_mulai_dict[nama_token] = waktu_mulai
            waktu_stop_dict[nama_token] = waktu_stop

    except Exception as e:
        log_message("error", f"🚨 Input error: {e}")
        return

    log_message("info", "🚀 Memulai pengiriman pesan...")

    # Progress bar
    total_pesan = sum(
        (waktu_stop_dict[nama_token] - waktu_mulai_dict[nama_token]).total_seconds() // (waktu_kirim + waktu_hapus)
        for nama_token, _ in tokens
    )
    with tqdm(total=int(total_pesan), desc="📩 Progres Pengiriman") as progress_bar:
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(kirim_pesan(session, channel_id, nama_token, token, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai_dict[nama_token], waktu_stop_dict[nama_token], progress_bar, counter))
                for nama_token, token in tokens
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    # Menampilkan ringkasan akhir
    log_message("info", "🎉 Semua token telah selesai!")
    log_message("info", "\n📊 **Ringkasan Pengiriman:**")
    for nama_token, jumlah in counter.items():
        log_message("info", f"🔹 {nama_token}: {jumlah} pesan terkirim")

if __name__ == "__main__":
    asyncio.run(main())
