from flask import Flask, render_template_string, jsonify, request
import requests
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt
from datetime import datetime

app = Flask(__name__)

# ตั้งค่า API Key ของ OpenRouter 
OPENROUTER_API_KEY = "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"
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

# ตัวแปรเก็บข่าวสาร (Admin สามารถอัปเดตได้สดๆ)
NEWS_CACHE = "หลักสูตรฝึกอบรมล่าสุด สนพ.มหาสารคาม: ช่างไฟฟ้าภายในอาคาร และช่างเชื่อม (ประจำปี พ.ศ. 2569)"

# API สำหรับให้แอดมินอัปเดตข่าวสารด่วน
@app.route('/api/update-news', methods=['POST'])
def update_news():
    global NEWS_CACHE
    data = request.json
    new_news = data.get("news", "").strip()
    if new_news:
        NEWS_CACHE = new_news
        return jsonify({"status": "success", "news_context": NEWS_CACHE})
    return jsonify({"status": "error", "message": "ข้อมูลข่าวสารว่างเปล่า"}), 400

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

    # ถ้าระบบเว็บดึงได้ ให้นำมารวมกับ Cache หลัก หรือปล่อยให้แอดมินคุมเองได้เต็มที่
    return jsonify({"status": "ok", "news_context": NEWS_CACHE})

# ฟังก์ชันแปลงวันที่ ค.ศ. เป็น พ.ศ. แบบอัตโนมัติ
def get_thai_current_date():
    now = datetime.now()
    days = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
    months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
    
    day_name = days[now.weekday()]
    day_num = now.day
    month_name = months[now.month - 1]
    thai_year = now.year + 543
    
    return f"{day_name}ที่ {day_num} {month_name} พ.ศ. {thai_year}"

