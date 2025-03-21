import random
import time
import logging
import aiohttp
import asyncio
from colorama import Fore, Style
from datetime import datetime, timedelta
from tqdm import tqdm
from itertools import cycle  # Untuk iterasi siklis

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

async def cek_token(session, nama_token, token):
    """Mengecek apakah token valid dengan mencoba request ke API Discord."""
    headers = {"Authorization": token}
    url = "https://discord.com/api/v9/users/@me"
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                log_message("info", f"{nama_token}: ✅ Token valid")
                return True
            elif response.status == 429:
                retry_after = float(response.headers.get("Retry-After", 5))
                log_message("warning", f"{nama_token}: ⏳ Rate limit saat cek token, menunggu {retry_after} detik")
                await asyncio.sleep(retry_after)
                return await cek_token(session, nama_token, token)  # Retry
            else:
                log_message("error", f"{nama_token}: ❌ Token tidak valid (Status: {response.status})")
                return False
    except aiohttp.ClientError as e:
        log_message("error", f"{nama_token}: ❌ Gagal memeriksa token di {url} - {str(e)}")
        return False

async def validasi_token(tokens):
    """Memeriksa semua token sebelum melanjutkan program."""
    async with aiohttp.ClientSession() as session:
        hasil_validasi = await asyncio.gather(
            *(cek_token(session, nama_token, token) for nama_token, token in tokens)
        )
    return all(hasil_validasi)

async def leave_thread(session, channel_id, nama_token, token):
    """Meninggalkan thread channel setelah selesai."""
    headers = {"Authorization": token}
    url = f"https://discord.com/api/v9/channels/{channel_id}/thread-members/@me"
    try:
        async with session.delete(url, headers=headers) as response:
            if response.status == 204:
                log_message("info", f"{nama_token}: 🚪 Berhasil meninggalkan thread channel {channel_id}")
            elif response.status == 429:
                retry_after = float(response.headers.get("Retry-After", 5))
                log_message("warning", f"{nama_token}: ⏳ Rate limit saat leave thread, menunggu {retry_after} detik")
                await asyncio.sleep(retry_after)
                await leave_thread(session, channel_id, nama_token, token)  # Retry
            else:
                log_message("warning", f"{nama_token}: ⚠️ Gagal meninggalkan thread channel {channel_id} (Status: {response.status})")
    except aiohttp.ClientError as e:
        log_message("error", f"{nama_token}: ❌ Gagal meninggalkan thread channel {channel_id} di {url} - {str(e)}")

async def perbarui_token(nama_token, tokens_dict):
    """Memperbarui token dari token.txt jika tidak valid."""
    try:
        with open("token.txt", "r") as f:
            for line in f.readlines():
                if ":" in line:
                    nama, token_baru = line.strip().split(":", 1)
                    if nama == nama_token:
                        if token_baru != tokens_dict[nama_token]:
                            log_message("info", f"{nama_token}: 🔄 Token diperbarui dari token.txt")
                            return token_baru
                        else:
                            log_message("warning", f"{nama_token}: ⚠️ Token di token.txt sama dengan yang lama")
                            return None
        log_message("error", f"{nama_token}: ❌ Tidak ditemukan token baru di token.txt")
        return None
    except Exception as e:
        log_message("error", f"{nama_token}: ❌ Gagal memperbarui token - {str(e)}")
        return None

