import requests
import time
import os
from colorama import Fore

print("   ____          ____       _                    ")
print("  | __ )  __ _  |  _ \ __ _| |_ ___ _ __   __ _  ")
print("  |  _ \ / _' | | |_) / _' | __/ _ \ '_ \ / _' | ")
print("  | |_) | (_| | |  __/ (_| | ||  __/ | | | (_| | ")
print("  |____/ \__, | |_|   \__,_|\__\___|_| |_|\__, | ")
print("         |___/                            |___/  \n")
print("=================================================")
print("Author: Bg.Pateng")
print("Script: Multi-Token Push Rank Discord")
print("===========================================")
print('PERINGATAN : TIDAK UNTUK DI PERJUAL-BELIKAN')
print("===========================================\n")

channel_id = input("Masukkan ID channel: ").strip()

# Pengaturan waktu manual
while True:
    waktu1 = float(input("Set Waktu Hapus Pesan (minimal 0.1 detik): "))
    waktu2 = float(input("Set Waktu Kirim Pesan (minimal 0.1 detik): "))
    if waktu1 >= 0.1 and waktu2 >= 0.1:
        break
    print("Waktu tidak valid! Masukkan nilai >= 0.1 detik.")

time.sleep(1)
print("3")
time.sleep(1)
print("2")
time.sleep(1)
print("1")
time.sleep(1)

os.system('cls' if os.name == 'nt' else 'clear')

# Baca pesan
with open("pesan.txt", "r") as f:
    words = [line.strip() for line in f.readlines()]

# Baca token
with open("token.txt", "r") as f:
    tokens = [line.strip() for line in f.readlines()]

index_message = 0  # Indeks pesan
index_token = 0    # Indeks token

while True:
    # Ambil token berdasarkan indeks
    authorization = tokens[index_token]

    # Ambil pesan berdasarkan indeks
    payload = {
        'content': words[index_message]
    }

    headers = {
        'Authorization': authorization
    }

    # Kirim pesan ke Discord
    r = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)
    if r.status_code == 200:
        print(Fore.GREEN + f"Token {index_token + 1} sent message: {payload['content']}")
    else:
        print(Fore.RED + f"Token {index_token + 1} failed to send message: {r.status_code}")

    # Update indeks pesan
    index_message += 1
    if index_message >= len(words):  # Reset ke awal jika semua pesan sudah dikirim
        index_message = 0

    # Update indeks token
    index_token += 1
    if index_token >= len(tokens):  # Reset ke awal jika semua token sudah digunakan
        index_token = 0

    # Delay untuk penghapusan dan pengiriman pesan
    time.sleep(waktu1)
    time.sleep(waktu2)
