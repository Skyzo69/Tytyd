#!/bin/bash

# Perbarui paket dan instal Python jika belum ada
echo "🔹 Memeriksa dan memperbarui sistem..."
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip -y

# Pastikan pip terbaru
echo "🔹 Memperbarui pip..."
python3 -m pip install --upgrade pip

# Instal semua dependensi yang diperlukan
echo "🔹 Menginstal dependensi..."
pip install -r requirements.txt

echo "✅ Instalasi selesai! Jalankan script dengan: python3 script.py"