async def kirim_pesan(session, channel_id, nama_token, token_dict, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, progress_bar, counter, leave_on_complete, tokens_dict, semaphore):
    """Mengirim dan menghapus pesan secara berurutan sesuai pesan.txt lalu loop ke awal"""
    async with semaphore:  # Batasi concurrency
        headers = {"Authorization": token_dict["token"], "Content-Type": "application/json"}
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        pesan_iterator = cycle(pesan_list)
        log_message("info", f"{nama_token}: ▶️ Memulai tugas pengiriman pesan")
        last_file_check = time.time()

        try:
            while datetime.now() < waktu_stop:
                if datetime.now() < waktu_mulai:
                    await asyncio.sleep(1)
                    continue

                # Periksa ulang file setiap 5 menit
                if time.time() - last_file_check >= 300:  # 300 detik = 5 menit
                    with open("pesan.txt", "r") as f:
                        pesan_list[:] = [line.strip() for line in f.readlines()]
                    pesan_iterator = cycle(pesan_list)
                    last_file_check = time.time()
                    log_message("info", f"{nama_token}: 🔄 Pesan diperbarui dari pesan.txt")

                pesan = next(pesan_iterator)
                data = {"content": pesan}

                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            message_id = (await response.json())["id"]
                            counter[nama_token] += 1
                            log_message("info", f"{nama_token}: 📩 Pesan ke {counter[nama_token]} terkirim - ID: {message_id} - {pesan}")
                            progress_bar.update(1)

                            await asyncio.sleep(waktu_hapus)

                            delete_url = f"{url}/{message_id}"
                            for i in range(3):
                                async with session.delete(delete_url, headers=headers) as del_response:
                                    if del_response.status == 204:
                                        log_message("info", f"{nama_token}: 🗑️ Pesan ke {counter[nama_token]} dihapus - ID: {message_id}")
                                        break
                                    elif del_response.status == 404:
                                        log_message("info", f"{nama_token}: ℹ️ Pesan ke {counter[nama_token]} sudah dihapus - ID: {message_id}")
                                        break
                                    elif del_response.status == 429:
                                        retry_after = float(del_response.headers.get("Retry-After", 5))
                                        log_message("warning", f"{nama_token}: ⏳ Rate limit saat hapus, menunggu {retry_after} detik")
                                        await asyncio.sleep(retry_after)
                                    else:
                                        log_message("warning", f"{nama_token}: ⚠️ Gagal menghapus pesan ke {counter[nama_token]} (Percobaan {i+1}, Status: {del_response.status})")
                                        await asyncio.sleep(1)
                            else:
                                log_message("error", f"{nama_token}: ❌ Gagal menghapus pesan ke {counter[nama_token]} setelah 3 percobaan - ID: {message_id}")

                        elif response.status == 429:
                            retry_after = float(response.headers.get("Retry-After", 5))
                            log_message("warning", f"{nama_token}: ⏳ Rate limit saat kirim, menunggu {retry_after} detik")
                            await asyncio.sleep(retry_after)
                        elif response.status == 401:
                            log_message("error", f"{nama_token}: ❌ Token tidak valid (Status: 401), mencoba perbarui...")
                            token_baru = await perbarui_token(nama_token, tokens_dict)
                            if token_baru:
                                token_dict["token"] = token_baru
                                headers["Authorization"] = token_baru
                                log_message("info", f"{nama_token}: 🔄 Melanjutkan dengan token baru")
                            else:
                                log_message("error", f"{nama_token}: ❌ Tidak bisa melanjutkan, tugas berhenti")
                                return
                        else:
                            log_message("error", f"{nama_token}: ❌ Gagal mengirim pesan di {url} (Status: {response.status})")
                            await asyncio.sleep(5)

                    await asyncio.sleep(waktu_kirim)

                except aiohttp.ClientConnectionError as e:
                    log_message("error", f"{nama_token}: ❌ Koneksi gagal di {url} - {str(e)}, membuat ulang session")
                    return await kirim_pesan(aiohttp.ClientSession(), channel_id, nama_token, token_dict, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, progress_bar, counter, leave_on_complete, tokens_dict, semaphore)
                except aiohttp.ClientError as e:
                    log_message("error", f"{nama_token}: ❌ Kesalahan jaringan di {url} - {str(e)}")
                    await asyncio.sleep(1)
                except Exception as e:
                    log_message("error", f"{nama_token}: ❌ Kesalahan tak terduga di {url} - {str(e)}")
                    await asyncio.sleep(5)

        except Exception as e:
            log_message("error", f"{nama_token}: ❌ Tugas pengiriman pesan berhenti - {str(e)}")
            raise

        if leave_on_complete:
            await leave_thread(session, channel_id, nama_token, token_dict["token"])

        log_message("info", f"{nama_token}: ⏹️ Tugas pengiriman pesan selesai")

