from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# คีย์การเข้าถึงข้อมูลข่าวสาร สนพ.มค.
NEWS_CACHE = "หลักสูตรที่เปิดรับสมัครล่าสุด: 1. ช่างไฟฟ้าภายในอาคาร (ฝึกอบรมฟรี) 2. ช่างเชื่อมอาร์กโลหะด้วยมือ"

@app.route('/scrape-dsd', methods=['GET'])
def scrape_dsd():
    global NEWS_CACHE
    try:
        # ตัวอย่างการดึงข้อมูลจากหน้าเว็บ สนพ.มหาสารคาม
        url = "https://www.dsd.go.th/mahasarakham"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # ดึงข้อความประกาศหรือข่าวประชาสัมพันธ์
            headlines = [a.get_text(strip=True) for a in soup.find_all('a') if 'ฝึกอบรม' in a.get_text()]
            if headlines:
                NEWS_CACHE = "ข่าวประกาศล่าสุด สนพ.มค.: " + " | ".join(headlines[:5])
    except Exception as e:
        print("Scrape error:", e)
    
    return jsonify({"status": "ok", "news_context": NEWS_CACHE})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)