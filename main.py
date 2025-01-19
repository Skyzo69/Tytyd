import requests
import random
import time
from colorama import Fore

# Input channel dan waktu delay
channel_id = input("Masukkan ID channel: ").strip()
waktu_hapus = float(input("Set Waktu Hapus Pesan (minimal 0.01 detik): "))
waktu_kirim = float(input("Set Waktu Kirim Pesan (minimal 0.1 detik): "))

# Baca file pesan
try:
    with open("pesan.txt", "r") as f:
        pesan_list = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    print(Fore.RED + "Error: File 'pesan.txt' tidak ditemukan.")
    exit()

# Baca file token
try:
    with open("token.txt", "r") as f:
        tokens = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    print(Fore.RED + "Error: File 'token.txt' tidak ditemukan.")
    exit()

if not tokens:
    print(Fore.RED + "Error: Tidak ada token di file 'token.txt'.")
    exit()

# Mulai loop
index_token = 0  # Untuk penggunaan token secara bergantian
while True:
    # Pilih token secara bergantian
    authorization = tokens[index_token]
    headers = {'Authorization': authorization}

    # Kirim pesan
    payload = {'content': random.choice(pesan_list)}
    send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)

    if send_response.status_code == 200:
        print(Fore.GREEN + f"Pesan dikirim: {payload['content']}")
    else:
        print(Fore.RED + f"Gagal mengirim pesan: {send_response.status_code}, {send_response.text}")
        break

    # Tunggu sebelum menghapus pesan
    time.sleep(waktu_hapus)

    # Ambil pesan terbaru
    get_response = requests.get(f"https://discord.com/api/v9/channels/{channel_id}/messages", headers=headers)
    if get_response.status_code == 200:
        messages = get_response.json()
        if messages:
            # Hapus pesan terbaru
            message_id = messages[0]['id']
            delete_response = requests.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}", headers=headers)
            if delete_response.status_code == 204:
                print(Fore.GREEN + f"Pesan dengan ID {message_id} berhasil dihapus.")
            else:
                print(Fore.RED + f"Gagal menghapus pesan dengan ID {message_id}: {delete_response.status_code}, {delete_response.text}")
        else:
            print(Fore.YELLOW + "Tidak ada pesan untuk dihapus.")
    else:
        print(Fore.RED + f"Gagal mendapatkan pesan: {get_response.status_code}, {get_response.text}")

    # Tunggu sebelum mengirim pesan berikutnya
    time.sleep(waktu_kirim)

    # Perbarui token untuk iterasi berikutnya
    index_token += 1
    if index_token >= len(tokens):
        index_token = 0