# ฟังก์ชันประมวลผลคำถามผ่าน OpenRouter AI (Gemini 2.5 Flash)
@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    data = request.json
    user_prompt = data.get("prompt", "")
    
    # ส่งสถานะ THINKING ไปยังบอร์ด ESP32-S3
    send_mqtt_command("THINKING")

    current_date_str = get_thai_current_date()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    payload = {
        "model": "google/gemini-2.5-flash",
        "max_tokens": 250,
        "messages": [
            {
                "role": "system",
                "content": f"คุณคือ 'น้องพัฒนา' ผู้ช่วยอัจฉริยะหญิงประจำ 'สำนักงานพัฒนาฝีมือแรงงานมหาสารคาม' (สนพ.มค.) วันนี้คือ '{current_date_str}' (ให้ยึดถือนี่เป็นวันเวลาปัจจุบันเสมอ) ข้อมูลข่าวสารล่าสุดที่ต้องใช้ตอบ: [{NEWS_CACHE}] จงตอบคำถามด้วยน้ำเสียงสุภาพ เป็นกันเอง และอ้างอิงข้อมูลข่าวสารล่าสุดนี้เสมอ"
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=15)
        res_data = response.json()
        ai_reply = res_data["choices"][0]["message"]["content"]
        
        # ส่งสถานะ SPEAKING ไปยังบอร์ด ESP32-S3 เมื่อได้คำตอบ
        send_mqtt_command("SPEAKING")
        return jsonify({"status": "success", "reply": ai_reply})
    except Exception as e:
        send_mqtt_command("HAPPY")
        return jsonify({"status": "error", "reply": "ระบบ AI ขัดข้องชั่วคราวค่ะ"}), 500

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nong Pattana AI - Admin Control Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 20px; }
        .container { max-width: 650px; margin: 0 auto; background: #1e293b; padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        h1 { color: #38bdf8; margin-bottom: 5px; }
        p { color: #94a3b8; margin-bottom: 20px; }
        .btn-group { display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        button { padding: 10px 18px; font-size: 15px; font-weight: bold; border: none; border-radius: 8px; cursor: pointer; color: white; transition: 0.2s; }
        button:hover { opacity: 0.9; transform: translateY(-2px); }
        .btn-happy { background: #22c55e; }
        .btn-thinking { background: #eab308; color: #000; }
        .btn-speaking { background: #ef4444; }
        .section { margin-top: 20px; text-align: left; background: #0f172a; padding: 15px; border-radius: 8px; }
        input[type="text"] { width: 70%; padding: 10px; font-size: 14px; background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; }
        .btn-action { background: #38bdf8; color: #0f172a; padding: 10px 15px; }
        .response-box { background: #0f172a; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #38bdf8; color: #cbd5e1; min-height: 40px; text-align: left; }
        #status-box { margin-top: 15px; padding: 10px; background: #334155; border-radius: 8px; font-weight: bold; color: #38bdf8; font-size: 14px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 น้องพัฒนาสารคาม AI</h1>
        <p>แผงควบคุมระบบ Kiosk และจัดการข่าวสารแอดมิน</p>
        
        <div class="btn-group">
            <button class="btn-happy" onclick="setEmotionAndSpeak('HAPPY', 'สวัสดีค่ะ น้องพัฒนายินดีต้อนรับค่ะ')">😊 ยิ้มแย้ม</button>
            <button class="btn-thinking" onclick="setEmotionAndSpeak('THINKING', 'กำลังตรวจสอบข้อมูลข่าวสารให้ค่ะ')">🤔 กำลังคิด</button>
            <button class="btn-speaking" onclick="setEmotionAndSpeak('SPEAKING', 'สนใจหลักสูตรฝึกอบรม สอบถามได้นะคะ')">🗣️ กำลังพูด</button>
        </div>

        <!-- แผงแอดมินอัปเดตข่าวสาร (Option 2) -->
        <div class="section">
            <label><b>🛠️ แอดมินอัปเดตข่าวสาร/หลักสูตรด่วน:</b></label><br><br>
            <input type="text" id="admin-news" placeholder="ระบุหลักสูตรหรือข่าวสารใหม่..." style="width: 73%;">
            <button class="btn-action" onclick="updateAdminNews()">บันทึกข่าว</button>
        </div>

        <!-- ส่วนแชททดสอบ AI -->
        <div class="section">
            <label><b>💬 ทดสอบสนทนากับน้องพัฒนา (LLM):</b></label><br><br>
            <input type="text" id="user-prompt" placeholder="สอบถามหลักสูตร / ข้อมูลฝึกอบรม..." style="width: 73%;">
            <button class="btn-action" onclick="askAI()">สอบถาม</button>
        </div>

        <div class="response-box" id="ai-response">
            <b>คำตอบจากน้องพัฒนา:</b><br>
            <span>รอรับคำสั่งหรือคำถาม...</span>
        </div>

        <div id="status-box">สถานะระบบ: พร้อมใช้งาน</div>
        
        <div class="response-box" style="border-left-color: #22c55e;">
            <b>📰 ข้อมูลข่าวสารปัจจุบันที่ AI กำลังใช้งานอยู่:</b><br>
            <span id="news-content" style="color: #38bdf8;">กำลังโหลดข้อมูล...</span>
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

        function updateAdminNews() {
            let newsText = document.getElementById("admin-news").value;
            if(!newsText) return;
            fetch('/api/update-news', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ news: newsText })
            })
            .then(res => res.json())
            .then(data => {
                alert("อัปเดตข่าวสารสำเร็จ!");
                document.getElementById('news-content').innerText = data.news_context;
                document.getElementById('admin-news').value = "";
            });
        }

        function askAI() {
            let promptText = document.getElementById("user-prompt").value;
            if(!promptText) return;
            document.getElementById("ai-response").innerHTML = "<b>คำตอบจากน้องพัฒนา:</b><br>⏳ กำลังประมวลผลข้อมูลและติดต่อ AI...";
            document.getElementById('status-box').innerText = "สถานะ: AI กำลังคิด (THINKING)";

            fetch('/api/ask-ai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: promptText })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById("ai-response").innerHTML = "<b>คำตอบจากน้องพัฒนา:</b><br>✨ " + data.reply;
                document.getElementById('status-box').innerText = "สถานะ: AI ตอบกลับแล้ว (SPEAKING)";
                speakThai(data.reply);
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
