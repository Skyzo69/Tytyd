import random
import time
import logging
import requests
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

def kirim_pesan(channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim):
    """Mengirim dan menghapus emoji pada channel tertentu menggunakan token secara synchronous."""
    headers = {'Authorization': token}
    max_retries = 5  # Jumlah percobaan maksimum untuk penghapusan

    while True:
        try:
            # Kirim emoji dan simpan ID pesan yang dikirim
            payload = {'content': random.choice(emoji_list)}
            send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages",
                                          json=payload, headers=headers)

            if send_response.status_code == 200:
                message_data = send_response.json()
                message_id = message_data['id']  # Simpan ID pesan
                log_message("info", f"Token {nama_token} ({token[:10]}...): Emoji dikirim: {payload['content']}, ID: {message_id}")
            elif send_response.status_code == 429:
                retry_after = send_response.json().get("retry_after", 1)
                log_message("warning", f"Token {nama_token} ({token[:10]}...): Rate limit terkena. Tunggu selama {retry_after:.2f} detik.")
                time.sleep(retry_after)
                continue
            else:
                log_message("error", f"Token {nama_token} ({token[:10]}...): Gagal mengirim emoji: {send_response.status_code}")
                break

            time.sleep(waktu_hapus)

            # Coba hapus pesan dengan ID yang telah disimpan
            retries = 0
            while retries < max_retries:
                delete_response = requests.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}",
                                                  headers=headers)
                if delete_response.status_code == 204:
                    log_message("info", f"Token {nama_token} ({token[:10]}...): Pesan dengan ID {message_id} berhasil dihapus.")
                    break
                elif delete_response.status_code == 404:
                    log_message("warning", f"Token {nama_token} ({token[:10]}...): Pesan tidak ditemukan, mungkin sudah tertimpa.")
                    break
                elif delete_response.status_code == 429:
                    retry_after = delete_response.json().get("retry_after", 1)
                    log_message("warning", f"Token {nama_token} ({token[:10]}...): Rate limit saat menghapus pesan. Tunggu {retry_after:.2f} detik.")
                    time.sleep(retry_after)
                    continue
                else:
                    log_message("warning", f"Token {nama_token} ({token[:10]}...): Gagal menghapus pesan (percobaan {retries + 1}): {delete_response.status_code}")
                    retries += 1
                    time.sleep(1)

            if retries == max_retries:
                log_message("error", f"Token {nama_token} ({token[:10]}...): Pesan dengan ID {message_id} gagal dihapus setelah {max_retries} percobaan.")

            time.sleep(waktu_kirim)
        except Exception as e:
            log_message("error", f"Token {nama_token} ({token[:10]}...): Error tidak terduga: {e}")

def main():
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
        
        waktu_hapus = float(input("Set Waktu Hapus Pesan (minimal 0.01 detik): "))
        waktu_kirim = float(input("Set Waktu Kirim Pesan/Emoji (minimal 0.01 detik): "))
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("Waktu harus minimal 0.01 detik.")

    except Exception as e:
        log_message("error", f"Input error: {e}")
        return

    log_message("info", "Memulai pengiriman emoji...")

    # Jalankan proses untuk setiap token
    for nama_token, token in tokens:
        kirim_pesan(channel_id, nama_token, token, emoji_list, waktu_hapus, waktu_kirim)

    log_message("info", "Selesai.")

# Jalankan program utama
if __name__ == "__main__":
    main()
