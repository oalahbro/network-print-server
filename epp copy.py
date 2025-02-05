import sys
import os
import socket
import win32print
import json
import logging
import threading
from flask import Flask, jsonify, render_template, request, redirect, url_for
from datetime import datetime, timedelta

# Konfigurasi
CONFIG_FILE = "conf.json"
LOG_FILE = "server_log.txt"
DEFAULT_PORT = 9100
HOST = "0.0.0.0"

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),  # Log ke file
        logging.StreamHandler(sys.stdout)  # Log ke terminal
    ]
)

# Flask Web Dashboard
app = Flask(__name__)
status = {"last_request": None, "total_jobs": 0}

def load_config():
    """Load konfigurasi dari file JSON."""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "DEFAULT": "HAKA",
            "PRINTER_NAME": r"\\\\LAPTOP-EN2ING59\\HAKA",
            "PORT": DEFAULT_PORT
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    """Simpan konfigurasi ke file JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def send_to_printer(data):
    """Mengirim data ke printer."""
    try:
        config = load_config()
        PRINTER_NAME = config.get("PRINTER_NAME", "")
        if not PRINTER_NAME:
            raise ValueError("Printer name not found in config.")
        
        logging.info(f"📄 Menerima permintaan cetak: {data}")
        logging.info(f"🖨️ Mengirim ke printer: {PRINTER_NAME}")

        hprinter = win32print.OpenPrinter(PRINTER_NAME)
        job_info = win32print.StartDocPrinter(hprinter, 1, ("Print Job", None, "RAW"))
        win32print.StartPagePrinter(hprinter)
        win32print.WritePrinter(hprinter, data)
        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)
        win32print.ClosePrinter(hprinter)

        status["total_jobs"] += 1
        status["last_request"] = str(datetime.now())
        logging.info("✅ Cetak berhasil.")
    except Exception as e:
        logging.error(f"❌ Kesalahan printer: {e}")

def start_server():
    """Jalankan print server."""
    config = load_config()
    port = config.get("PORT", DEFAULT_PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        try:
            server.bind((HOST, port))
            server.listen(5)
            logging.info(f"🚀 Print server berjalan di {HOST}:{port}...")

            while True:
                client, addr = server.accept()
                logging.info(f"🔗 Koneksi diterima dari {addr}")

                with client:
                    data = client.recv(1024)
                    if data:
                        send_to_printer(data)

        except Exception as e:
            logging.error(f"❌ Server error: {e}")

def run_server():
    """Jalankan print server di thread terpisah."""
    threading.Thread(target=start_server, daemon=True).start()

@app.route("/", methods=["GET", "POST"])
def dashboard():
    """Tampilan dashboard Flask."""
    config = load_config()
    default_printer = config.get("DEFAULT", "")

    if request.method == "POST":
        new_default = request.form["default_printer"].strip()
        computer_name = os.environ['COMPUTERNAME']
        new_printer_path = f"\\\\{computer_name}\\{new_default}"

        config["DEFAULT"] = new_default
        config["PRINTER_NAME"] = new_printer_path
        save_config(config)

        return redirect(url_for("dashboard"))

    return render_template(
        "dashboard.html",
        status=status,
        config=config,
        default_printer=default_printer
    )

if __name__ == "__main__":
    logging.info("🛠 Main script running...")
    
    run_server()  # Jalankan print server di thread terpisah
    
    logging.info(" Menjalankan Flask...")
    app.run(host="0.0.0.0", port=5000, debug=False)
