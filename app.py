from flask import Flask, request, render_template_string, session, redirect, url_for
import time
import random
import requests
import threading
from urllib.parse import urlparse
import os
import logging
import json
import uuid
from datetime import datetime
from threading import Event
import sqlite3

app = Flask(__name__)
app.secret_key = "3a4f82d59c6e4f0a8e912a5d1f7c3b2e6f9a8d4c5b7e1d1a4c"

# Global variable to track running tasks
active_tasks = {}
running_tasks = {}

# Database setup
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks
        (id TEXT PRIMARY KEY,
         thread_id TEXT,
         prefix TEXT,
         interval INTEGER,
         messages TEXT,
         cookies TEXT,
         status TEXT,
         messages_sent INTEGER,
         start_time TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

init_db()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Facebook Message Automation Using Cookies</title>
  <style>
        body, html {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            color: #333;
        }

        header {
            position: relative;
            width: 100%;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }

        .header-wrapper {
            display: flex;
            width: 100%;
            height: 100%;
            position: relative;
        }

        .header-left {
            flex: 1;
            background: #7d7dff;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Arial Black', sans-serif;
            font-style: italic;
            clip-path: polygon(0 0, 100% 0, 90% 100%, 0% 100%);
        }

        .header-right {
            flex: 1;
            background: white;
            color: black;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Arial Black', sans-serif;
            font-style: italic;
            clip-path: polygon(10% 0, 100% 0, 100% 100%, 0 100%);
        }

        .header-left h1, .header-right h1 {
            font-size: 0.9rem;
            font-weight: bold;
            letter-spacing: 0.1px;
            text-transform: uppercase;
        }

        .container {
            background: white;
            border: 1px solid #ddd;
            border-radius: 10px;
            width: auto;
            max-width: 600px;
            margin: 30px auto;
            padding: 20px;
            text-align: center;
            margin-bottom: 15px;
            font-weight: bold;
            box-sizing: border-box;
        }
        
        .form-title {
            font-size: 1.2rem;
            color: #28a745;
            margin-top: 20px;
            margin-bottom: 10px;
            font-style: italic;
            border-left: 4px solid #28a745;
            padding-left: 10px;
        }

        .switchover-title {
            font-size: 1.0rem;
            color: #28a745;
            margin-top: 20px;
            margin-bottom: 10px;
            font-style: italic;
            border-left: 4px solid #28a745;
            padding-left: 10px;
        }

        input, select, textarea {
            color: green;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 50px;
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            display: inline-block;
            width: 100%;
            height: 50px;
            outline: none;
            border: 0.1px solid #ccc;
            font-size: 0.9rem;
            box-sizing: border-box;
            margin-top: 10px;
            margin-bottom: 10px;
        }

        textarea {
            height: 140px;
            resize: none;
        }

        button {
            padding: 17px 40px;
            border-radius: 50px;
            cursor: pointer;
            border: 0;
            background-color: white;
            box-shadow: rgb(0 0 0 / 50%) 0 0 8px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            font-size: 15px;
            transition: all 0.5s ease;
        }
        button:hover {
            letter-spacing: 4px;
            background-color: rgb(24, 191, 220);
            color: hsl(0, 0%, 100%);
            box-shadow: rgb(24, 191, 220) 0px 7px 29px 0px;
        }

        button:active {
            letter-spacing: 3px;
            background-color: hsl(24, 191, 220);
            color: hsl(0, 0%, 100%);
            box-shadow: rgb(24, 191, 220) 0px 0px 0px 0px;
            transform: translateY(10px);
            transition: 100ms;
        }

        .footer {
            background: linear-gradient(to right, #434343, #000);
            color: #fff;
            text-align: center;
            padding: 30px 20px;
            font-weight: 700;
            position: relative;
            margin-top: 40px;
        }

        .footer p {
            margin: 10px 0;
            font-size: 16px;
        }

        .footer::before {
            content: '';
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 5px;
            background-color: #25d366;
            border-radius: 50px;
        }

        .facebook-link, .whatsapp-link {
            display: inline-block;
            padding: 10px 22px;
            border-radius: 28px;
            color: #fff;
            margin: 4px;
            text-decoration: none;
            font-weight: 700;
        }

        .facebook-link {
            background-color: #4267b2;
        }

        .whatsapp-link {
            background-color: #25d366;
        }

        .status-container {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            background-color: #f0f0f0;
            display: none;
        }

        .status-item {
            margin: 5px 0;
            font-weight: bold;
        }

        .status-running {
            color: #007bff;
        }

        .status-completed {
            color: #28a745;
        }

        .status-stopped {
            color: #dc3545;
        }

        .status-error {
            color: #ffc107;
        }

        .cookie-info {
            background: rgba(255, 255, 0, 0.1);
            border: 1px solid yellow;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-size: 0.8em;
        }
  </style>
</head>
<body>
  <header>
    <div class="header-wrapper">
      <div class="header-left">
        <h1>Send From Web</h1>
      </div>
      <div class="header-right">
        <h1> Convo / Chat Setup</h1>
      </div>
    </div>
  </header>

  <div class="container">
    <h1 class="form-title">Target Facebook Chat</h1>
    
    <div class="cookie-info">
        <strong>📝 DIRECT COOKIE LOGIN:</strong><br>
        Paste complete Facebook cookies. No token generation - direct cookie authentication.
    </div>

    <form id="messageForm" method="POST" action="/start_task">
      <div class="form-group">
        <input type="text" id="chat_url" name="chat_url" placeholder="Enter Facebook Chat URL (e.g., https://www.facebook.com/messages/t/123456789)" required>
      </div>
      
      <div class="form-group">
        <h1 class="switchover-title">Facebook Cookies</h1>
        <textarea id="cookies" name="cookies" placeholder="Paste complete Facebook cookies&#10;Example:&#10;ps_n=1; c_user=100004620784238; xs=36%3A60KGjx0BrwaLZQ%3A2%3A...&#10;fr=0GDPpiknPpRrCKYa7.AWfX89NY-oSYuAexguj1g2u-c7k0..." required></textarea>
      </div>
      
      <h1 class="switchover-title">Messages to Send</h1>
      <div class="form-group">
        <textarea id="messages" name="messages" placeholder="Enter messages to send (one per line)" required></textarea>
      </div>
      
      <h1 class="switchover-title">Delay Between Messages</h1>
      <div class="form-group">
        <input type="number" id="delay" name="delay" value="60" min="5" placeholder="Delay in seconds between messages" required>
      </div>

      <button type="submit" id="submitBtn">Start Loader</button>
      <button type="button" id="stopBtn" style="display: none;">Stop Sending</button>
    </form>

    <div id="statusContainer" class="status-container">
      <h2>Task Status</h2>
      <div class="status-item">Status: <span id="statusText">-</span></div>
      <div class="status-item">Messages Sent: <span id="messagesSent">0</span></div>
      <div class="status-item">Last Message: <span id="lastMessage">-</span></div>
    </div>
  </div>


  <footer class="footer">
    <p>©2025 Send From Web Using Cookies</p>
    <p>◉ All Rights Reserved ◉</p>
    <p>Owner: Bhoja X Alliance ✷</p>
    <div style="margin-top:15px">
      <a href="https://chat.whatsapp.com/GQKqTiTovC4IYDx8bEs9EQ" target="_blank" class="whatsapp-link">
        WhatsApp
      </a>
      <a href="https://facebook.com" target="_blank" class="facebook-link">
        Facebook
      </a>
    </div>
  </footer>

  <script>
    document.getElementById('messageForm').addEventListener('submit', function(e) {
      e.preventDefault();
      
      const submitBtn = document.getElementById('submitBtn');
      const stopBtn = document.getElementById('stopBtn');
      const statusContainer = document.getElementById('statusContainer');
      
      submitBtn.disabled = true;
      stopBtn.style.display = 'inline-block';
      statusContainer.style.display = 'block';
      
      const formData = new FormData(this);
      
      fetch('/start_task', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          const taskId = data.task_id;
          updateStatus(taskId);
        } else {
          alert(data.message);
          submitBtn.disabled = false;
          stopBtn.style.display = 'none';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        submitBtn.disabled = false;
        stopBtn.style.display = 'none';
      });
    });
    
    document.getElementById('stopBtn').addEventListener('click', function() {
      const taskId = this.getAttribute('data-task-id');
      if (taskId) {
        fetch('/stop_task/' + taskId, {
          method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
          if (data.status === 'success') {
            document.getElementById('statusText').textContent = 'Stopped';
            document.getElementById('statusText').className = 'status-stopped';
            document.getElementById('submitBtn').disabled = false;
            this.style.display = 'none';
          }
        });
      }
    });
    
    function updateStatus(taskId) {
      const stopBtn = document.getElementById('stopBtn');
      stopBtn.setAttribute('data-task-id', taskId);
      
      const statusInterval = setInterval(() => {
        fetch('/task_status/' + taskId)
        .then(response => response.json())
        .then(data => {
          if (data.status === 'error' && data.message === 'Task not found') {
            clearInterval(statusInterval);
            return;
          }
          
          document.getElementById('statusText').textContent = data.status;
          document.getElementById('statusText').className = 'status-' + data.status;
          document.getElementById('messagesSent').textContent = data.messages_sent || '0';
          document.getElementById('lastMessage').textContent = data.last_message || '-';
          
          if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
            clearInterval(statusInterval);
            document.getElementById('submitBtn').disabled = false;
            stopBtn.style.display = 'none';
          }
        });
      }, 1000);
    }
  </script>
