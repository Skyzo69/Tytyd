import random
import time
import logging
import aiohttp
import asyncio
from colorama import Fore, Style
from datetime import datetime, timedelta
from tqdm import tqdm
from tabulate import tabulate

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

async def kirim_pesan(session, channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim, waktu_stop, progress_bar):
    """Mengirim dan menghapus emoji pada channel tertentu menggunakan token secara asynchronous."""
    headers = {"Authorization": token}
    max_retries = 5  # Jumlah percobaan maksimum untuk penghapusan
    message_id = None  # Variabel untuk menyimpan ID pesan

    while datetime.now() < waktu_stop:
        try:
            # Kirim emoji dan simpan ID pesan yang dikirim
            payload = {"content": random.choice(emoji_list)}
            async with session.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
            ) as send_response:
                if send_response.status == 200:
                    message_data = await send_response.json()
                    message_id = message_data["id"]  # Simpan ID pesan
                    log_message("info", f"{nama_token}: ✅ Emoji dikirim {payload['content']} (ID: {message_id})")
                elif send_response.status == 429:
                    retry_after = (await send_response.json()).get("retry_after", 1)
                    log_message("warning", f"{nama_token}: ⏳ Rate limit! Tunggu {retry_after:.2f} detik.")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    log_message("error", f"{nama_token}: ❌ Gagal kirim emoji ({send_response.status})")
                    break

            await asyncio.sleep(waktu_hapus)

            # Coba hapus pesan dengan ID yang telah disimpan
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
            progress_bar.update(1)  # Update progress bar setiap pesan dikirim
        except Exception as e:
            log_message("error", f"{nama_token}: 🚨 Error: {e}")

    log_message("info", f"{nama_token}: ⏹️ Waktu habis, berhenti mengirim emoji.")

async def main():
    try:
        # Baca file emoji
        with open("emoji.txt", "r") as f:
            emoji_list = [line.strip() for line in f.readlines()]
        if not emoji_list:
            raise ValueError("⚠️ File emoji.txt kosong!")

        # Baca file token dan nama
        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines()]  # Format: nama_token:token
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong!")

        # Input dari pengguna
        channel_id = input("🔹 Masukkan ID channel: ").strip()
        if not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka!")

        waktu_hapus = float(input("⌛ Set Waktu Hapus Pesan (min 0.01 detik): "))
        waktu_kirim = float(input("📨 Set Waktu Kirim Pesan (min 0.01 detik): "))
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

        waktu_berhenti_menit = int(input("⏰ Masukkan waktu berhenti (menit): "))
        if waktu_berhenti_menit <= 0:
            raise ValueError("⚠️ Waktu berhenti harus lebih dari 0 menit!")

        waktu_stop = datetime.now() + timedelta(minutes=waktu_berhenti_menit)

    except Exception as e:
        log_message("error", f"🚨 Input error: {e}")
        return

    log_message("info", f"🚀 Memulai pengiriman hingga {waktu_stop.strftime('%H:%M:%S')}...")

    # Progress bar
    total_pesan = waktu_berhenti_menit * 60 // (waktu_kirim + waktu_hapus)
    with tqdm(total=total_pesan, desc="📩 Progres Pengiriman") as progress_bar:
        async with aiohttp.ClientSession() as session:
            if hasattr(asyncio, "TaskGroup"):  # Python 3.11+
                async with asyncio.TaskGroup() as tg:
                    for nama_token, token in tokens:
                        tg.create_task(
                            kirim_pesan(session, channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim, waktu_stop, progress_bar)
                        )
            else:  # Python 3.10 ke bawah
                tasks = [
                    kirim_pesan(session, channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim, waktu_stop, progress_bar)
                    for nama_token, token in tokens
                ]
                await asyncio.gather(*tasks)

    log_message("info", "🎉 Selesai!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
