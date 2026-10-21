from flask import Flask, render_template_string, jsonify, request
import requests
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "sarakham/kiosk/status"

def send_mqtt_command(state):
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, 1883, 60)
        client.publish(MQTT_TOPIC, state)
        client.disconnect()
        return True
    except Exception as e:
        print(f"MQTT Error: {e}")
        return False

NEWS_CACHE = "หลักสูตรฝึกอบรมล่าสุด สนพ.มหาสารคาม: ช่างไฟฟ้าภายในอาคาร และช่างเชื่อม"

@app.route('/scrape-dsd', methods=['GET'])
def scrape_dsd():
    global NEWS_CACHE
    headlines = []
    
    try:
        url = "https://www.dsd.go.th/mahasarakham"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            web_headlines = [a.get_text(strip=True) for a in soup.find_all('a') if 'ฝึกอบรม' in a.get_text() or 'ประกาศ' in a.get_text()]
            headlines.extend(web_headlines[:3])
    except Exception as e:
        print("Web Scrape error:", e)

    try:
        fb_news = "ติดตามภาพกิจกรรมและข่าวสารอบรมผ่าน Facebook สนพ.มหาสารคาม"
        headlines.append(fb_news)
    except Exception as e:
        print("Facebook Scrape error:", e)

    if headlines:
        NEWS_CACHE = " | ".join(headlines)

    return jsonify({"status": "ok", "news_context": NEWS_CACHE})

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nong Pattana AI - Global Control Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 40px; }
        .container { max-width: 600px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; margin-bottom: 5px; }
        p { color: #94a3b8; margin-bottom: 25px; }
        .btn-group { display: flex; justify-content: center; gap: 12px; margin-bottom: 25px; flex-wrap: wrap; }
        button { padding: 12px 20px; font-size: 16px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; color: white; transition: 0.2s; }
        button:hover { opacity: 0.9; transform: translateY(-2px); }
        .btn-happy { background: #22c55e; }
        .btn-thinking { background: #eab308; color: #000; }
        .btn-speaking { background: #ef4444; }
        .news-box { background: #0f172a; padding: 15px; border-radius: 8px; text-align: left; margin-top: 20px; border-left: 4px solid #38bdf8; font-size: 14px; color: #cbd5e1; }
        #status-box { margin-top: 15px; padding: 12px; background: #334155; border-radius: 8px; font-weight: bold; color: #38bdf8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 น้องพัฒนาสารคาม AI</h1>
        <p>ระบบควบคุมอัจฉริยะ (Global Cloud & MQTT)</p>
        
        <div class="btn-group">
            <button class="btn-happy" onclick="setEmotionAndSpeak('HAPPY', 'สวัสดีค่ะ น้องพัฒนายินดีต้อนรับค่ะ')">😊 ยิ้มแย้ม</button>
            <button class="btn-thinking" onclick="setEmotionAndSpeak('THINKING', 'กำลังตรวจสอบข้อมูลข่าวสารให้ค่ะ')">🤔 กำลังคิด</button>
            <button class="btn-speaking" onclick="setEmotionAndSpeak('SPEAKING', 'สนใจหลักสูตรฝึกอบรม สอบถามได้นะคะ')">🗣️ กำลังพูด</button>
        </div>

        <div id="status-box">สถานะระบบ: พร้อมใช้งานทั่วโลก</div>
        
        <div class="news-box">
            <b>📰 ข้อมูลข่าวสารล่าสุด (เว็บ สนพ. + Facebook):</b><br>
            <span id="news-content">กำลังโหลดข้อมูล...</span>
        </div>
    </div>

    <script>
        function speakThai(text) {
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            let utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'th-TH';
            utterance.pitch = 1.2;
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
        }

        function setEmotionAndSpeak(emotion, text) {
            speakThai(text);
            fetch('/api/set-state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: emotion })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('status-box').innerText = "ส่งคำสั่งสำเร็จ: " + data.state;
            });
        }

        function loadNews() {
            fetch('/scrape-dsd')
            .then(res => res.json())
            .then(data => {
                document.getElementById('news-content').innerText = data.news_context;
            });
        }
        loadNews();
        setInterval(loadNews, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/set-state', methods=['POST'])
def set_state():
    data = request.json
    state = data.get("state", "HAPPY")
    send_mqtt_command(state)
    return jsonify({"status": "success", "state": state})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