</body>
</html>
"""

# ------------------ DIRECT COOKIE SENDER ------------------
def send_messages_with_cookies(task_id, stop_event, pause_event):
    """
    Direct cookies use karke messages send karega - NO TOKEN GENERATION
    """
    while not stop_event.is_set():
        if pause_event.is_set():
            time.sleep(1)
            continue
        
        try:
            # Get task from database
            conn = sqlite3.connect('tasks.db')
            c = conn.cursor()
            c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task_data = c.fetchone()
            
            if not task_data:
                conn.close()
                break

            # Parse task data
            task = {
                'id': task_data[0],
                'thread_id': task_data[1],
                'prefix': task_data[2],
                'interval': task_data[3],
                'messages': json.loads(task_data[4]),
                'cookies': json.loads(task_data[5]),
                'messages_sent': task_data[7]
            }

            cookie_strings = task['cookies']
            messages = task['messages']

            for message_content in messages:
                if stop_event.is_set():
                    break
                
                if pause_event.is_set():
                    break
                
                for cookie_string in cookie_strings:
                    if stop_event.is_set():
                        break
                    
                    # Direct cookies use karega
                    cookies = {}
                    for part in cookie_string.split(';'):
                        part = part.strip()
                        if '=' in part:
                            key, value = part.split('=', 1)
                            cookies[key.strip()] = value.strip()
                    
                    # Facebook API call with direct cookies
                    api_url = f'https://graph.facebook.com/v19.0/t_{task["thread_id"]}/'
                    message = f"{task['prefix']} {message_content}"
                    
                    try:
                        # Method 1: Direct API call with parameters
                        parameters = {
                            'message': message,
                            'access_token': f"{cookies.get('c_user', '')}|{cookies.get('xs', '')}"
                        }
                        
                        response = requests.post(
                            api_url, 
                            data=parameters, 
                            cookies=cookies,  # Direct cookies bhi send karega
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            # Update message count in database
                            task['messages_sent'] += 1
                            c.execute("UPDATE tasks SET messages_sent = ? WHERE id = ?", 
                                     (task['messages_sent'], task_id))
                            conn.commit()
                            
                            # Update active tasks
                            if task_id in active_tasks:
                                active_tasks[task_id]['messages_sent'] = task['messages_sent']
                                active_tasks[task_id]['last_message'] = message
                            
                            logging.info(f"✅ Sent: {message[:30]} for Task ID: {task_id}")
                        else:
                            # Try alternative method
                            logging.warning(f"❌ Method 1 Fail [{response.status_code}]: {response.text[:100]}")
                            
                            # Method 2: Different approach
                            try:
                                alt_response = requests.post(
                                    api_url,
                                    data={'message': message},
                                    cookies=cookies,
                                    timeout=10
                                )
                                if alt_response.status_code == 200:
                                    task['messages_sent'] += 1
                                    c.execute("UPDATE tasks SET messages_sent = ? WHERE id = ?", 
                                             (task['messages_sent'], task_id))
                                    conn.commit()
                                    
                                    if task_id in active_tasks:
                                        active_tasks[task_id]['messages_sent'] = task['messages_sent']
                                        active_tasks[task_id]['last_message'] = message
                                    
                                    logging.info(f"✅ Sent (Alt): {message[:30]} for Task ID: {task_id}")
                                else:
                                    logging.warning(f"❌ Method 2 Fail [{alt_response.status_code}]")
                            except Exception as alt_e:
                                logging.error(f"⚠️ Alt method error: {alt_e}")
                                
                    except requests.exceptions.RequestException as e:
                        logging.error(f"⚠️ Network error for Task ID {task_id}: {e}")
                    
                    if pause_event.is_set():
                        break
                
                if pause_event.is_set():
                    break
                
                time.sleep(task['interval'])
            
            conn.close()
            
        except Exception as e:
            logging.error(f"⚠️ Error in message loop for Task ID {task_id}: {e}")
            try:
                conn.close()
            except:
                pass
            time.sleep(10)

def send_messages_task(task_id, chat_url, cookies, messages, delay):
    """Original function with cookies integration"""
    try:
        # Extract thread ID from URL
        parsed_url = urlparse(chat_url)
        path_parts = parsed_url.path.split('/')
        thread_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
        
        # Store in database
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO tasks (id, thread_id, prefix, interval, messages, cookies, status, messages_sent, start_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, thread_id, "Auto", delay, json.dumps(messages), json.dumps(cookies), 'running', 0, datetime.now()))
        conn.commit()
        conn.close()
        
        # Start the advanced cookie sender
        stop_event = Event()
        pause_event = Event()
        thread = threading.Thread(target=send_messages_with_cookies, args=(task_id, stop_event, pause_event))
        thread.daemon = True
        thread.start()
        
        running_tasks[task_id] = {
            'thread': thread,
            'stop_event': stop_event,
            'pause_event': pause_event
        }
        
    except Exception as e:
        if task_id in active_tasks:
            active_tasks[task_id]['status'] = 'error'
            active_tasks[task_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/start_task', methods=['POST'])
def start_task():
    # Get form data
    chat_url = request.form.get('chat_url')
    cookies = request.form.get('cookies')
    messages = request.form.get('messages')
    delay = int(request.form.get('delay', 60))
    
    # Validate inputs
    if not all([chat_url, cookies, messages]):
        return {'status': 'error', 'message': 'All fields are required'}, 400
    
    # Parse cookies into list
    cookie_list = [cookie.strip() for cookie in cookies.strip().splitlines() if cookie.strip()]
    
    # Parse messages into list
    message_list = [msg.strip() for msg in messages.split('\n') if msg.strip()]
    
    # Generate a unique task ID
    task_id = str(int(time.time())) + str(random.randint(1000, 9999))
    
    # Store the task information
    active_tasks[task_id] = {
        'status': 'running',
        'start_time': time.time(),
        'messages_sent': 0,
        'last_message': None
    }
    
    # Start the task in a new thread
    thread = threading.Thread(
        target=send_messages_task,
        args=(task_id, chat_url, cookie_list, message_list, delay)
    )
    thread.daemon = True
    thread.start()
    
    return {
        'status': 'success',
        'task_id': task_id,
        'message': 'Message sending process started'
    }

@app.route('/stop_task/<task_id>', methods=['POST'])
def stop_task(task_id):
    if task_id in active_tasks:
        active_tasks[task_id]['status'] = 'stopped'
        
        # Also stop in running_tasks
        if task_id in running_tasks:
            running_tasks[task_id]['stop_event'].set()
        
        # Update database
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = 'stopped' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        
        return {'status': 'success', 'message': 'Task stopped'}
    return {'status': 'error', 'message': 'Task not found'}, 404

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    if task_id in active_tasks:
        return active_tasks[task_id]
    return {'status': 'error', 'message': 'Task not found'}, 404

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == "AXSHU143":
            session['admin'] = True
            return redirect('/admin/panel')
    return '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Login</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body {
          background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 50%, #16213e 100%);
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .login-container {
          background: rgba(10, 10, 10, 0.9);
          border: 1px solid #00ffff;
          box-shadow: 0 0 30px rgba(0, 255, 255, 0.6);
          border-radius: 15px;
          padding: 30px;
          width: 100%;
          max-width: 350px;
        }
        .form-control {
          background-color: #1a1a1a;
          border: 1px solid #00ffff;
          color: #00ffff;
        }
      </style>
    </head>
    <body>
      <div class="login-container">
        <h2 class="text-center text-info mb-4">ADMIN PANEL</h2>
        <form method="POST">
          <div class="mb-3">
            <label class="form-label text-info">Password</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <button type="submit" class="btn btn-info w-100">Login</button>
        </form>
      </div>
    </body>
    </html>
    '''

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect('/admin/login')
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks")
    tasks_data = c.fetchall()
    conn.close()
    
    tasks = []
    for task in tasks_data:
        tasks.append({
            'id': task[0],
            'thread_id': task[1],
            'prefix': task[2],
            'interval': task[3],
            'messages': task[4],
            'cookies': task[5],
            'status': task[6],
            'messages_sent': task[7],
            'start_time': task[8]
        })
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Admin Panel</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
      <div class="container mt-4">
        <h2>Admin Panel - Active Tasks</h2>
        <table class="table table-striped">
          <thead>
            <tr>
              <th>Task ID</th>
              <th>Thread ID</th>
              <th>Status</th>
              <th>Messages Sent</th>
              <th>Start Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {"".join([f'''
            <tr>
              <td>{task['id']}</td>
              <td>{task['thread_id']}</td>
              <td>{task['status']}</td>
              <td>{task['messages_sent']}</td>
              <td>{task['start_time']}</td>
              <td>
                <form method="POST" action="/stop_task/{task['id']}" class="d-inline">
                  <button type="submit" class="btn btn-danger btn-sm">Stop</button>
                </form>
              </td>
            </tr>
            ''' for task in tasks])}
          </tbody>
        </table>
        <a href="/" class="btn btn-primary">Back to Main</a>
      </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
