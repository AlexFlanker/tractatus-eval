#!/usr/bin/env python3
"""
Tractatus-Eval Progress Dashboard
A lightweight HTTP server that displays real-time evaluation progress.
Run: python3 scripts/progress_dashboard.py
Open: http://localhost:8765
"""
import http.server
import json
import re
import subprocess
import os
from datetime import datetime

PORT = 8765

# Command IDs to monitor (from lm_eval runs)
MISTRAL_LOG = "/tmp/eval_mistral_7b.log"
LLAMA8B_LOG = "/tmp/eval_llama3_8b.log"

def parse_progress(log_path, model_name):
    """Parse lm_eval log file for progress info."""
    if not os.path.exists(log_path):
        return {"model": model_name, "status": "waiting", "progress": 0, "total": 36000,
                "speed": 0, "eta": "—", "detail": "Not started yet"}
    
    try:
        # Read last 5KB of log
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 5000))
            content = f.read().decode('utf-8', errors='replace')
        
        # Check if completed (has results table)
        if '|tractatus_' in content and 'Exit code: 0' in content:
            return {"model": model_name, "status": "done", "progress": 36000, "total": 36000,
                    "speed": 0, "eta": "Done!", "detail": "Evaluation complete ✅"}
        
        # Check for errors
        if 'Error' in content and 'Traceback' in content:
            error_match = re.search(r'(Error|Exception): (.+)', content)
            err_msg = error_match.group(0) if error_match else "Unknown error"
            return {"model": model_name, "status": "error", "progress": 0, "total": 36000,
                    "speed": 0, "eta": "—", "detail": f"❌ {err_msg[:100]}"}
        
        # Parse progress bar: "Running loglikelihood requests:  22%|..| 7951/36000 [26:25<1:06:02,  7.08it/s]"
        matches = re.findall(r'(\d+)/36000 \[[\d:]+<([\d:]+),\s*([\d.]+)it/s\]', content)
        if matches:
            last = matches[-1]
            current = int(last[0])
            eta = last[1]
            speed = float(last[2])
            return {"model": model_name, "status": "running", "progress": current, "total": 36000,
                    "speed": speed, "eta": eta, "detail": f"Processing at {speed:.1f} it/s"}
        
        # Check if loading
        if 'Loading weights' in content or 'Materializing' in content:
            return {"model": model_name, "status": "loading", "progress": 0, "total": 36000,
                    "speed": 0, "eta": "—", "detail": "Loading model weights..."}
        
        if 'Building contexts' in content:
            return {"model": model_name, "status": "loading", "progress": 0, "total": 36000,
                    "speed": 0, "eta": "—", "detail": "Building evaluation contexts..."}
        
        return {"model": model_name, "status": "unknown", "progress": 0, "total": 36000,
                "speed": 0, "eta": "—", "detail": "Initializing..."}
    except Exception as e:
        return {"model": model_name, "status": "error", "progress": 0, "total": 36000,
                "speed": 0, "eta": "—", "detail": str(e)}


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tractatus-Eval Progress</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  
  * { margin: 0; padding: 0; box-sizing: border-box; }
  
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0f0f1a;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }
  
  .container {
    max-width: 700px;
    width: 100%;
  }
  
  h1 {
    font-size: 1.8rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 0.3rem;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  
  .subtitle {
    text-align: center;
    color: #888;
    font-size: 0.85rem;
    margin-bottom: 2rem;
  }
  
  .card {
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.3s;
  }
  .card:hover { border-color: #3a3a6a; }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  
  .model-name {
    font-size: 1.1rem;
    font-weight: 600;
    color: #fff;
  }
  
  .status-badge {
    font-size: 0.75rem;
    font-weight: 500;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .status-running  { background: #1e3a5f; color: #60a5fa; }
  .status-loading  { background: #3a2e1e; color: #f59e0b; }
  .status-waiting  { background: #2a2a3a; color: #888; }
  .status-done     { background: #1e3a2e; color: #34d399; }
  .status-error    { background: #3a1e1e; color: #f87171; }
  .status-unknown  { background: #2a2a3a; color: #888; }
  
  .progress-container {
    background: #0f0f1a;
    border-radius: 10px;
    height: 24px;
    overflow: hidden;
    position: relative;
    margin-bottom: 0.75rem;
  }
  
  .progress-bar {
    height: 100%;
    border-radius: 10px;
    transition: width 0.6s ease;
    position: relative;
    overflow: hidden;
  }
  .progress-bar.running {
    background: linear-gradient(90deg, #2563eb, #60a5fa);
  }
  .progress-bar.done {
    background: linear-gradient(90deg, #059669, #34d399);
  }
  .progress-bar.error {
    background: linear-gradient(90deg, #dc2626, #f87171);
    width: 100% !important;
  }
  .progress-bar.loading, .progress-bar.waiting, .progress-bar.unknown {
    background: linear-gradient(90deg, #d97706, #f59e0b);
    animation: pulse 2s ease-in-out infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
  
  .progress-bar::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    animation: shimmer 2s infinite;
  }
  @keyframes shimmer {
    100% { left: 100%; }
  }
  
  .progress-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    z-index: 1;
  }
  
  .stats {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #888;
  }
  .stats span { display: flex; gap: 0.3rem; align-items: center; }
  .stats .value { color: #ccc; font-weight: 500; }
  
  .detail {
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.5rem;
    font-style: italic;
  }
  
  .refresh-btn {
    display: block;
    width: 100%;
    padding: 0.9rem;
    border: none;
    border-radius: 12px;
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    color: #fff;
    font-size: 1rem;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.3s;
    margin-top: 0.5rem;
  }
  .refresh-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(37, 99, 235, 0.3);
  }
  .refresh-btn:active { transform: translateY(0); }
  .refresh-btn.spinning { opacity: 0.7; pointer-events: none; }
  
  .last-update {
    text-align: center;
    color: #555;
    font-size: 0.75rem;
    margin-top: 1rem;
  }
</style>
</head>
<body>
<div class="container">
  <h1>🏛️ Tractatus-Eval</h1>
  <p class="subtitle">Model Evaluation Progress Dashboard</p>
  <div id="cards"></div>
  <button class="refresh-btn" id="refreshBtn" onclick="refresh()">
    🔄 Refresh Progress
  </button>
  <p class="last-update" id="lastUpdate">Loading...</p>
</div>

<script>
function renderCard(d) {
  const pct = d.total > 0 ? (d.progress / d.total * 100).toFixed(1) : 0;
  return `
    <div class="card">
      <div class="card-header">
        <span class="model-name">${d.model}</span>
        <span class="status-badge status-${d.status}">${d.status}</span>
      </div>
      <div class="progress-container">
        <div class="progress-text">${pct}% (${d.progress.toLocaleString()} / ${d.total.toLocaleString()})</div>
        <div class="progress-bar ${d.status}" style="width: ${Math.max(pct, d.status === 'loading' ? 5 : 0)}%"></div>
      </div>
      <div class="stats">
        <span>Speed: <span class="value">${d.speed > 0 ? d.speed.toFixed(1) + ' it/s' : '—'}</span></span>
        <span>ETA: <span class="value">${d.eta}</span></span>
      </div>
      <div class="detail">${d.detail}</div>
    </div>`;
}

async function refresh() {
  const btn = document.getElementById('refreshBtn');
  btn.classList.add('spinning');
  btn.textContent = '⏳ Checking...';
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('cards').innerHTML = data.map(renderCard).join('');
    document.getElementById('lastUpdate').textContent = 
      'Last updated: ' + new Date().toLocaleTimeString();
  } catch(e) {
    document.getElementById('lastUpdate').textContent = 'Error: ' + e.message;
  }
  btn.classList.remove('spinning');
  btn.textContent = '🔄 Refresh Progress';
}

refresh();
</script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/status':
            models = [
                parse_progress(MISTRAL_LOG, "Mistral-7B-v0.1"),
                parse_progress(LLAMA8B_LOG, "Meta-Llama-3-8B"),
            ]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(models).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
    
    def log_message(self, format, *args):
        pass  # Suppress request logs

if __name__ == '__main__':
    server = http.server.HTTPServer(('', PORT), Handler)
    print(f"🏛️  Tractatus-Eval Progress Dashboard")
    print(f"   Open: http://localhost:{PORT}")
    print(f"   Press Ctrl+C to stop")
    server.serve_forever()
