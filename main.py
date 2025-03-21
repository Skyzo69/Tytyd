import random
import time
import logging
import aiohttp
import asyncio
from colorama import Fore, Style, init
from datetime import datetime, timedelta
from itertools import cycle
from tabulate import tabulate  # Untuk tabel ringkasan

# Inisialisasi colorama untuk mendukung warna di Windows Command Prompt
init(autoreset=True)

# Konfigurasi logging ke file
logging.basicConfig(
    filename="activity.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_message(nama_token, level, message):
    """Log pesan ke file dan konsol dengan format warna-warni dan prefix token"""
    color_map = {"info": Fore.GREEN, "warning": Fore.YELLOW, "error": Fore.RED}
    color = color_map.get(level, Style.RESET_ALL)
    formatted_message = f"[{nama_token}] {message}"
    logging.log(getattr(logging, level.upper()), formatted_message)
    print(f"{color}{formatted_message}{Style.RESET_ALL}")

async def cek_token(session, nama_token, token):
    """Mengecek apakah token valid dengan mencoba request ke API Discord."""
    headers = {"Authorization": token}
    url = "https://discord.com/api/v9/users/@me"
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                log_message(nama_token, "info", "✅ Token valid")
                return True
            elif response.status == 429:
                retry_after = float(response.headers.get("Retry-After", 5))
                log_message(nama_token, "warning", f"⏳ Rate limit saat cek token, menunggu {retry_after} detik")
                await asyncio.sleep(retry_after)
                return await cek_token(session, nama_token, token)
            else:
                log_message(nama_token, "error", f"❌ Token tidak valid (Status: {response.status})")
                return False
    except aiohttp.ClientError as e:
        log_message(nama_token, "error", f"❌ Gagal memeriksa token - {str(e)}")
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
                log_message(nama_token, "info", f"🚪 Berhasil meninggalkan thread channel {channel_id}")
            elif response.status == 429:
                retry_after = float(response.headers.get("Retry-After", 5))
                log_message(nama_token, "warning", f"⏳ Rate limit saat leave thread, menunggu {retry_after} detik")
                await asyncio.sleep(retry_after)
                await leave_thread(session, channel_id, nama_token, token)
            else:
                log_message(nama_token, "warning", f"⚠️ Gagal meninggalkan thread channel {channel_id} (Status: {response.status})")
    except aiohttp.ClientError as e:
        log_message(nama_token, "error", f"❌ Gagal meninggalkan thread channel {channel_id} - {str(e)}")

async def kirim_pesan(session, channel_id, nama_token, token_dict, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, counter, leave_on_complete, semaphore, cycle_completion_event):
    """Mengirim dan menghapus pesan secara berurutan sesuai pesan.txt lalu loop ke awal"""
    async with semaphore:
        headers = {"Authorization": token_dict["token"], "Content-Type": "application/json"}
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        pesan_iterator = cycle(pesan_list)
        log_message(nama_token, "info", "▶️ Memulai tugas pengiriman pesan")
        last_file_check = time.time()

        try:
            while datetime.now() < waktu_stop:
                if datetime.now() < waktu_mulai:
                    await asyncio.sleep(1)
                    continue

                if time.time() - last_file_check >= 300:
                    with open("pesan.txt", "r") as f:
                        pesan_list[:] = [line.strip() for line in f.readlines()]
                    pesan_iterator = cycle(pesan_list)
                    last_file_check = time.time()
                    log_message(nama_token, "info", "🔄 Pesan diperbarui dari pesan.txt")

                pesan = next(pesan_iterator)
                data = {"content": pesan}

                try:
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            message_id = (await response.json())["id"]
                            counter[nama_token] += 1
                            log_message(nama_token, "info", f"✉️ Pesan ke-{counter[nama_token]} terkirim (ID: {message_id}) - {pesan}")

                            await asyncio.sleep(waktu_hapus)

                            delete_url = f"{url}/{message_id}"
                            for i in range(3):
                                start_time = time.time()  # Mulai pengukuran waktu penghapusan
                                async with session.delete(delete_url, headers=headers) as del_response:
                                    elapsed_time = time.time() - start_time  # Hitung waktu yang diperlukan untuk penghapusan
                                    if del_response.status == 204:
                                        log_message(nama_token, "info", f"🗑 Pesan ke-{counter[nama_token]} dihapus (ID: {message_id}) - {elapsed_time:.2f} detik")
                                        cycle_completion_event[nama_token].set()
                                        break
                                    elif del_response.status == 404:
                                        log_message(nama_token, "info", f"ℹ️ Pesan ke-{counter[nama_token]} sudah dihapus (ID: {message_id}) - {elapsed_time:.2f} detik")
                                        cycle_completion_event[nama_token].set()
                                        break
                                    elif del_response.status == 429:
                                        retry_after = float(response.headers.get("Retry-After", 5))
                                        log_message(nama_token, "warning", f"⏳ Rate limit saat hapus, menunggu {retry_after} detik")
                                        await asyncio.sleep(retry_after)
                                    else:
                                        log_message(nama_token, "warning", f"⚠️ Gagal menghapus pesan ke-{counter[nama_token]} (Percobaan {i+1}, Status: {del_response.status})")
                                        await asyncio.sleep(1)
                            else:
                                log_message(nama_token, "error", f"❌ Gagal menghapus pesan ke-{counter[nama_token]} setelah 3 percobaan (ID: {message_id})")

                        elif response.status == 429:
                            retry_after = float(response.headers.get("Retry-After", 5))
                            log_message(nama_token, "warning", f"⏳ Rate limit saat kirim, menunggu {retry_after} detik")
                            await asyncio.sleep(retry_after)
                        elif response.status == 401:
                            log_message(nama_token, "error", "❌ Token tidak valid (Status: 401), tugas berhenti")
                            return
                        else:
                            log_message(nama_token, "error", f"❌ Gagal mengirim pesan (Status: {response.status})")
                            await asyncio.sleep(5)

                    await asyncio.sleep(waktu_kirim)

                except aiohttp.ClientConnectionError as e:
                    log_message(nama_token, "error", f"❌ Koneksi gagal - {str(e)}, membuat ulang session")
                    return await kirim_pesan(aiohttp.ClientSession(), channel_id, nama_token, token_dict, pesan_list, waktu_hapus, waktu_kirim, waktu_mulai, waktu_stop, counter, leave_on_complete, semaphore, cycle_completion_event)
                except aiohttp.ClientError as e:
                    log_message(nama_token, "error", f"❌ Kesalahan jaringan - {str(e)}")
                    await asyncio.sleep(1)
                except Exception as e:
                    log_message(nama_token, "error", f"❌ Kesalahan tak terduga - {str(e)}")
                    await asyncio.sleep(5)

        except Exception as e:
            log_message(nama_token, "error", f"❌ Tugas pengiriman pesan berhenti - {str(e)}")
            raise

        if leave_on_complete:
            await leave_thread(session, channel_id, nama_token, token_dict["token"])

        log_message(nama_token, "info", "⏹️ Tugas pengiriman pesan selesai")

async def monitor_cycles(tokens, cycle_completion_event, waktu_mulai_dict, waktu_stop_dict, counter, waktu_kirim):
    """Monitor siklus pengiriman dan penghapusan pesan untuk semua token dan tampilkan pesan saat ini/estimasi pesan."""
    waktu_stop_terakhir = max(waktu_stop_dict.values())
    waktu_mulai_pertama = min(waktu_mulai_dict.values())
    # Lebar kotak diperbesar untuk menampung angka 4 digit
    box_width = 36  # Lebar total kotak (termasuk border), sebelumnya 30

    while datetime.now() < waktu_stop_terakhir:  # Berhenti hanya jika semua token selesai
        # Token yang aktif: belum selesai (waktu sekarang < waktu_stop)
        active_tokens = [
            nama for nama, _ in tokens
            if datetime.now() < waktu_stop_dict[nama]
        ]

        # Token yang sedang mengirim pesan: sudah melewati waktu mulai dan belum selesai
        sending_tokens = [
            nama for nama in active_tokens
            if datetime.now() >= waktu_mulai_dict[nama]
        ]

        if not active_tokens:
            print(f"{Fore.YELLOW}⏹️ Semua tugas pengiriman selesai, monitor siklus berhenti.{Style.RESET_ALL}")
            break

        if sending_tokens:
            # Cek apakah ada token yang menyelesaikan siklus
            any_cycle_complete = False
            for nama in sending_tokens:
                if cycle_completion_event[nama].is_set():
                    any_cycle_complete = True
                    cycle_completion_event[nama].clear()

            if any_cycle_complete:
                waktu_sekarang = datetime.now()
                total_durasi = (waktu_stop_terakhir - waktu_mulai_pertama).total_seconds()
                durasi_berlalu = (waktu_sekarang - waktu_mulai_pertama).total_seconds()
                persentase = min(100, max(0, (durasi_berlalu / total_durasi) * 100)) if total_durasi > 0 else 0

                # Hitung total pesan saat ini dan estimasi total pesan untuk semua token
                total_pesan_sekarang = sum(counter[nama] for nama in sending_tokens)
                total_estimasi_pesan = 0
                for nama in sending_tokens:
                    durasi_total_detik = (waktu_stop_dict[nama] - waktu_mulai_dict[nama]).total_seconds()
                    estimasi_pesan = int(durasi_total_detik / waktu_kirim) if waktu_kirim > 0 else 0
                    total_estimasi_pesan += estimasi_pesan
                
                # Format teks untuk pesan dan estimasi waktu
                pesan_text = f"Pesan {total_pesan_sekarang}/{total_estimasi_pesan} ({persentase:.1f}% selesai)"
                # Format estimasi waktu selesai menjadi YYYY-MM-DD HH:MM:SS
                waktu_selesai_text = waktu_stop_terakhir.strftime("%Y-%m-%d %H:%M:%S")
                
                # Hitung padding agar teks rata tengah
                padding_pesan = (box_width - 4 - len(pesan_text)) // 2  # -4 untuk border dan spasi
                padding_waktu = (box_width - 4 - len(waktu_selesai_text)) // 2
                padding_pesan_right = box_width - 4 - len(pesan_text) - padding_pesan
                padding_waktu_right = box_width - 4 - len(waktu_selesai_text) - padding_waktu

                # Tampilkan kotak dengan border lengkap
                print(f"{Fore.CYAN}┌{'─' * (box_width - 2)}┐{Style.RESET_ALL}")
                print(f"{Fore.CYAN}│{' ' * padding_pesan}{pesan_text}{' ' * padding_pesan_right}│{Style.RESET_ALL}")
                print(f"{Fore.CYAN}├{'─' * (box_width - 2)}┤{Style.RESET_ALL}")
                print(f"{Fore.CYAN}│{' ' * padding_waktu}{waktu_selesai_text}{' ' * padding_waktu_right}│{Style.RESET_ALL}")
                print(f"{Fore.CYAN}└{'─' * (box_width - 2)}┘{Style.RESET_ALL}")

        await asyncio.sleep(1)  # Polling setiap 1 detik

async def main():
    global waktu_mulai_dict, waktu_stop_dict  # Untuk akses di monitor_cycles
    pesan_list = []
    tokens = []
    counter = {}
    tasks = []
    cycle_completion_event = {}

    print(f"{Fore.CYAN}=== Mulai Skrip Pengiriman Pesan ==={Style.RESET_ALL}")
    try:
        with open("pesan.txt", "r") as f:
            pesan_list = [line.strip() for line in f.readlines()]
        if not pesan_list:
            raise ValueError("⚠️ File pesan.txt kosong!")

        with open("token.txt", "r") as f:
            tokens = [line.strip().split(":") for line in f.readlines() if ":" in line]
        if not tokens:
            raise ValueError("⚠️ File token.txt kosong!")

        print(f"{Fore.YELLOW}--- Memeriksa Token ---{Style.RESET_ALL}")
        if not await validasi_token(tokens):
            print(f"{Fore.RED}🚨 Beberapa token tidak valid. Perbaiki token.txt dan coba lagi.{Style.RESET_ALL}")
            return

        channel_id = input(f"{Fore.CYAN}🔹 Masukkan ID channel: {Style.RESET_ALL}").strip()
        if not channel_id or not channel_id.isdigit():
            raise ValueError("⚠️ Channel ID harus angka dan tidak boleh kosong!")

        waktu_hapus_input = input(f"{Fore.CYAN}⌛ Set Waktu Hapus Pesan (detik, min 0.01): {Style.RESET_ALL}").strip()
        waktu_kirim_input = input(f"{Fore.CYAN}📨 Set Waktu Kirim Pesan (detik, min 0.01): {Style.RESET_ALL}").strip()
        if not waktu_hapus_input or not waktu_kirim_input:
            raise ValueError("⚠️ Waktu tidak boleh kosong!")
        waktu_hapus = float(waktu_hapus_input)
        waktu_kirim = float(waktu_kirim_input)
        if waktu_hapus < 0.01 or waktu_kirim < 0.01:
            raise ValueError("⚠️ Waktu minimal adalah 0.01 detik!")

        leave_choice = input(f"{Fore.CYAN}🚪 Ingin leave thread setelah selesai untuk setiap token? (y/n): {Style.RESET_ALL}").strip().lower()
        if not leave_choice:
            raise ValueError("⚠️ Pilihan leave thread tidak boleh kosong!")
        leave_on_complete = leave_choice == 'y'

        waktu_mulai_dict = {}
        waktu_stop_dict = {}
        counter = {nama_token: 0 for nama_token, _ in tokens}
        cycle_completion_event = {nama_token: asyncio.Event() for nama_token, _ in tokens}

        for nama_token, _ in tokens:
            waktu_mulai_menit_input = input(f"{Fore.CYAN}⏳ Masukkan waktu mulai untuk {nama_token} (menit dari sekarang): {Style.RESET_ALL}").strip()
            waktu_berhenti_menit_input = input(f"{Fore.CYAN}⏰ Masukkan waktu berhenti untuk {nama_token} (menit setelah mulai): {Style.RESET_ALL}").strip()
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

        print(f"{Fore.YELLOW}--- Memulai Pengiriman Pesan ---{Style.RESET_ALL}")
        # Hitung waktu stop terakhir untuk estimasi selesai dan tampilkan
        waktu_stop_terakhir = max(waktu_stop_dict.values())
        print(f"{Fore.CYAN}⏰ Estimasi skrip selesai pada: {waktu_stop_terakhir.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        semaphore = asyncio.Semaphore(100)
        print()
        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(kirim_pesan(
                    session, channel_id, nama_token, {"token": token}, pesan_list,
                    waktu_hapus, waktu_kirim, waktu_mulai_dict[nama_token], waktu_stop_dict[nama_token],
                    counter, leave_on_complete, semaphore, cycle_completion_event
                ))
                for nama_token, token in tokens
            ]
            tasks.append(asyncio.create_task(monitor_cycles(tokens, cycle_completion_event, waktu_mulai_dict, waktu_stop_dict, counter, waktu_kirim)))

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for (nama_token, _), result in zip(tokens, results[:-1]):  # Exclude monitor task
                    if isinstance(result, Exception):
                        log_message(nama_token, "error", f"❌ Tugas gagal - {str(result)}")
            except KeyboardInterrupt:
                print(f"{Fore.YELLOW}⏹️ Pengguna menghentikan skrip, melakukan cleanup...{Style.RESET_ALL}")
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        print(f"{Fore.RED}🚨 Error selama eksekusi: {str(e)}{Style.RESET_ALL}")

    finally:
        print(f"{Fore.YELLOW}--- Ringkasan Pengiriman ---{Style.RESET_ALL}")
        table_data = []
        for nama_token, _ in tokens:
            # Hitung estimasi pesan untuk token ini
            durasi_total_detik = (waktu_stop_dict[nama_token] - waktu_mulai_dict[nama_token]).total_seconds()
            estimasi_pesan = int(durasi_total_detik / waktu_kirim) if waktu_kirim > 0 else 0
            jumlah = counter[nama_token]
            table_data.append([nama_token, f"{jumlah}/{estimasi_pesan} pesan"])
        print(tabulate(table_data, headers=["Token", "Jumlah Pesan Terkirim"], tablefmt="grid"))
        print(f"{Fore.CYAN}=== Proses Selesai (Normal atau Dihentikan) ==={Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}🏁 Skrip dihentikan oleh pengguna.{Style.RESET_ALL}")
