from flask import Flask, Response, request, render_template_string, jsonify
import subprocess
import requests
import re
from urllib.parse import quote, unquote

app = Flask(__name__)

def parse_m3u_content(content):
    channels = []
    lines = content.split('\n')
    current_name = None
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            name_match = re.search(r',([^,]+)$', line)
            if name_match:
                current_name = name_match.group(1).strip()
            else:
                current_name = "قناة بدون اسم"
        elif line.startswith('http://') or line.startswith('https://'):
            if current_name:
                channels.append({"name": current_name, "url": line})
                current_name = None
            else:
                channels.append({"name": line.split('/')[-1], "url": line})
    return channels

HTML_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>📺 لوحة تحكم IPTV</title>
    <style>
        body { background-color: #0c0f12; color: #ffffff; font-family: Arial, sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 850px; background: #161b22; padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #30363d; }
        h1 { text-align: center; color: #58a6ff; font-size: 24px; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; color: #c9d1d9; }
        select, input[type="text"], input[type="range"], input[type="file"] { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #fff; box-sizing: border-box; }
        .slider-val { float: left; color: #58a6ff; font-weight: bold; }
        button { width: 100%; padding: 12px; background: #238636; border: none; border-radius: 6px; color: white; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; transition: 0.2s; }
        button:hover { background: #2ea043; }
        .channels-container { display: none; background: #21262d; padding: 15px; border-radius: 6px; margin-top: 15px; border: 1px solid #30363d; }
        .channels-list { max-height: 300px; overflow-y: auto; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; }
        .channel-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #21262d; transition: 0.2s; font-size: 14px; text-align: right; }
        .channel-item:hover { background: #161b22; color: #58a6ff; }
        .channel-item.selected { background: #1f6feb; color: white; font-weight: bold; }
        .m3u-methods { display: flex; gap: 10px; margin-bottom: 10px; }
        .method-btn { flex: 1; background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 10px; border-radius: 6px; cursor: pointer; text-align: center; font-size: 14px; font-weight: bold; }
        .method-btn.active { background: #388bfd; color: white; border-color: #388bfd; }
        .video-box { margin-top: 25px; text-align: center; background: #000; border-radius: 8px; overflow: hidden; border: 2px solid #58a6ff; display: none; }
        video { width: 100%; max-width: 854px; height: 480px; display: block; }
        .loading { color: #f1e05a; display: none; font-weight: bold; margin-top: 5px; }
        .status { color: #3fb950; font-size: 12px; margin-top: 5px; display: none; }
    </style>
</head>
<body>

<div class="container">
    <h1>📺 لوحة تحكم IPTV</h1>

    <div class="form-group">
        <label>اختر مصدر البث:</label>
        <select id="sourceType" onchange="handleSourceChange()">
            <option value="single">رابط مباشر (قناة واحدة)</option>
            <option value="m3u">ملف أو رابط M3U (قائمة قنوات)</option>
        </select>
    </div>

    <div class="form-group" id="singleArea">
        <label>أدخل رابط القناة المباشر:</label>
        <input type="text" id="singleUrl" value="http://ugeen.live:8080/Ugeen_VIPmS3NcQ/qQPQWj/4540">
    </div>

    <div id="m3uSection" style="display:none; border: 1px dashed #30363d; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
        <div class="m3u-methods">
            <div class="method-btn active" id="btnLink" onclick="switchM3uMethod('link')">🔗 رابط M3U</div>
            <div class="method-btn" id="btnFile" onclick="switchM3uMethod('file')">📁 رفع ملف M3U</div>
        </div>

        <div class="form-group" id="m3uUrlArea">
            <label>أدخل رابط ملف M3U:</label>
            <input type="text" id="m3uUrl" value="">
        </div>

        <div class="form-group" id="m3uFileArea" style="display:none;">
            <label>اختر ملف M3U من جهازك:</label>
            <input type="file" id="m3uFile" accept=".m3u,.m3u8">
        </div>

        <button type="button" style="background:#1f6feb;" onclick="processM3U()">🔄 تحليل واستخراج القنوات</button>
        <div class="loading" id="loadingText">جاري التحليل...</div>
    </div>

    <div class="channels-container" id="channelsArea">
        <label style="color: #58a6ff;">🔍 اختر قناة من القائمة:</label>
        <input type="text" id="channelSearch" placeholder="ابحث عن قناة..." oninput="filterChannels()" style="margin-bottom:10px; margin-top:5px;">
        <div class="channels-list" id="channelsList"></div>
        <div class="status" id="channelStatus"></div>
    </div>

    <hr style="border:0; border-top:1px solid #30363d; margin:20px 0;">

    <div class="form-group">
        <label>معدل بيانات الفيديو: <span class="slider-val" id="v_val">650 Kbps</span></label>
        <input type="range" id="videoKbps" min="200" max="1500" value="650" step="50" oninput="document.getElementById('v_val').innerText = this.value + ' Kbps'">
    </div>

    <div class="form-group">
        <label>معدل بيانات الصوت: <span class="slider-val" id="a_val">96 Kbps</span></label>
        <input type="range" id="audioKbps" min="32" max="128" value="96" step="16" oninput="document.getElementById('a_val').innerText = this.value + ' Kbps'">
    </div>

    <button onclick="applySettings()">🚀 تشغيل البث المباشر</button>

    <div class="video-box" id="videoBox">
        <video id="player" controls autoplay name="media"></video>
    </div>
</div>

<script>
    var currentM3uMethod = 'link';
    var allChannels = [];
    var selectedChannelUrl = "";

    function handleSourceChange() {
        var type = document.getElementById("sourceType").value;
        document.getElementById("singleArea").style.display = (type === "single") ? "block" : "none";
        document.getElementById("m3uSection").style.display = (type === "m3u") ? "block" : "none";
        if (type === "single") {
            document.getElementById("channelsArea").style.display = "none";
        }
    }

    function switchM3uMethod(method) {
        currentM3uMethod = method;
        document.getElementById("btnLink").classList.toggle("active", method === 'link');
        document.getElementById("btnFile").classList.toggle("active", method === 'file');
        document.getElementById("m3uUrlArea").style.display = (method === 'link') ? "block" : "none";
        document.getElementById("m3uFileArea").style.display = (method === 'file') ? "block" : "none";
    }

    function processM3U() {
        var loading = document.getElementById("loadingText");
        loading.style.display = "block";

        if (currentM3uMethod === 'link') {
            var m3uUrl = document.getElementById("m3uUrl").value;
            if (!m3uUrl) { loading.style.display = "none"; alert("أدخل رابط M3U أولاً!"); return; }
            fetch('/api/parse_m3u_url?url=' + encodeURIComponent(m3uUrl))
                .then(function(res) { return res.json(); })
                .then(function(data) { populateChannels(data); loading.style.display = "none"; })
                .catch(function() { loading.style.display = "none"; alert("خطأ في جلب الرابط."); });
        } else {
            var fileInput = document.getElementById("m3uFile");
            if (fileInput.files.length === 0) { loading.style.display = "none"; alert("اختر ملف M3U أولاً!"); return; }
            var formData = new FormData();
            formData.append("file", fileInput.files[0]);
            fetch('/api/parse_m3u_file', { method: 'POST', body: formData })
                .then(function(res) { return res.json(); })
                .then(function(data) { populateChannels(data); loading.style.display = "none"; })
                .catch(function() { loading.style.display = "none"; alert("خطأ في قراءة الملف."); });
        }
    }

    function populateChannels(data) {
        allChannels = data || [];
        if (allChannels.length === 0) {
            alert("لم يتم العثور على قنوات.");
            return;
        }
        document.getElementById("channelsArea").style.display = "block";
        document.getElementById("channelStatus").style.display = "block";
        document.getElementById("channelStatus").innerText = "تم العثور على " + allChannels.length + " قناة";
        document.getElementById("channelSearch").value = "";
        filterChannels();
    }

    function filterChannels() {
        var query = document.getElementById("channelSearch").value.toLowerCase();
        var container = document.getElementById("channelsList");
        container.innerHTML = "";
        var count = 0;
        for (var i = 0; i < allChannels.length; i++) {
            if (allChannels[i].name.toLowerCase().indexOf(query) !== -1) {
                var item = document.createElement("div");
                item.className = "channel-item";
                if (allChannels[i].url === selectedChannelUrl) item.className += " selected";
                item.innerText = allChannels[i].name;
                item.dataset.url = allChannels[i].url;
                item.onclick = function() {
                    var items = container.getElementsByClassName("channel-item");
                    for (var j = 0; j < items.length; j++) items[j].classList.remove("selected");
                    this.classList.add("selected");
                    selectedChannelUrl = this.dataset.url;
                };
                container.appendChild(item);
                count++;
                if (count >= 200) break;
            }
        }
    }

    function applySettings() {
        var type = document.getElementById("sourceType").value;
        var url = "";
        if (type === "single") {
            url = document.getElementById("singleUrl").value;
        } else {
            url = selectedChannelUrl;
            if (!url) { alert("اختر قناة من القائمة أولاً!"); return; }
        }
        var v_kbps = document.getElementById("videoKbps").value;
        var a_kbps = document.getElementById("audioKbps").value;
        var streamUrl = "/api/video_feed?url=" + encodeURIComponent(url) + "&v_kbps=" + v_kbps + "&a_kbps=" + a_kbps + "&t=" + new Date().getTime();

        var videoBox = document.getElementById("videoBox");
        var player = document.getElementById("player");
        videoBox.style.display = "block";
        player.src = streamUrl;
        player.load();
        player.play();

        player.onwaiting = function() {
            if (player.buffered.length > 0) {
                var liveEdge = player.buffered.end(player.buffered.length - 1);
                player.currentTime = liveEdge - 0.5;
            }
        };
    }
</script>

</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_INTERFACE)

@app.route('/api/parse_m3u_url')
def parse_m3u_url_endpoint():
    m3u_url = request.args.get('url', '')
    if not m3u_url:
        return jsonify([])
    try:
        response = requests.get(m3u_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        channels = parse_m3u_content(response.text)
        print(f"[M3U URL] {m3u_url} -> {len(channels)} channels")
    except Exception as e:
        print(f"[M3U URL ERROR] {e}")
        channels = []
    return jsonify(channels)

@app.route('/api/parse_m3u_file', methods=['POST'])
def parse_m3u_file_endpoint():
    if 'file' not in request.files:
        return jsonify([])
    file = request.files['file']
    if file.filename == '':
        return jsonify([])
    try:
        content = file.read().decode('utf-8', errors='ignore')
        channels = parse_m3u_content(content)
        print(f"[M3U FILE] {file.filename} -> {len(channels)} channels")
    except Exception as e:
        print(f"[M3U FILE ERROR] {e}")
        channels = []
    return jsonify(channels)

@app.route('/api/video_feed')
def video_feed():
    target_url = unquote(request.args.get('url', ''))
    v_kbps = request.args.get('v_kbps', '650')
    a_kbps = request.args.get('a_kbps', '96')

    if not target_url:
        return "Missing URL", 400

    resolution = "854x480" if int(v_kbps) >= 600 else "640x360"
    print(f"[VIDEO FEED] url={target_url} v={v_kbps}k a={a_kbps}k res={resolution}")

    ffmpeg_cmd = [
        'ffmpeg',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '10',
        '-fflags', '+genpts+discardcorrupt',
        '-flags', '+low_delay',
        '-i', target_url,
        '-c:v', 'libx264',
        '-b:v', f'{v_kbps}k',
        '-maxrate', f'{int(v_kbps)+50}k',
        '-bufsize', f'{int(v_kbps)*2}k',
        '-s', resolution,
        '-preset', 'veryfast',
        '-tune', 'zerolatency',
        '-c:a', 'aac',
        '-b:a', f'{a_kbps}k',
        '-async', '1',
        '-vsync', '1',
        '-max_muxing_queue_size', '1024',
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+faststart',
        '-'
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def generate():
        import time
        empty_count = 0
        try:
            while True:
                data = process.stdout.read(1024 * 64)
                if not data:
                    empty_count += 1
                    if empty_count > 5:
                        break
                    time.sleep(0.1)
                    continue
                empty_count = 0
                yield data
        finally:
            process.kill()

    return Response(generate(), mimetype='video/mp4')

if __name__ == "__main__":
    app.run()