async def main():
    # Inisialisasi variabel yang akan digunakan
    pesan_list = []
    tokens = []
    tokens_dict = {}
    counter = {}
    tasks = []

    try:
        with open("pesan.txt", "r") as f:
            pesan_list = [line.strip() for line in f.readlines()]
        if not pesan_list:
            raise ValueError("⚠️ File pesan.txt kosong!")

        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines() if ":" in line]
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong!")

        log_message("info", "🔍 Memeriksa validitas token...")
        if not await validasi_token(tokens):
            log_message("error", "🚨 Beberapa token tidak valid. Harap perbaiki token.txt dan coba lagi.")
            return

        tokens_dict = {nama_token: token for nama_token, token in tokens}
        channel_id = input("🔹 Masukkan ID channel: ").strip()
        if not channel_id or not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka dan tidak boleh kosong!")

        waktu_hapus_input = input("⌛ Set Waktu Hapus Pesan (detik, min 0.01): ").strip()
        waktu_kirim_input = input("📨 Set Waktu Kirim Pesan (detik, min 0.01): ").strip()
        if not waktu_hapus_input or not waktu_kirim_input:
            raise ValueError("⚠️ Waktu tidak boleh kosong!")
        waktu_hapus = float(waktu_hapus_input)
        waktu_kirim = float(waktu_kirim_input)
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

        leave_choice = input("🚪 Ingin leave thread setelah selesai untuk setiap token? (y/n): ").strip().lower()
        if not leave_choice:
            raise ValueError("⚠️ Pilihan leave thread tidak boleh kosong!")
        leave_on_complete = leave_choice == 'y'

        waktu_mulai_dict = {}
        waktu_stop_dict = {}
        counter = {nama_token: 0 for nama_token, _ in tokens}

        for nama_token, _ in tokens:
            waktu_mulai_menit_input = input(f"⏳ Masukkan waktu mulai untuk {nama_token} (menit dari sekarang): ").strip()
            waktu_berhenti_menit_input = input(f"⏰ Masukkan waktu berhenti untuk {nama_token} (menit setelah mulai): ").strip()
            if not waktu_mulai_menit_input or not waktu_berhenti_menit_input:
                raise ValueError("⚠️ Waktu mulai/berhenti tidak boleh kosong!")
            waktu_mulai_menit = int(waktu_mulai_menit_input)
            waktu_berhenti_menit = int(waktu_berhenti_menit_input)
            if waktu_mulai_menit < 0 or waktu_berhenti_menit <= 0:
                raise ValueError("⚠️ Waktu mulai harus >= 0 dan waktu berhenti harus > 0 menit!")
            
            waktu_mulai = datetime.now() + timedelta(minutes=waktu_mulai_menit)
            waktu_stop = waktu_mulai + timedelta(minutes=waktu_berhenti_menit)
            waktu_mulai_dict[nama_token] = waktu_mulai
            waktu_stop_dict[nama_token] = waktu_stop

        log_message("info", "🚀 Memulai pengiriman pesan...")
        semaphore = asyncio.Semaphore(100)
        total_pesan = sum(counter.values())  # Akan diperbarui dinamis
        with tqdm(total=None, desc="📩 Progres Pengiriman") as progress_bar:
            progress_bar.total = 0  # Akan diperbarui saat pesan terkirim
            async with aiohttp.ClientSession() as session:
                tasks = [
                    asyncio.create_task(kirim_pesan(
                        session, channel_id, nama_token, {"token": token}, pesan_list, 
                        waktu_hapus, waktu_kirim, waktu_mulai_dict[nama_token], waktu_stop_dict[nama_token], 
                        progress_bar, counter, leave_on_complete, tokens_dict, semaphore
                    ))
                    for nama_token, token in tokens
                ]
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for (nama_token, _), result in zip(tokens, results):
                        if isinstance(result, Exception):
                            log_message("error", f"{nama_token}: ❌ Tugas gagal dengan kesalahan - {str(result)}")
                except KeyboardInterrupt:
                    log_message("warning", "⏹️ Pengguna menghentikan skrip, melakukan cleanup...")
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

            progress_bar.total = sum(counter.values())  # Set total akhir berdasarkan pesan terkirim

    except Exception as e:
        log_message("error", f"🚨 Error selama eksekusi: {str(e)}")

    finally:
        # Selalu tampilkan ringkasan, baik selesai normal maupun dihentikan
        log_message("info", "🎉 Proses selesai (normal atau dihentikan)!")
        log_message("info", "\n📊 Ringkasan Pengiriman:")
        for nama_token, jumlah in counter.items():
            log_message("info", f"🔹 {nama_token}: {jumlah} pesan terkirim")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_message("info", "🏁 Skrip dihentikan oleh pengguna.")
