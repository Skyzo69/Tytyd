#!/bin/bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip -y
python3 -m pip install --upgrade pip

# Buat dan aktifkan virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Instal dependensi di dalam venv
pip install -r requirements.txt

echo "✅ Instalasi selesai! Jalankan script dengan: source myenv/bin/activate && python3 main.py"
