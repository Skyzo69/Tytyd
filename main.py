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

async def kirim_pesan(session, channel_id, nama_token, token, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, progress_bar, counter):
    """Mengirim dan menghapus pesan pada channel tertentu menggunakan token secara asynchronous."""
    headers = {"Authorization": token}
    max_retries = 5
    message_id = None

    while datetime.now() < waktu_mulai:
        await asyncio.sleep(1)

    log_message("info", f"{nama_token}: ▶️ Mulai mengirim pesan pada {waktu_mulai.strftime('%H:%M:%S')}")

    while datetime.now() < waktu_stop:
        try:
            payload = {"content": random.choice(pesan_list)}
            counter[nama_token] += 1

            async with session.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
            ) as send_response:
                if send_response.status == 200:
                    message_data = await send_response.json()
                    if "id" in message_data:
                        message_id = message_data["id"]
                        log_message("info", f"{nama_token}: ✅ Pesan dikirim ke-{counter[nama_token]} (ID: {message_id})")
                elif send_response.status == 429:
                    retry_after = (await send_response.json()).get("retry_after", 1)
                    log_message("warning", f"{nama_token}: ⏳ Rate limit! Tunggu {retry_after:.2f} detik.")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    log_message("error", f"{nama_token}: ❌ Gagal kirim pesan ({send_response.status})")
                    break

            await asyncio.sleep(waktu_hapus)

            retries = 0
            while retries < max_retries and message_id:
                async with session.delete(
                    f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}",
                    headers=headers,
                ) as delete_response:
                    if delete_response.status == 204:
                        log_message("info", f"{nama_token}: 🗑️ Pesan {message_id} dihapus")
                        break
                    elif delete_response.status == 404:
                        log_message("warning", f"{nama_token}: ❓ Pesan {message_id} tidak ditemukan")
                        break
                    elif delete_response.status == 429:
                        retry_after = (await delete_response.json()).get("retry_after", 1)
                        log_message("warning", f"{nama_token}: ⏳ Rate limit saat hapus! Tunggu {retry_after:.2f} detik.")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        log_message("warning", f"{nama_token}: ⚠️ Gagal hapus pesan (Percobaan {retries + 1})")
                        retries += 1
                        await asyncio.sleep(1)

            if retries == max_retries and message_id:
                log_message("error", f"{nama_token}: ❌ Gagal hapus pesan {message_id} setelah {max_retries} percobaan.")

            await asyncio.sleep(waktu_kirim)
            progress_bar.update(1)
        except Exception as e:
            log_message("error", f"{nama_token}: 🚨 Error: {e}")

    log_message("info", f"{nama_token}: ⏹️ Waktu habis, berhenti mengirim pesan. Total terkirim: {counter[nama_token]}")

async def main():
    try:
        with open("pesan.txt", "r") as f:
            pesan_list = [line.strip() for line in f.readlines() if line.strip()]
        if not pesan_list:
            raise ValueError("⚠️ File pesan.txt kosong!")

        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines()]
            tokens = [(nama, tkn) for nama, tkn in tokens if len(tkn) > 10]
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong atau format salah!")

        channel_id = input("🔹 Masukkan ID channel: ").strip()
        if not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka!")

        waktu_hapus = float(input("⌛ Set Waktu Hapus Pesan (min 0.01 detik): "))
        waktu_kirim = float(input("📨 Set Waktu Kirim Pesan (min 0.01 detik): "))
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

        waktu_mulai_dict = {}
        waktu_stop_dict = {}
        counter = {}

        for nama_token, _ in tokens:
            waktu_mulai_menit = int(input(f"⏳ Waktu mulai untuk {nama_token} (menit dari sekarang): "))
            waktu_berhenti_menit = int(input(f"⏰ Waktu berhenti untuk {nama_token} (menit setelah mulai): "))

            waktu_mulai = datetime.now() + timedelta(minutes=waktu_mulai_menit)
            waktu_stop = waktu_mulai + timedelta(minutes=waktu_berhenti_menit)

            waktu_mulai_dict[nama_token] = waktu_mulai
            waktu_stop_dict[nama_token] = waktu_stop
            counter[nama_token] = 0

    except Exception as e:
        log_message("error", f"🚨 Input error: {e}")
        return

    log_message("info", "🚀 Memulai pengiriman pesan...")

    total_pesan = sum(
        (waktu_stop_dict[nama_token] - waktu_mulai_dict[nama_token]).total_seconds() // max(waktu_kirim + waktu_hapus, 0.01)
        for nama_token, _ in tokens
    )

    with tqdm(total=int(total_pesan), desc="📩 Progres Pengiriman") as progress_bar:
        async with aiohttp.ClientSession() as session:
            tasks = [
                kirim_pesan(session, channel_id, nama_token, token, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai_dict[nama_token], waktu_stop_dict[nama_token], progress_bar, counter)
                for nama_token, token in tokens
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    log_message("info", "🎉 Semua token telah selesai!")
