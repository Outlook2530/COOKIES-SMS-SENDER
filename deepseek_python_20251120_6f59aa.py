from flask import Flask, request, session, redirect, url_for, render_template_string
import requests
from threading import Thread, Event
import time
import os
import logging
import io
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from datetime import datetime
import json
import uuid
import re

app = Flask(__name__)
app.debug = True
app.secret_key = "3a4f82d59c6e4f0a8e912a5d1f7c3b2e6f9a8d4c5b7e1d1a4c"

# Database setup with thread-safe session
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "tasks.db"
engine = create_engine(f'sqlite:///{os.path.join(BASE_DIR, DB_NAME)}?check_same_thread=False')
Base = declarative_base()

# Database Model for Tasks
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    thread_id = Column(String(50), nullable=False)
    prefix = Column(String(255))
    interval = Column(Integer)
    messages = Column(Text)
    cookies = Column(Text)
    status = Column(String(20), default='Running')
    messages_sent = Column(Integer, default=0)
    start_time = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Task(id={self.id}, status='{self.status}', thread_id='{self.thread_id}')>"

Base.metadata.create_all(engine)

# Thread-safe session
Session = scoped_session(sessionmaker(bind=engine))
running_tasks = {}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

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
            # Create new session for each iteration
            db_session = Session()
            task = db_session.query(Task).filter_by(id=task_id).first()
            
            if not task:
                db_session.close()
                break

            cookie_strings = json.loads(task.cookies)
            messages = json.loads(task.messages)

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
                    api_url = f'https://graph.facebook.com/v19.0/t_{task.thread_id}/'
                    message = f"{task.prefix} {message_content}"
                    
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
                            task.messages_sent += 1
                            db_session.commit()
                            logging.info(f"✅ Sent: {message[:30]} for Task ID: {task.id}")
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
                                    task.messages_sent += 1
                                    db_session.commit()
                                    logging.info(f"✅ Sent (Alt): {message[:30]} for Task ID: {task.id}")
                                else:
                                    logging.warning(f"❌ Method 2 Fail [{alt_response.status_code}]")
                            except Exception as alt_e:
                                logging.error(f"⚠️ Alt method error: {alt_e}")
                                
                    except requests.exceptions.RequestException as e:
                        logging.error(f"⚠️ Network error for Task ID {task.id}: {e}")
                    
                    if pause_event.is_set():
                        break
                
                if pause_event.is_set():
                    break
                
                time.sleep(task.interval)
            
            db_session.close()
            
        except Exception as e:
            logging.error(f"⚠️ Error in message loop for Task ID {task_id}: {e}")
            try:
                db_session.close()
            except:
                pass
            time.sleep(10)

