import asyncio
import random
import time
import logging
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style

# Konfigurasi logging ke file
logging.basicConfig(filename="activity.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def log_message(level, message):
    """Log pesan ke file dan konsol."""
    if level == "info":
        logging.info(message)
        print(Fore.GREEN + message + Style.RESET_ALL)
    elif level == "warning":
        logging.warning(message)
        print(Fore.YELLOW + message + Style.RESET_ALL)
    elif level == "error":
        logging.error(message)
        print(Fore.RED + message + Style.RESET_ALL)

async def kirim_pesan(session, channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim):
    """Mengirim dan menghapus emoji pada channel tertentu menggunakan token secara async."""
    headers = {'Authorization': token}
    max_retries = 5  # Jumlah percobaan maksimum untuk penghapusan
    while True:
        try:
            # Kirim emoji
            payload = {'content': random.choice(emoji_list)}
            async with session.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers) as send_response:
                if send_response.status == 200:
                    log_message("info", f"Token {nama_token} ({token[:10]}...): Emoji dikirim: {payload['content']}")
                elif send_response.status == 429:
                    retry_after = float((await send_response.json()).get("retry_after", 1))
                    log_message("warning", f"Token {nama_token} ({token[:10]}...): Rate limit terkena. Tunggu selama {retry_after:.2f} detik.")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    log_message("error", f"Token {nama_token} ({token[:10]}...): Gagal mengirim emoji: {send_response.status}")
                    break

            await asyncio.sleep(waktu_hapus)

            # Ambil dan hapus pesan
            retries = 0
            while retries < max_retries:
                async with session.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers) as get_response:
                    if get_response.status == 200:
                        messages = await get_response.json()
                        if messages:
                            message_id = messages[0]['id']
                            async with session.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}", headers=headers) as delete_response:
                                if delete_response.status == 204:
                                    log_message("info", f"Token {nama_token} ({token[:10]}...): Pesan dengan ID {message_id} berhasil dihapus.")
                                    break
                                else:
                                    log_message("warning", f"Token {nama_token} ({token[:10]}...): Gagal menghapus pesan (percobaan {retries + 1}): {delete_response.status}")
                                    retries += 1
                                    await asyncio.sleep(1)
                        else:
                            log_message("warning", f"Token {nama_token} ({token[:10]}...): Tidak ada pesan yang tersedia untuk dihapus.")
                            break
                    elif get_response.status == 429:
                        retry_after = float((await get_response.json()).get("retry_after", 1))
                        log_message("warning", f"Token {nama_token} ({token[:10]}...): Rate limit terkena saat GET pesan. Tunggu {retry_after:.2f} detik.")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        log_message("error", f"Token {nama_token} ({token[:10]}...): Gagal mendapatkan pesan: {get_response.status}")
                        break

            if retries == max_retries:
                log_message("error", f"Token {nama_token} ({token[:10]}...): Pesan dengan ID {message_id} gagal dihapus setelah {max_retries} percobaan.")

            await asyncio.sleep(waktu_kirim)
        except Exception as e:
            log_message("error", f"Token {nama_token} ({token[:10]}...): Error tidak terduga: {e}")

async def main():
    try:
        # Baca file emoji
        with open("emoji.txt", "r") as f:
            emoji_list = [line.strip() for line in f.readlines()]
        if not emoji_list:
            raise ValueError("File emoji kosong.")

        # Baca file token dan nama
        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines()]  # Format: nama_token:token
        if not tokens:
            raise ValueError("File token kosong.")

        # Input ID channel dan waktu delay
        channel_id = input("Masukkan ID channel: ").strip()
        if not channel_id.isdigit():
            raise ValueError("Channel ID harus berupa angka.")
        
        waktu_hapus = float(input("Set Waktu Hapus Pesan (minimal 0.05 detik): "))
        waktu_kirim = float(input("Set Waktu Kirim Pesan/Emoji (minimal 0.05 detik): "))
        if waktu_hapus < 0.1 or waktu_kirim < 0.1:
            raise ValueError("Waktu harus minimal 0.1 detik.")

    except Exception as e:
        log_message("error", f"Input error: {e}")
        return

    log_message("info", "Memulai pengiriman emoji...")
    
    # Buat sesi HTTP untuk async requests
    async with aiohttp.ClientSession() as session:
        tasks = []
        for nama_token, token in tokens:
            task = asyncio.create_task(kirim_pesan(session, channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim))
            tasks.append(task)
        
        # Tunggu semua tugas selesai
        await asyncio.gather(*tasks)

    log_message("info", "Selesai.")

# Jalankan program utama
asyncio.run(main())
