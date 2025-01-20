import requests
import random
import time
import os
from colorama import Fore

# Header script
print("   ____          ____       _                    ")
print("  | __ )  __ _  |  _ \ __ _| |_ ___ _ __   __ _  ")
print("  |  _ \ / _' | | |_) / _' | __/ _ \ '_ \ / _' | ")
print("  | |_) | (_| | |  __/ (_| | ||  __/ | | | (_| | ")
print("  |____/ \__, | |_|   \__,_|\__\___|_| |_|\__, | ")
print("         |___/                            |___/  \n")
print("=================================================")
author = "Bg.Pateng"
print("Author: " + author)
script = "Push Rank Discord"
print("Script: " + script)
telegram = "@bangpateng_group"
print("Telegram: " + telegram)
youtube = "Bang Pateng"
print("Youtube: " + youtube)
print("===========================================")
print('PERINGATAN : TIDAK UNTUK DI PERJUAL-BELIKAN')
print("===========================================\n")

time.sleep(1)

# Input pengguna
channel_id = input("Masukkan ID channel: ")
waktu_hapus = float(input("Set Waktu Hapus Pesan (detik, contoh: 0.1): "))
waktu_kirim = float(input("Set Waktu Kirim Pesan (detik, contoh: 0.1): "))

time.sleep(0.1)
print("3")
time.sleep(0.1)
print("2")
time.sleep(0.1)
print("1")
time.sleep(0.1)

# Bersihkan terminal
os.system('cls' if os.name == 'nt' else 'clear')

# Baca pesan dan token dari file
with open("pesan.txt", "r") as f:
    words = f.readlines()

with open("token.txt", "r") as f:
    authorization = f.readline().strip()

# Loop utama
while True:
    channel_id = channel_id.strip()

    # Kirim pesan secara acak
    payload = {
        'content': random.choice(words).strip()
    }

    headers = {
        'Authorization': authorization
    }

    try:
        r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)
        if r.status_code == 200 or r.status_code == 204:
            print(Fore.WHITE + "Sent message: ")
            print(Fore.YELLOW + payload['content'])
        else:
            print(Fore.RED + f"Gagal mengirim pesan: {r.status_code}, response: {r.text}")
            continue
    except Exception as e:
        print(Fore.RED + f"Error saat mengirim pesan: {e}")
        continue

    # Ambil daftar pesan untuk dihapus
    try:
        response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)

        if response.status_code == 200:
            messages = response.json()
            if len(messages) == 0:
                print(Fore.RED + "Tidak ada pesan di channel. Menghentikan script.")
                break
            else:
                time.sleep(waktu_hapus)

                message_id = messages[0]['id']
                for _ in range(3):  # Coba maksimal 3 kali
                    response = requests.delete(f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}', headers=headers)
                    if response.status_code == 204:
                        print(Fore.GREEN + f'Pesan dengan ID {message_id} berhasil dihapus')
                        break
                    elif response.status_code == 429:  # Rate limit
                        retry_after = response.json().get("retry_after", 1)
                        print(Fore.RED + f'Rate limit! Menunggu {retry_after} detik...')
                        time.sleep(retry_after)
                    else:
                        print(Fore.RED + f'Gagal menghapus pesan dengan ID {message_id}: {response.status_code}, response: {response.text}')
                else:
                    print(Fore.RED + f'Gagal menghapus pesan dengan ID {message_id} setelah 3 percobaan.')
        else:
            print(Fore.RED + f'Gagal mendapatkan pesan di channel: {response.status_code}, response: {response.text}')
    except Exception as e:
        print(Fore.RED + f"Error saat mendapatkan/menghapus pesan: {e}")

    time.sleep(waktu_kirim)