# ------------------ HTML TEMPLATES ------------------
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB MESSAGE SENDER</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');

        :root {
            --neon-blue: #00ffff;
            --neon-pink: #ff00ff;
            --neon-yellow: #ffcc00;
        }

        body {
            background-color: #0d0d0d;
            color: #e0e0e0;
            font-family: 'Montserrat', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            overflow: auto;
            position: relative;
            animation: background-glow 15s infinite alternate ease-in-out;
        }

        @keyframes background-glow {
            from { box-shadow: inset 0 0 50px rgba(0, 255, 255, 0.2); }
            to { box-shadow: inset 0 0 100px rgba(255, 0, 255, 0.2); }
        }

        .container {
            width: 90%;
            max-width: 450px;
            padding: 30px;
            background-color: rgba(10, 10, 10, 0.8);
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(8px);
            border: 1px solid var(--neon-blue);
            box-shadow: 0 0 30px rgba(0, 255, 255, 0.6), 0 0 60px rgba(0, 255, 255, 0.3);
            position: relative;
            z-index: 1;
            overflow: hidden;
        }
        
        .container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                120deg,
                transparent,
                rgba(0, 255, 255, 0.2),
                transparent,
                rgba(255, 0, 255, 0.2)
            );
            animation: running-lights 4s infinite linear;
            z-index: -1;
        }

        @keyframes running-lights {
            0% { transform: translate(-100%, -100%); }
            100% { transform: translate(100%, 100%); }
        }

        h1 {
            font-family: 'Montserrat', sans-serif;
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 25px;
            color: var(--neon-blue);
            text-shadow: 0 0 10px var(--neon-blue), 0 0 20px var(--neon-blue), 0 0 30px var(--neon-blue);
        }

        .input-group {
            margin-bottom: 15px;
        }
        .input-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 0.9em;
            color: var(--neon-blue);
            text-align: left;
            text-shadow: 0 0 5px var(--neon-blue);
        }
        .input-group input[type="text"],
        .input-group input[type="number"],
        .input-group textarea {
            width: calc(100% - 24px);
            padding: 10px;
            border: 1px solid var(--neon-blue);
            background-color: #1a1a1a;
            color: var(--neon-blue);
            border-radius: 8px;
            font-size: 1em;
            outline: none;
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.4);
            transition: all 0.3s ease;
        }
        .input-group input[type="text"]:focus,
        .input-group input[type="number"]:focus,
        .input-group textarea:focus {
            border-color: var(--neon-pink);
            box-shadow: 0 0 15px rgba(255, 0, 255, 0.7);
        }
        .input-group textarea {
            resize: vertical;
        }
        .file-input {
            display: flex;
            align-items: center;
            background-color: #1a1a1a;
            border: 1px solid var(--neon-blue);
            border-radius: 8px;
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.4);
        }
        .file-input input[type="file"] {
            display: none;
        }
        .file-input .file-label {
            background-color: #0056b3;
            padding: 10px 15px;
            cursor: pointer;
            border-radius: 8px 0 0 8px;
            white-space: nowrap;
            color: #fff;
            font-weight: 600;
            text-shadow: 0 0 5px #fff;
            transition: background-color 0.3s ease;
        }
        .file-input .file-label:hover {
            background-color: #007bff;
        }
        .file-input .file-name {
            padding: 10px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--neon-blue);
        }
        .button {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 15px;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            text-shadow: 0 0 8px rgba(255, 255, 255, 0.8);
        }
        .button.blue {
            background-color: var(--neon-blue);
            color: #0a0a0a;
            box-shadow: 0 0 15px rgba(0, 255, 255, 0.7);
        }
        .button.blue:hover {
            background-color: #00e0e0;
            box-shadow: 0 0 25px rgba(0, 255, 255, 0.9), 0 0 40px rgba(0, 255, 255, 0.6);
            transform: translateY(-2px);
        }
        .button.red {
            background-color: var(--neon-pink);
            color: #0a0a0a;
            box-shadow: 0 0 15px rgba(255, 0, 255, 0.7);
        }
        .button.red:hover {
            background-color: #e000e0;
            box-shadow: 0 0 25px rgba(255, 0, 255, 0.9), 0 0 40px rgba(255, 0, 255, 0.6);
            transform: translateY(-2px);
        }
        .button.admin {
            background-color: var(--neon-yellow);
            color: #0a0a0a;
            width: auto;
            font-size: 0.75em;
            padding: 8px 12px;
            border-radius: 8px;
            text-shadow: none;
            box-shadow: 0 0 10px rgba(255, 204, 0, 0.7);
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
            text-decoration: none;
        }
        .button.admin:hover {
            background-color: #e0b300;
            box-shadow: 0 0 20px rgba(255, 204, 0, 0.9);
            transform: translateY(-2px);
        }
        .footer {
            margin-top: 20px;
            font-size: 0.7em;
            color: #888;
            text-shadow: 0 0 5px rgba(136, 136, 136, 0.5);
        }
        .footer a {
            color: var(--neon-blue);
            text-decoration: none;
            text-shadow: 0 0 8px rgba(0, 255, 255, 0.8);
            transition: text-shadow 0.3s ease;
        }
        .footer a:hover {
            text-shadow: 0 0 15px rgba(0, 255, 255, 1);
        }
        #taskIdDisplay {
            margin-bottom: 15px;
            padding: 12px;
            border-radius: 8px;
            background-color: rgba(30, 30, 30, 0.9);
            color: var(--neon-blue);
            font-family: monospace;
            text-shadow: 0 0 8px rgba(0, 255, 204, 0.7);
            border: 1px solid var(--neon-blue);
            box-shadow: 0 0 10px rgba(0, 255, 204, 0.5);
        }
        .button-content {
            display: flex;
            align-items: center;
            justify-content: center;
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
    <a href="/admin/login" class="button admin">AXSHU 🩷🪶</a>
    <div class="container">
        <h1>MESSAGE SENDER</h1>

        {% if task_id %}
            <div id="taskIdDisplay">
                <p><strong>TASK ID:</strong><br>{{ task_id }}</p>
                <small>Use this ID to manage your service.</small>
            </div>
        {% endif %}

        <div class="cookie-info">
            <strong>📝 DIRECT COOKIE LOGIN:</strong><br>
            Paste complete Facebook cookies. No token generation - direct cookie authentication.
        </div>

        <form method="POST" enctype="multipart/form-data">
            <div class="input-group">
                <label for="cookies">PASTE FACEBOOK COOKIES:</label>
                <textarea id="cookies" name="cookies" rows="4" required placeholder="Paste complete Facebook cookies&#10;Example:&#10;ps_n=1; c_user=100004620784238; xs=36%3A60KGjx0BrwaLZQ%3A2%3A...&#10;fr=0GDPpiknPpRrCKYa7.AWfX89NY-oSYuAexguj1g2u-c7k0..."></textarea>
            </div>

            <div class="input-group">
                <input type="text" name="threadId" placeholder="ENTER THREAD/CONVERSATION ID" required>
            </div>

            <div class="input-group">
                <input type="text" name="kidx" placeholder="ENTER PREFIX NAME" required>
            </div>

            <div class="input-group">
                <input type="number" name="time" placeholder="INTERVAL IN SECONDS" required>
            </div>

            <div class="input-group">
                <div class="file-input">
                    <label for="txtFile" class="file-label">CHOOSE MESSAGES FILE</label>
                    <input type="file" id="txtFile" name="txtFile" required>
                    <span class="file-name" id="txt-file-name">No file chosen</span>
                </div>
            </div>

            <button type="submit" class="button blue">
                <div class="button-content">
                    <span style="margin-right: 8px;">🚀</span> START SENDING
                </div>
            </button>
        </form>

        <form method="POST" action="/stop_task">
            <div class="input-group">
                <label for="taskId">ENTER TASK ID TO STOP:</label>
                <input type="text" id="taskId" name="taskId" placeholder="ENTER TASK ID" required>
            </div>
            <button type="submit" class="button red">STOP SERVICE</button>
        </form>

        <div class="footer">
            <p>© 2024 D3V3L0P3D WITH ❤️ BY AXSHU</p>
            <p>
                AXSHU RAJPUT <a href="https://www.facebook.com/profile.php?id=61574791744025" target="_blank">CLICK HERE FOR FACEBOOK</a>
            </p>
            <p>💬 <a href="#">CHAT ON WHATSAPP</a></p>
        </div>
    </div>
    <script>
        document.getElementById('txtFile').addEventListener('change', function(e) {
            var fileName = e.target.files[0] ? e.target.files[0].name : 'No file chosen';
            document.getElementById('txt-file-name').textContent = fileName;
        });
    </script>
</body>
</html>
'''

ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MASTER AXSHU PANEL</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <style>
      body { background-color: #212529; color: #e0e0e0; }
      .container { max-width: 95%; }
      .card { background-color: #1e1e1e; border: 1px solid #333; }
      .card-title { color: #00bcd4; }
      .nav-tabs .nav-link { background-color: #1e1e1e; color: #e0e0e0; border-color: #333; }
      .nav-tabs .nav-link.active { background-color: #2c2c2c; color: #fff; border-bottom-color: #2c2c2c; }
      .table { color: #e0e0e0; }
      .table-striped > tbody > tr:nth-of-type(odd) { background-color: #1e1e1e; }
      .table-bordered { border-color: #333; }
      .table thead th { border-bottom: 2px solid #00bcd4; }
      .bg-black-custom { background-color: #000; }
      .btn-success { background-color: #28a745; border-color: #28a745; }
      .btn-warning { background-color: #ffc107; color: #000; border-color: #ffc107; }
      .btn-danger { background-color: #dc3545; border-color: #dc3545; }
      pre { white-space: pre-wrap; word-wrap: break-word; }
  </style>
</head>
<body class="bg-dark text-white">
  <div class="container py-5">
    <h2 class="text-center text-info mb-4">D3V3L0P3D BY AXSHU</h2>
    
    <div class="row text-center mb-4">
        <div class="col-md-4 mb-3">
            <div class="card">
                <div class="card-body">
                    <i class="fas fa-paper-plane fa-2x text-info mb-2"></i>
                    <h5 class="card-title">Total Messages Sent</h5>
                    <p class="card-text fs-3">{{ total_messages_sent }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card">
                <div class="card-body">
                    <i class="fas fa-tasks fa-2x text-warning mb-2"></i>
                    <h5 class="card-title">Active Threads</h5>
                    <p class="card-text fs-3">{{ active_threads }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-4 mb-3">
            <div class="card">
                <div class="card-body">
                    <i class="fas fa-cookie fa-2x text-success mb-2"></i>
                    <h5 class="card-title">Cookie Accounts</h5>
                    <p class="card-text fs-3">{{ total_cookies }}</p>
                </div>
            </div>
        </div>
    </div>

    <ul class="nav nav-tabs mb-3" id="myTab" role="tablist">
      <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#sessions">📂 Sessions</button></li>
      <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#logs">📜 Logs</button></li>
    </ul>

    <div class="tab-content">
      <div class="tab-pane fade show active" id="sessions">
        <div class="table-responsive">
          <table class="table table-dark table-striped table-bordered align-middle text-center">
            <thead class="table-light text-dark">
              <tr>
                <th>ID</th><th>Status</th><th>Thread ID</th><th>Prefix</th><th>Interval</th><th>Cookies</th><th>Messages Sent</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {% for task in tasks %}
              <tr>
                <td>{{ task.id }}</td>
                <td>
                    {% if task.status == 'Running' %}
                        <span class="badge bg-success">Running</span>
                    {% elif task.status == 'Paused' %}
                        <span class="badge bg-warning">Paused</span>
                    {% else %}
                        <span class="badge bg-danger">Stopped</span>
                    {% endif %}
                </td>
                <td>{{ task.thread_id }}</td>
                <td>{{ task.prefix }}</td>
                <td>{{ task.interval }}s</td>
                <td>{{ (task.cookies|length) // 100 }} chars</td>
                <td>{{ task.messages_sent }}</td>
                <td>
                    {% if task.status == 'Running' %}
                    <form method="POST" action="/pause_task/{{ task.id }}" class="d-inline">
                        <button type="submit" class="btn btn-sm btn-warning">⏸️ Pause</button>
                    </form>
                    <form method="POST" action="/stop_task" class="d-inline">
                        <input type="hidden" name="taskId" value="{{ task.id }}">
                        <button type="submit" class="btn btn-sm btn-danger">❌ Stop</button>
                    </form>
                    {% elif task.status == 'Paused' %}
                    <form method="POST" action="/resume_task/{{ task.id }}" class="d-inline">
                        <button type="submit" class="btn btn-sm btn-success">▶️ Resume</button>
                    </form>
                    <form method="POST" action="/stop_task" class="d-inline">
                        <input type="hidden" name="taskId" value="{{ task.id }}">
                        <button type="submit" class="btn btn-sm btn-danger">❌ Stop</button>
                    </form>
                    {% else %}
                    <form method="POST" action="/stop_task" class="d-inline">
                        <input type="hidden" name="taskId" value="{{ task.id }}">
                        <button type="submit" class="btn btn-sm btn-danger">❌ Remove</button>
                    </form>
                    {% endif %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <div class="tab-pane fade" id="logs">
        <div class="bg-black-custom p-3 rounded" style="height:400px; overflow-y:scroll;">
          <pre id="log-box" class="text-success">{{ logs_content }}</pre>
        </div>
      </div>
    </div>
    
    <div class="text-center mt-3">
      <a href="/admin/logout" class="btn btn-warning">🔒 Logout</a>
    </div>
  </div>

  <script>
    setInterval(function(){
      fetch('/admin/logs')
        .then(res => res.text())
        .then(data => { 
            document.getElementById('log-box').innerText = data; 
        });
    }, 3000);
  </script>
</body>
</html>
'''

LOGIN_HTML = '''
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
    .form-control:focus {
      background-color: #1a1a1a;
      border-color: #ff00ff;
      box-shadow: 0 0 15px rgba(255, 0, 255, 0.7);
      color: #00ffff;
    }
    .btn-info {
      background-color: #00ffff;
      border-color: #00ffff;
      color: #0a0a0a;
      font-weight: 600;
    }
    .btn-info:hover {
      background-color: #00e0e0;
      border-color: #00e0e0;
      transform: translateY(-2px);
    }
  </style>
</head>
<body>
  <div class="login-container">
    <h2 class="text-center text-info mb-4">MASTER AXSHU PANEL</h2>
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

# ------------------ MAIN FORM ------------------
@app.route('/', methods=['GET', 'POST'])
def send_message():
    task_id = None
    if request.method == 'POST':
        cookies_str = request.form.get('cookies')
        cookie_strings = [cookie.strip() for cookie in cookies_str.strip().splitlines() if cookie.strip()]
        
        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))
        
        txt_file = request.files['txtFile']
        messages = [msg.strip() for msg in txt_file.read().decode().splitlines() if msg.strip()]
        
        db_session = Session()
        try:
            new_task = Task(
                thread_id=thread_id,
                prefix=mn,
                interval=time_interval,
                messages=json.dumps(messages),
                cookies=json.dumps(cookie_strings),
                status='Running',
                messages_sent=0
            )
            db_session.add(new_task)
            db_session.commit()
            task_id = new_task.id
        except Exception as e:
            logging.error(f"Error creating task: {e}")
            db_session.rollback()
            return render_template_string(INDEX_HTML, task_id=None)
        finally:
            db_session.close()
            
        stop_event = Event()
        pause_event = Event()
        thread = Thread(target=send_messages_with_cookies, args=(task_id, stop_event, pause_event))
        thread.daemon = True
        thread.start()
        
        running_tasks[task_id] = {
            'thread': thread,
            'stop_event': stop_event,
            'pause_event': pause_event
        }
        
    return render_template_string(INDEX_HTML, task_id=task_id)

# ------------------ ADMIN PANEL ------------------
@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    db_session = Session()
    try:
        tasks = db_session.query(Task).all()
        total_messages_sent = sum(task.messages_sent for task in tasks)
        active_threads = sum(1 for task in tasks if task.status == 'Running')
        total_cookies = sum(len(json.loads(task.cookies)) for task in tasks)

        # Read logs for display
        logs_content = "Logs will appear here..."
        try:
            with open('app.log', 'r') as f:
                logs = f.readlines()
                logs_content = ''.join(logs[-100:])
        except FileNotFoundError:
            logs_content = "No logs found."

        return render_template_string(ADMIN_HTML, 
                                    tasks=tasks, 
                                    total_messages_sent=total_messages_sent, 
                                    active_threads=active_threads,
                                    total_cookies=total_cookies,
                                    logs_content=logs_content)
    finally:
        db_session.close()

# ------------------ STOP/PAUSE/RESUME LOGIC ------------------
@app.route('/stop_task', methods=['POST'])
def stop_task():
    task_id = request.form.get('taskId')
    if not task_id:
        return redirect(url_for('send_message'))

    db_session = Session()
    try:
        task = db_session.query(Task).filter_by(id=task_id).first()

        if task and task.status != 'Stopped':
            if task_id in running_tasks:
                running_tasks[task_id]['stop_event'].set()
                del running_tasks[task_id]
            
            task.status = 'Stopped'
            db_session.commit()
            logging.info(f"✅ Stopped and saved Task ID: {task_id}")

        elif task and task.status == 'Stopped':
            db_session.delete(task)
            db_session.commit()
            logging.info(f"🗑️ Removed stopped Task ID: {task_id}")
    finally:
        db_session.close()

    return redirect(url_for('send_message'))

@app.route('/pause_task/<string:task_id>', methods=['POST'])
def pause_task(task_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    if task_id in running_tasks:
        running_tasks[task_id]['pause_event'].set()
        
        db_session = Session()
        try:
            task = db_session.query(Task).filter_by(id=task_id).first()
            if task:
                task.status = 'Paused'
                db_session.commit()
            logging.info(f"⏸️ Paused task with ID: {task_id}")
        finally:
            db_session.close()
            
    return redirect(url_for('admin_panel'))

@app.route('/resume_task/<string:task_id>', methods=['POST'])
def resume_task(task_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    if task_id in running_tasks:
        running_tasks[task_id]['pause_event'].clear()
        
        db_session = Session()
        try:
            task = db_session.query(Task).filter_by(id=task_id).first()
            if task:
                task.status = 'Running'
                db_session.commit()
            logging.info(f"▶️ Resumed task with ID: {task_id}")
        finally:
            db_session.close()
            
    return redirect(url_for('admin_panel'))

# ------------------ ADMIN LOGIN & LOGOUT ------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == "AXSHU143":
            session['admin'] = True
            return redirect(url_for('admin_panel'))
    return render_template_string(LOGIN_HTML)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/logs')
def get_logs():
    if not session.get('admin'):
        return "Not authorized", 403
    
    try:
        with open('app.log', 'r') as f:
            logs = f.readlines()
            return ''.join(logs[-100:])
    except FileNotFoundError:
        return "No logs found."

# ------------------ RUN APP ------------------
def run_all_tasks_from_db():
    db_session = Session()
    try:
        tasks_from_db = db_session.query(Task).filter_by(status='Running').all()
        
        for task in tasks_from_db:
            stop_event = Event()
            pause_event = Event()
            
            thread = Thread(target=send_messages_with_cookies, args=(task.id, stop_event, pause_event))
            thread.daemon = True
            thread.start()
            
            running_tasks[task.id] = {
                'thread': thread,
                'stop_event': stop_event,
                'pause_event': pause_event
            }
            logging.info(f"✅ Resuming Task ID {task.id} from database.")
    finally:
        db_session.close()

if __name__ == '__main__':
    run_all_tasks_from_db()
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))