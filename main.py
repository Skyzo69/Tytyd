import requests
import random
import time
import os
from colorama import Fore

# Informasi Script
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

# Input
channel_id = input("Masukkan ID channel: ")
waktu_hapus = float(input("Set Waktu Hapus Pesan (detik, contoh: 0.07): "))
waktu_kirim = float(input("Set Waktu Kirim Pesan (detik, contoh: 0.07): "))

# Load Data
with open("pesan.txt", "r") as f:
    words = f.readlines()

with open("token.txt", "r") as f:
    authorization = f.readline().strip()

headers = {'Authorization': authorization}

# Countdown
time.sleep(0.07)
print("3")
time.sleep(0.07)
print("2")
time.sleep(0.07)
print("1")
time.sleep(0.07)

os.system('cls' if os.name == 'nt' else 'clear')

# Main Loop
while True:
    # Kirim pesan
    payload = {'content': random.choice(words).strip()}
    r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)
    
    if r.status_code == 200 or r.status_code == 204:
        print(Fore.WHITE + "Sent message: " + Fore.YELLOW + payload['content'])
    else:
        print(Fore.RED + f"Error saat mengirim pesan: {r.status_code} - {r.text}")

    # Ambil pesan terbaru
    response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
    if response.status_code == 200:
        messages = response.json()
        if len(messages) > 0:
            time.sleep(waktu_hapus)
            message_id = messages[0]['id']

            # Hapus pesan
            delete_response = requests.delete(f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}', headers=headers)
            if delete_response.status_code == 204:
                print(Fore.GREEN + f'Pesan dengan ID {message_id} berhasil dihapus')
            elif delete_response.status_code == 403:
                print(Fore.RED + f"Gagal menghapus pesan (403 Forbidden): Token tidak memiliki izin.")
            elif delete_response.status_code == 404:
                print(Fore.RED + f"Gagal menghapus pesan (404 Not Found): Pesan sudah tidak ada.")
            elif delete_response.status_code == 429:
                retry_after = delete_response.json().get('retry_after', 1)
                print(Fore.RED + f"Rate limit tercapai. Tunggu {retry_after} detik...")
                time.sleep(retry_after)
            else:
                print(Fore.RED + f"Gagal menghapus pesan: {delete_response.status_code} - {delete_response.text}")
        else:
            print(Fore.RED + "Tidak ada pesan untuk dihapus.")
    else:
        print(Fore.RED + f"Gagal mengambil pesan: {response.status_code} - {response.text}")

    time.sleep(waktu_kirim)
