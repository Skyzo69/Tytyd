import random
import time
import logging
import aiohttp
import asyncio
from colorama import Fore, Style
from datetime import datetime, timedelta
from tqdm import tqdm
from itertools import cycle

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
    return all(hasil_validasi)

async def kirim_pesan(session, channel_id, nama_token, token, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, progress_bar, counter):
    """Mengirim dan menghapus pesan secara berurutan dengan retry jika gagal."""
    headers = {"Authorization": token, "Content-Type": "application/json"}
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    pesan_iterator = cycle(pesan_list)
    pesan_gagal_hapus = []

    while datetime.now() < waktu_stop:
        if datetime.now() < waktu_mulai:
            await asyncio.sleep(1)
            continue

        pesan = next(pesan_iterator)
        data = {"content": pesan}

        # Retry pengiriman pesan jika gagal
        for attempt in range(3):  # Coba maksimal 3 kali
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    message_id = (await response.json())["id"]
                    log_message("info", f"{nama_token}: 📩 Pesan terkirim - {pesan}")
                    counter[nama_token] += 1
                    progress_bar.update(1)
                    break
                else:
                    log_message("error", f"{nama_token}: ❌ Gagal mengirim pesan (Status: {response.status}) - Percobaan {attempt + 1}")
                    await asyncio.sleep(2)  # Tunggu sebelum mencoba lagi
            else:
                continue  # Jika semua percobaan gagal, lanjut ke pesan berikutnya

        await asyncio.sleep(waktu_hapus)

        # Coba hapus pesan yang baru dikirim
        delete_url = f"{url}/{message_id}"
        for attempt in range(3):  # Coba maksimal 3 kali
            async with session.delete(delete_url, headers=headers) as del_response:
                if del_response.status == 204:
                    log_message("info", f"{nama_token}: 🗑️ Pesan dihapus")
                    break
                else:
                    log_message("error", f"{nama_token}: ❌ Gagal menghapus pesan - Percobaan {attempt + 1}")
                    await asyncio.sleep(2)  # Tunggu sebelum mencoba lagi
            else:
                # Jika gagal dihapus setelah 3 kali coba, simpan ID-nya
                pesan_gagal_hapus.append(message_id)

        await asyncio.sleep(waktu_kirim)

    # Coba hapus pesan yang gagal dihapus sebelumnya
    for message_id in pesan_gagal_hapus:
        delete_url = f"{url}/{message_id}"
        async with session.delete(delete_url, headers=headers) as del_response:
            if del_response.status == 204:
                log_message("info", f"{nama_token}: 🗑️ Pesan lama berhasil dihapus")
            else:
                log_message("error", f"{nama_token}: ❌ Masih gagal menghapus pesan {message_id}")

async def main():
    try:
        with open("pesan.txt", "r") as f:
            pesan_list = [line.strip() for line in f.readlines()]
        if not pesan_list:
            raise ValueError("⚠️ File pesan.txt kosong!")

        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines() if ":" in line]
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong!")

        log_message("info", "🔍 Memeriksa validitas token...")

        if not await validasi_token(tokens):
            log_message("error", "🚨 Beberapa token tidak valid. Harap perbaiki token.txt dan coba lagi.")
            return

        channel_id = input("🔹 Masukkan ID channel: ").strip()
        if not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka!")

        waktu_hapus = float(input("⌛ Set Waktu Hapus Pesan (min 0.01 detik): "))
        waktu_kirim = float(input("📨 Set Waktu Kirim Pesan (min 0.01 detik): "))
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

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

    with tqdm(total=100, desc="📩 Progres Pengiriman") as progress_bar:
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(kirim_pesan(session, channel_id, nama_token, token, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai_dict[nama_token], waktu_stop_dict[nama_token], progress_bar, counter))
                for nama_token, token in tokens
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
