import requests
import random
import time
import threading
from colorama import Fore

# Fungsi untuk mengirim pesan dan menghapus pesan
def kirim_dan_hapus_pesan(channel_id, token, pesan_list):
    headers = {'Authorization': token}

    while True:
        try:
            # Kirim pesan
            payload = {'content': random.choice(pesan_list)}
            start_post = time.time()
            send_response = requests.post(f"https://discord.com/api/v9/channels/{channel_id}/messages", data=payload, headers=headers)
            end_post = time.time()

            if send_response.status_code == 200:
                print(Fore.GREEN + f"Pesan dikirim: {payload['content']}")
            else:
                print(Fore.RED + f"Gagal mengirim pesan: {send_response.status_code}")
                break

            time.sleep(0.01)  # Waktu tunggu 0.01 detik untuk penghapusan pesan

            # Ambil pesan dan hapus
            start_get = time.time()
            response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
            end_get = time.time()

            if response.status_code == 200:
                messages = response.json()
                if messages:
                    message_id = messages[0]['id']
                    start_delete = time.time()
                    delete_response = requests.delete(f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}", headers=headers)
                    end_delete = time.time()

                    if delete_response.status_code == 204:
                        print(Fore.GREEN + f"Pesan dengan ID {message_id} berhasil dihapus.")
                    else:
                        print(Fore.RED + f"Gagal menghapus pesan: {delete_response.status_code}")
                else:
                    print(Fore.YELLOW + "Tidak ada pesan untuk dihapus.")
            else:
                print(Fore.RED + f"Gagal mendapatkan pesan: {response.status_code}")

            print(f"Waktu GET: {end_get - start_get:.4f} detik")
            print(f"Waktu DELETE: {end_delete - start_delete:.4f} detik")

        except Exception as e:
            print(Fore.RED + f"Terjadi error: {str(e)}")
            break

        time.sleep(0.01)  # Waktu tunggu 0.01 detik untuk pengiriman pesan berikutnya

# Baca file pesan
with open("pesan.txt", "r") as f:
    pesan_list = [line.strip() for line in f.readlines()]

# Baca file token
with open("token.txt", "r") as f:
    tokens = [line.strip() for line in f.readlines()]

# Input channel
channel_id = input("Masukkan ID channel: ").strip()

# Mulai thread untuk setiap token
threads = []
for token in tokens:
    t = threading.Thread(target=kirim_dan_hapus_pesan, args=(channel_id, token, pesan_list))
    t.start()
    threads.append(t)

# Tunggu semua thread selesai
for t in threads:
    t.join()
