import requests

TOKEN = "8306380276:AAHo7cJ6HZ6v3jz71cYGR-c0nBDKtva3_uw"
CHAT_ID = "1036638753"
PESAN = "Halo! Ini adalah pesan dari skrip Python saya."

def kirim_pesan_telegram(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": pesan
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("Pesan berhasil dikirim!")
    else:
        print(f"Gagal mengirim pesan: {response.text}")

# Panggil fungsi
kirim_pesan_telegram(PESAN)