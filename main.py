import requests
import random
import time
import logging
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

def kirim_pesan(channel_id, token, pesan_list, sticker_list, waktu_hapus, waktu_kirim):
    """Mengirim dan menghapus pesan atau sticker pada channel tertentu menggunakan token."""
    headers = {'Authorization': token}
    max_retries = 5  # Jumlah percobaan maksimum untuk penghapusan
    while True:
        try:
            # Pilih secara acak apakah mengirim pesan teks atau sticker
            if random.choice([True, False]) and sticker_list:
                # Kirim sticker
                sticker_id = random.choice(sticker_list)
                payload = {"sticker_ids": [sticker_id]}
                send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages",
                                              json=payload, headers=headers)
                if send_response.status_code == 200:
                    log_message("info", f"Sticker dikirim dengan ID: {sticker_id}")
                else:
                    log_message("error", f"Gagal mengirim sticker: {send_response.status_code}, {send_response.text}")
            else:
                # Kirim pesan teks
                payload = {'content': random.choice(pesan_list)}
                send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages",
                                              data=payload, headers=headers)
                if send_response.status_code == 200:
                    log_message("info", f"Pesan dikirim: {payload['content']}")
                else:
                    log_message("error", f"Gagal mengirim pesan: {send_response.status_code}, {send_response.text}")
            
            # Tunggu sebelum menghapus pesan
            time.sleep(waktu_hapus)

            # Ambil dan hapus pesan terakhir
            get_response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers)
            if get_response.status_code == 200:
                messages = get_response.json()
                if messages:
                    message_id = messages[0]['id']
                    retries = 0
                    while retries < max_retries:
                        delete_response = requests.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}", headers=headers)
                        if delete_response.status_code == 204:
                            log_message("info", f"Pesan dengan ID {message_id} berhasil dihapus.")
                            break
                        else:
                            retries += 1
                            log_message("warning", f"Gagal menghapus pesan (percobaan {retries}): {delete_response.status_code}, {delete_response.text}")
                            time.sleep(1)
                    if retries == max_retries:
                        log_message("error", f"Pesan dengan ID {message_id} gagal dihapus setelah {max_retries} percobaan.")
            elif get_response.status_code == 429:
                retry_after = float(get_response.json().get("retry_after", 1))
                log_message("warning", f"Rate limit terkena saat GET pesan. Tunggu {retry_after:.2f} detik.")
                time.sleep(retry_after)
                continue
            else:
                log_message("error", f"Gagal mendapatkan pesan: {get_response.status_code}, {get_response.text}")

            # Tunggu sebelum mengirim pesan berikutnya
            time.sleep(waktu_kirim)
        except requests.exceptions.RequestException as e:
            log_message("error", f"Request error: {e}")
        except Exception as e:
            log_message("error", f"Error tidak terduga: {e}")

# Validasi input
try:
    # Baca file pesan
    with open("pesan.txt", "r") as f:
        pesan_list = [line.strip() for line in f.readlines()]
    if not pesan_list:
        raise ValueError("File pesan kosong.")

    # Baca file sticker
    try:
        with open("sticker.txt", "r") as f:
            sticker_list = [line.strip() for line in f.readlines() if line.strip().isdigit()]
        if not sticker_list:
            log_message("warning", "File sticker kosong. Hanya pesan teks yang akan dikirim.")
    except FileNotFoundError:
        sticker_list = []
        log_message("warning", "File sticker.txt tidak ditemukan. Hanya pesan teks yang akan dikirim.")

    # Baca file token
    with open("token.txt", "r") as f:
        tokens = [line.strip() for line in f.readlines()]
    if not tokens:
        raise ValueError("File token kosong.")

    # Input ID channel dan waktu delay
    channel_id = input("Masukkan ID channel: ").strip()
    if not channel_id.isdigit():
        raise ValueError("Channel ID harus berupa angka.")
    
    waktu_hapus = float(input("Set Waktu Hapus Pesan (minimal 0.1 detik): "))
    waktu_kirim = float(input("Set Waktu Kirim Pesan (minimal 0.1 detik): "))
    if waktu_hapus < 0.1 or waktu_kirim < 0.1:
        raise ValueError("Waktu harus minimal 0.1 detik.")

except Exception as e:
    log_message("error", f"Input error: {e}")
    exit()

# Eksekusi dengan ThreadPoolExecutor
log_message("info", "Memulai pengiriman pesan...")
with ThreadPoolExecutor(max_workers=5) as executor:
    for token in tokens:
        executor.submit(kirim_pesan, channel_id, token, pesan_list, sticker_list, waktu_hapus, waktu_kirim)

log_message("info", "Selesai.")
