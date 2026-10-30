#!/usr/bin/env python3
"""
Bandwidth Hog Detector Pro - Main Application
Flask server with REST API and WebSocket - WORKING VERSION
"""

import os
import sys
import time
import json
import yaml
import logging
import eventlet # type: ignore
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add core to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core import NetworkTrafficManager

# ==================== Configuration ====================

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ Error loading config: {e}")
        return {
            'server': {'host': '0.0.0.0', 'port': 5000, 'debug': False},
            'network': {'interface': 'Wi-Fi', 'promiscuous': True},
            'monitoring': {'update_interval': 2},
            'logging': {'level': 'INFO', 'file': 'logs/app.log'}
        }

config = load_config()

# ==================== Flask App Setup ====================

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')
app.config['SECRET_KEY'] = 'bandwidth-hog-detector-pro-secret'
CORS(app)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    async_mode='eventlet'
)

# ==================== Logging Setup ====================

log_file = config['logging'].get('file', 'logs/app.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config['logging'].get('level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== Traffic Manager ====================

try:
    traffic_manager = NetworkTrafficManager(config['network'])
    logger.info("✅ Traffic manager initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize traffic manager: {e}")
    sys.exit(1)

# ==================== Routes ====================

@app.route('/')
def index():
    return render_template('dashboard.html', config=config)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', config=config)

@app.route('/analytics')
def analytics():
    return render_template('analytics.html', config=config)

@app.route('/settings')
def settings():
    return render_template('settings.html', config=config)

# ==================== API Routes ====================

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'running',
        'interface': traffic_manager.interface,
        'uptime': time.time() - traffic_manager.stats['start_time'],
        'config': config
    })

@app.route('/api/dashboard')
def api_dashboard():
    try:
        return jsonify(traffic_manager.get_dashboard_data())
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices')
def api_devices():
    try:
        limit = request.args.get('limit', 10, type=int)
        devices = traffic_manager.accounting.get_top_consumers(limit)
        
        formatted = []
        for i, device in enumerate(devices, 1):
            formatted.append({
                'rank': i,
                'ip': device['ip'],
                'total_mb': round(device['total_mb'], 2),
                'sent_mb': round(device['sent_mb'], 2),
                'recv_mb': round(device['recv_mb'], 2),
                'packets': device['packets'],
                'status': get_device_status(device['ip'])
            })
        return jsonify(formatted)
    except Exception as e:
        logger.error(f"Devices error: {e}")
        return jsonify([]), 500

@app.route('/api/anomalies')
def api_anomalies():
    try:
        return jsonify(traffic_manager.anomaly_detector.get_recent_anomalies(20))
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/rules')
def api_rules():
    try:
        rules = traffic_manager.control.get_active_rules()
        formatted = []
        for ip, rule in rules.items():
            formatted.append({
                'ip': ip,
                'type': rule['type'],
                'rate': rule.get('rate', ''),
                'expires': rule.get('expiry', 0)
            })
        return jsonify(formatted)
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/control', methods=['POST'])
def api_control():
    try:
        data = request.json
        action = data.get('action')
        ip = data.get('ip')
        
        if not action or not ip:
            return jsonify({'success': False, 'error': 'Missing parameters'})
        
        success = traffic_manager.control_device(
            action=action,
            ip=ip,
            rate=data.get('rate'),
            duration=data.get('duration')
        )
        
        if success:
            socketio.emit('control_update', {
                'action': action,
                'ip': ip,
                'timestamp': time.time()
            })
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def api_reset():
    try:
        traffic_manager.accounting.reset()
        traffic_manager.capture.reset_stats()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== WebSocket Events ====================

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    logger.info(f"✅ Client connected: {client_id}")
    
    def send_updates():
        update_count = 0
        while True:
            try:
                update_count += 1
                data = traffic_manager.get_dashboard_data()
                
                socketio.emit('dashboard_update', {
                    'update_id': update_count,
                    'timestamp': time.time(),
                    'data': data
                }, room=client_id)
                
                socketio.sleep(config['monitoring'].get('update_interval', 2))
            except Exception as e:
                logger.error(f"Update error: {e}")
                socketio.sleep(5)
    
    socketio.start_background_task(send_updates)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"❌ Client disconnected: {request.sid}")

# ==================== Helper Functions ====================

def get_device_status(ip):
    try:
        rules = traffic_manager.control.get_active_rules()
        if ip in rules:
            return rules[ip]['type']
    except:
        pass
    return 'normal'

# ==================== Main ====================

def main():
    print("\n" + "=" * 60)
    print("BANDWIDTH HOG DETECTOR PRO".center(60))
    print("=" * 60)
    
    traffic_manager.start()
    
    server_config = config.get('server', {'host': '0.0.0.0', 'port': 5000})
    host = server_config['host']
    port = server_config['port']
    
    print(f"\n🌐 Server starting on {host}:{port}")
    print(f"📊 Dashboard: http://localhost:{port}")
    print("⏎ Press Ctrl+C to stop\n")
    
    try:
        # SIMPLE - No extra parameters!
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        traffic_manager.stop()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traffic_manager.stop()
        sys.exit(1)

if __name__ == '__main__':
    main()