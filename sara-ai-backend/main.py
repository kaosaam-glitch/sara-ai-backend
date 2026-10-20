from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import datetime
import os

app = Flask(__name__)

def get_thai_date():
    # คำนวณวันที่และปี พ.ศ. ปัจจุบัน
    now = datetime.datetime.now()
    thai_year = now.year + 543
    months_th = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                 "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    return f"{now.day} {months_th[now.month-1]} {thai_year}"

@app.route('/scrape-dsd', methods=['GET'])
def scrape_dsd():
    today_str = get_thai_date()
    news_cache = f"ข้อมูล ณ วันที่ {today_str}: สนพ.มหาสารคาม เปิดรับสมัครฝึกอบรมยกระดับฝีมือแรงงานหลายสาขา (ฟรี)"
    
    try:
        # เจาะจง URL หน้าข่าวประชาสัมพันธ์ สนพ.มหาสารคาม
        url = "https://www.dsd.go.th/mahasarakham"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=8, verify=False)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.content.decode('utf-8', 'ignore'), 'html.parser')
            
            # ค้นหาข้อความข่าวประชาสัมพันธ์ / ประกาศ
            headlines = []
            for a in soup.find_all('a'):
                text = a.get_text(strip=True)
                # คัดกรองเอาเฉพาะหัวข้อที่มีความยาวน่าจะเป็นข่าว
                if len(text) > 15 and ('สนพ.' in text or 'ฝึกอบรม' in text or 'ประกาศ' in text or 'กิจกรรม' in text):
                    if text not in headlines:
                        headlines.append(text)
            
            if headlines:
                news_cache = f"ข้อมูลอัปเดต ณ วันที่ {today_str} - ข่าวล่าสุด สนพ.มค.: " + " | ".join(headlines[:4])
                
    except Exception as e:
        print("Scrape error:", e)
    
    return jsonify({
        "status": "ok", 
        "current_date": today_str,
        "news_context": news_cache
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
