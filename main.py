from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# ข้อความข่าวสำรอง/ข่าวล่าสุดจากเพจ Facebook (กรณีดึงจากเว็บหลักไม่เจอ หรือต้องการอัปเดตข่าวเพจด่วน)
FACEBOOK_NEWS_CACHE = "หลักสูตรที่เปิดรับสมัครล่าสุดจากเพจ สนพ.มค.: 1. ช่างไฟฟ้าภายในอาคาร (ฝึกอบรมฟรี) 2. ช่างเชื่อมอาร์กโลหะด้วยมือ"
LATEST_NEWS_CONTEXT = FACEBOOK_NEWS_CACHE

@app.route('/scrape-dsd', methods=['GET'])
def scrape_dsd():
    global LATEST_NEWS_CONTEXT
    web_news = ""
    try:
        # 1. ดึงข้อมูลประกาศสดๆ จากหน้าเว็บ สนพ.มหาสารคาม
        url = "https://www.dsd.go.th/mahasarakham"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # ดึงหัวข้อที่มีคำว่า ฝึกอบรม หรือ รับสมัคร
            headlines = [a.get_text(strip=True) for a in soup.find_all('a') if any(k in a.get_text() for k in ['ฝึกอบรม', 'รับสมัคร', 'ประกาศ'])]
            if headlines:
                web_news = "ข่าวประกาศหน้าเว็บ: " + " | ".join(headlines[:3])
    except Exception as e:
        print("Scrape error:", e)

    # 2. รวมข้อมูลข่าวสารจากเว็บหลัก + ข่าวสารด่วนจาก Facebook เพจ
    if web_news:
        LATEST_NEWS_CONTEXT = f"{web_news} [ข่าวสารอัปเดตล่าสุด: {FACEBOOK_NEWS_CACHE}]"
    else:
        LATEST_NEWS_CONTEXT = FACEBOOK_NEWS_CACHE

    return jsonify({
        "status": "ok", 
        "news_context": LATEST_NEWS_CONTEXT
    })

# API Endpoint สำหรับกดส่งข่าวสารด่วนจาก Facebook เพจเข้ามาอัปเดตในระบบ
@app.route('/update-facebook-news', methods=['POST'])
def update_facebook_news():
    global FACEBOOK_NEWS_CACHE
    data = request.get_json()
    if data and 'news' in data:
        FACEBOOK_NEWS_CACHE = data['news']
        return jsonify({"status": "success", "updated_news": FACEBOOK_NEWS_CACHE})
    return jsonify({"status": "error", "message": "Missing 'news' parameter"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
