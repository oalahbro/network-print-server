function logFixer() {
    document.querySelectorAll(".log-line").forEach(function (el) {
        el.innerHTML = el.innerHTML
            .replace(/ð/g, "🚀")  // Ganti karakter yang salah dengan emoji aslinya
            .replace(/ð/g, "🛠️") // Tambahkan pattern lain jika diperlukan
            .replace(/ð¨ï¸/g, "🖨️") // Tambahkan pattern lain jika diperlukan
            .replace(/ð/g, "🔗") // Tambahkan pattern lain jika diperlukan
            .replace(/â/g, "✅") // Tambahkan pattern lain jika diperlukan
            .replace(/ð¨/g, "🖶") // Tambahkan pattern lain jika diperlukanb'
            .replace(/ð/g, "📃") // Tambahkan pattern lain jika diperlukanb'
            .replace(//g, "\n") // Tambahkan pattern lain jika diperlukan
            .replace(//g, "\n"); // Tambahkan pattern lain jika diperlukan
    });
};

function refreshLogs() {
    fetch(window.location.href) // Mengambil ulang halaman dashboard
        .then(response => response.text())
        .then(html => {
            let parser = new DOMParser();
            let doc = parser.parseFromString(html, "text/html");
            let newLogs = doc.getElementById("logContainer").innerHTML;
            let newQueue = doc.getElementById("queueContainer").innerHTML;

            document.getElementById("queueContainer").innerHTML = newQueue; // Update log
            document.getElementById("logContainer").innerHTML = newLogs; // Update log         

            logFixer(); // Panggil ulang fungsi untuk memperbaiki karakter
        })
        .catch(error => console.error("Error fetching logs:", error));
}

function showTab(tabName) {
    const logsTab = document.getElementById("logsTab");
    const historyTab = document.getElementById("historyTab");

    if (tabName === "logs") {
        logsTab.style.display = "block";
        historyTab.style.display = "none";
    } else {
        logsTab.style.display = "none";
        historyTab.style.display = "block";
    }
}

function reprint(jobId) {
    fetch(`/reprint/${jobId}`, {
        method: "POST"
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                showNotification("✅ Reprint berhasil!");
                refreshLogs()
            } else {
                showNotification("Gagal ❌ : " + data.message);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            showNotification("❌ Server error!");
        });
}
function viewJob(jobId) {
    fetch(`/view/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {

                // convert hex ke text
                let text = hexToString(data.raw_data);
                let clean = text.replace(/\x1B./g, '')
                    // hapus GS (0x1D) + 1 byte setelahnya
                    .replace(/\x1D./g, '')
                    // hapus control char KECUALI \n (0x0A) dan \r (0x0D)
                    .replace(/[\x00-\x09\x0B-\x0C\x0E-\x1F\x7F]/g, '');
                showModal(clean);
            } else {
                showNotification("Data tidak ditemukan");
            }
        })
        .catch(error => {
            console.error(error);
            showNotification("Server error");
        });
}

function hexToString(hex) {
    let bytes = new Uint8Array(hex.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
    return new TextDecoder().decode(bytes);
}

function showModal(content) {
    document.getElementById("modalContent").textContent = content;
    document.getElementById("modalOverlay").style.display = "flex";
}

function closeModal() {
    document.getElementById("modalOverlay").style.display = "none";
}
document.getElementById("modalOverlay").addEventListener("click", function (e) {
    if (e.target === this) {
        closeModal();
    }
});
function showNotification(message) {
    let notif = document.createElement("div");
    notif.innerText = message;
    notif.classList.add("toast", "glass");

    document.body.appendChild(notif);

    setTimeout(() => {
        notif.remove();
    }, 2000);
}
document.addEventListener("DOMContentLoaded", logFixer);