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

def kirim_emoji(channel_id, token, emoji_list):
    """Mengirim emoji ke channel tertentu menggunakan token."""
    headers = {'Authorization': token}
    try:
        payload = {'content': random.choice(emoji_list)}
        send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)

        if send_response.status_code == 200:
            log_message("info", f"Token {token[:10]}...: Emoji dikirim: {payload['content']}")
        elif send_response.status_code == 429:
            retry_after = float(send_response.json().get("retry_after", 1))
            log_message("warning", f"Token {token[:10]}...: Rate limit terkena. Tunggu selama {retry_after:.2f} detik.")
            time.sleep(retry_after)
        else:
            log_message("error", f"Token {token[:10]}...: Gagal mengirim emoji: {send_response.status_code}, {send_response.text}")
    except requests.exceptions.RequestException as e:
        log_message("error", f"Token {token[:10]}...: Request error: {e}")
    except Exception as e:
        log_message("error", f"Token {token[:10]}...: Error tidak terduga: {e}")

def hapus_pesan(channel_id, token, waktu_hapus):
    """Menghapus pesan di channel tertentu menggunakan token."""
    headers = {'Authorization': token}
    max_retries = 5  # Jumlah percobaan maksimum untuk penghapusan
    time.sleep(waktu_hapus)  # Tunggu sebelum menghapus pesan
    retries = 0
    while retries < max_retries:
        try:
            get_response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers)
            if get_response.status_code == 200:
                messages = get_response.json()
                if messages:
                    message_id = messages[0]['id']
                    delete_response = requests.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}", headers=headers)
                    if delete_response.status_code == 204:
                        log_message("info", f"Token {token[:10]}...: Pesan dengan ID {message_id} berhasil dihapus.")
                        break
                    else:
                        log_message("warning", f"Token {token[:10]}...: Gagal menghapus pesan (percobaan {retries + 1}): {delete_response.status_code}, {delete_response.text}")
                        retries += 1
                        time.sleep(1)
                else:
                    log_message("warning", f"Token {token[:10]}...: Tidak ada pesan yang tersedia untuk dihapus.")
                    break
            elif get_response.status_code == 429:
                retry_after = float(get_response.json().get("retry_after", 1))
                log_message("warning", f"Token {token[:10]}...: Rate limit terkena saat GET pesan. Tunggu {retry_after:.2f} detik.")
                time.sleep(retry_after)
            else:
                log_message("error", f"Token {token[:10]}...: Gagal mendapatkan pesan: {get_response.status_code}, {get_response.text}")
                break
        except requests.exceptions.RequestException as e:
            log_message("error", f"Token {token[:10]}...: Request error saat menghapus pesan: {e}")
        except Exception as e:
            log_message("error", f"Token {token[:10]}...: Error tidak terduga saat menghapus pesan: {e}")

# Validasi input
try:
    # Baca file emoji
    with open("emoji.txt", "r") as f:
        emoji_list = [line.strip() for line in f.readlines()]
    if not emoji_list:
        raise ValueError("File emoji kosong.")

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
    waktu_kirim = float(input("Set Waktu Kirim Pesan/Emoji (minimal 0.1 detik): "))
    if waktu_hapus < 0.1 or waktu_kirim < 0.1:
        raise ValueError("Waktu harus minimal 0.1 detik.")

except Exception as e:
    log_message("error", f"Input error: {e}")
    exit()

# Eksekusi dengan ThreadPoolExecutor
log_message("info", "Memulai pengiriman emoji...")
with ThreadPoolExecutor(max_workers=100) as executor:  # Batasi maksimal 100 token berjalan paralel
    for token in tokens:
        # Kirim emoji dan hapus pesan bersamaan untuk setiap token
        executor.submit(kirim_emoji, channel_id, token, emoji_list)
        executor.submit(hapus_pesan, channel_id, token, waktu_hapus)

log_message("info", "Selesai.")
