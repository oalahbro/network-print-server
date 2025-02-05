import socket
import win32print
import json
import os
import logging
import time
import threading
from flask import Flask, jsonify, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from waitress import serve
import servicemanager
import win32service
import win32serviceutil
import win32event

# Konfigurasi
CONFIG_FILE = "conf.json"
LOG_FILE = "server_log.txt"
BACKUP_LOG_FILE = "log1.bak"
LOG_MAX_SIZE = 5 * 1024 * 1024  # 1MB
LOG_RETENTION_DAYS = 30
DEFAULT_PORT = 9100
HOST = "0.0.0.0"

# Flask Web Dashboard
app = Flask(__name__)
status = {"last_request": None, "total_jobs": 0}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "DEFAULT": "HAKA",
            "PRINTER_NAME": r"\\\\LAPTOP-EN2ING59\\HAKA",
            "PORT": DEFAULT_PORT
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    return config

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def rotate_log():
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX_SIZE:
        logging.shutdown()  # Tutup file log sebelum mengganti nama
        
        # Cari nomor backup tertinggi
        backup_files = [f for f in os.listdir(".") if f.startswith("log") and f.endswith(".bak")]
        backup_numbers = sorted(
            [int(f[3:-4]) for f in backup_files if f[3:-4].isdigit()], reverse=True
        )
        
        next_backup_number = backup_numbers[0] + 1 if backup_numbers else 1
        new_backup_file = f"log{next_backup_number}.bak"

        # Rename file log ke backup baru
        os.rename(LOG_FILE, new_backup_file)
        logging.info(f"Log rotated: {new_backup_file}")

def cleanup_old_logs():
    cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for file in os.listdir("."):
        if file.startswith("server_log_") and file.endswith(".txt"):
            file_date = datetime.strptime(file[11:21], "%Y-%m-%d")
            if file_date < cutoff_date:
                os.remove(file)
                logging.info(f"Deleted old log: {file}")

logging.basicConfig(
    filename=LOG_FILE, level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True  # Memastikan semua log masuk ke file
)

# Tambahkan logging ke console untuk debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

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
    logging.info("🛠 Starting service ...")  # Tambahkan log awal
    config = load_config()
    port = config.get("PORT", DEFAULT_PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, port))
        server.listen(5)
        logging.info(f"🚀 Print server starting on port {port}...")
        logging.info(f"✅ Print server listening on {HOST}:{port}")

        while True:
            rotate_log()
            cleanup_old_logs()
            client, addr = server.accept()
            logging.info(f"🔗 Connection received from {addr}")

            with client:
                data = client.recv(1024)
                logging.info(f"📩 Received {len(data)} bytes")
                if data.startswith(b"\x1b@"):
                    logging.info("🖨 Sending data to printer...")
                    send_to_printer(data)


def run_server():
    threading.Thread(target=start_server, daemon=True).start()

def read_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return f.readlines()
    return []

def get_printer_list():
    """ Mengambil daftar printer yang tersedia dalam format UNC """
    printers = []
    for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_CONNECTIONS + win32print.PRINTER_ENUM_LOCAL):
        printers.append(printer[2])  # Ambil nama printer saja

    return printers

@app.route("/", methods=["GET", "POST"])
def dashboard():
    config = load_config()
    printers = get_printer_list()
    default_printer = config.get("DEFAULT", "")

    if request.method == "POST":
        new_default = request.form["default_printer"].strip()
        
        # Buat path UNC berdasarkan nama printer yang dipilih
        computer_name = os.environ['COMPUTERNAME']
        new_printer_path = f"\\\\{computer_name}\\{new_default}"

        # Update konfigurasi
        config["DEFAULT"] = new_default
        config["PRINTER_NAME"] = new_printer_path
        save_config(config)

        return redirect(url_for("dashboard"))

    logs=read_log()
    logs = [line.encode('utf-8').decode('unicode_escape') if isinstance(line, str) else line for line in logs]
    return render_template(
        "dashboard.html",
        status=status,
        config=config,
        logs=logs,  # Sekarang logs sudah diproses sebelumnya
        printers=printers,
        default_printer=default_printer
    )

class PrintServerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "PrintServerService"
    _svc_display_name_ = "Print Server Service"
    _svc_description_ = "Custom print server that handles network print requests."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Print Server Service started.")
        run_server()
        app.run()
        while self.running:
            time.sleep(1)

    def SvcStop(self):
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

if __name__ == "__main__":
    
    run_server()  # Jalankan print server di thread terpisah
    serve(app, host="0.0.0.0", port=5000)