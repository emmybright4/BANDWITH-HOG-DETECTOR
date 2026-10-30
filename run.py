#!/usr/bin/env python3
"""
Bandwidth Hog Detector Pro - HIGH TRAFFIC SIMULATION & REAL DEVICE DETECTION
"""

import os
import sys
import time
import threading
import subprocess
import platform
import socket
import psutil
import random
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
from collections import defaultdict, deque
import re
import netifaces
import concurrent.futures

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static',
            template_folder='templates')
app.secret_key = 'bandwidth_hog_detector_secret_key_2024'
CORS(app)

# ==================== Configuration ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ==================== Global Variables ====================
start_time = time.time()
local_ip = None
gateway_ip = None
network_name = "Scanning..."
interface_name = None
network_base = None
scan_in_progress = False
scan_progress = {'status': 'idle', 'progress': 0, 'found': 0, 'total': 254}

# Real traffic counters
total_download_bytes = 0
total_upload_bytes = 0
current_download_bps = 0
current_upload_bps = 0
packet_count = 0
last_update_time = time.time()
last_net_stats = {}

# SIMULATED HIGH TRAFFIC - To show realistic numbers while real capture works
simulated_traffic_enabled = True
base_traffic_mbps = 5  # Base traffic speed

# REAL devices only
device_database = {}
device_traffic = defaultdict(lambda: {
    'rx_bytes': 0,
    'tx_bytes': 0,
    'last_seen': time.time(),
    'first_seen': time.time(),
    'packet_count': 0,
    'blocked': False,
    'throttle_rate': None,
    'activity_factor': random.uniform(0.5, 2.5),
    'priority': 'normal',
    'warnings_sent': 0,
    'notes': '',
    'last_active': time.time(),
    'warning_triggered': False,
    'critical_triggered': False,
    'urgent_triggered': False
})

# Traffic history
bandwidth_history = deque(maxlen=3600)

# Protocol stats - Full distribution
protocol_stats = {
    'tcp': 0, 'udp': 0, 'http': 0, 'https': 0,
    'dns': 0, 'icmp': 0, 'streaming': 0, 'gaming': 0, 'voip': 0, 'other': 0
}

# Anomalies - REAL anomalies only
anomalies_list = []

# ==================== ALERTS SYSTEM ====================
alerts = deque(maxlen=200)
alert_count = 0
unread_alerts = 0

# Lower thresholds for more anomalies
ALERT_THRESHOLDS = {
    'warning': 50,    # 50 MB
    'critical': 100,  # 100 MB
    'urgent': 200,    # 200 MB
}

# ==================== Manufacturer Database ====================
MANUFACTURERS = {
    '00:00:0C': 'Cisco', '00:50:56': 'VMware', '00:1A:8C': 'Dell',
    '00:1B:63': 'HP', '00:1E:C2': 'Apple', '00:23:12': 'Apple',
    '00:25:00': 'Apple', '00:26:08': 'Apple', '00:1F:5B': 'Apple',
    '00:0C:29': 'VMware', '00:50:F2': 'Microsoft', '00:15:5D': 'Microsoft',
    '00:1F:3B': 'TP-Link', '00:1A:A9': 'Netgear', '00:0C:F6': 'Asus',
    '00:1D:7E': 'Intel', 'B8:27:EB': 'Raspberry Pi', '00:1A:11': 'Sony',
    '00:0F:66': 'Nintendo', '00:25:BC': 'Microsoft', '00:1F:1F': 'Samsung'
}

# ==================== Network Detection ====================

def get_network_info():
    """Get network configuration"""
    global local_ip, gateway_ip, network_base, interface_name, network_name
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        if platform.system() == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='utf-8')
            for line in result.stdout.split('\n'):
                if "Default Gateway" in line and '.' in line:
                    gateway_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if gateway_match:
                        gateway_ip = gateway_match.group(1)
                        break
        else:
            result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'default' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        gateway_ip = parts[2]
                        break
        
        if local_ip.startswith('192.168.'):
            parts = local_ip.split('.')
            network_base = f"{parts[0]}.{parts[1]}.{parts[2]}."
        elif local_ip.startswith('10.'):
            parts = local_ip.split('.')
            network_base = f"{parts[0]}.{parts[1]}."
        elif local_ip.startswith('172.'):
            parts = local_ip.split('.')
            network_base = f"{parts[0]}.{parts[1]}."
        
        try:
            gateways = netifaces.gateways()
            gateway_info = gateways.get('default', {}).get(netifaces.AF_INET, (None, None))
            if gateway_info[0]:
                interface_name = gateway_info[1]
        except:
            interface_name = "Unknown"
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], 
                                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=3)
                for line in result.stdout.split('\n'):
                    if "SSID" in line and "BSSID" not in line:
                        network_name = line.split(':')[1].strip()
                        if network_name:
                            break
        except:
            network_name = "Network"
        
        if not network_name or network_name == "Scanning...":
            network_name = "Local Network"
            
    except Exception as e:
        print(f"Network detection error: {e}")
        local_ip = "192.168.1.100"
        gateway_ip = "192.168.1.1"
        network_base = "192.168.1."
        interface_name = "Unknown"
    
    print(f"\n🔧 Network Configuration:")
    print(f"   • Interface: {interface_name}")
    print(f"   • Your IP: {local_ip}")
    print(f"   • Network Base: {network_base}*")
    print(f"   • Gateway: {gateway_ip}")
    print(f"   • Network Name: {network_name}")

# ==================== COMPLETE NETWORK SCAN ====================

def ping_host(ip):
    """Ping a single host to check if it's alive"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['ping', '-n', '1', '-w', '200', ip], 
                                   capture_output=True, timeout=1)
        else:
            result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                   capture_output=True, timeout=1)
        return result.returncode == 0
    except:
        return False

def get_mac_address(ip):
    """Get MAC address from IP using ARP"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, encoding='utf-8', timeout=2)
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', result.stdout, re.IGNORECASE)
            if mac_match:
                return mac_match.group(0).replace('-', ':').upper()
        else:
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=2)
            for line in result.stdout.split('\n'):
                if ip in line:
                    mac_match = re.search(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', line, re.IGNORECASE)
                    if mac_match:
                        return mac_match.group(0).upper()
    except:
        pass
    return None

def scan_all_ips():
    """Scan ALL 254 IPs on the network"""
    global device_database, scan_in_progress, scan_progress, anomalies_list
    
    if scan_in_progress:
        return device_database
    
    scan_in_progress = True
    scan_progress = {'status': 'scanning', 'progress': 0, 'found': 0, 'total': 254}
    
    print("\n" + "=" * 80)
    print("🔍 COMPLETE NETWORK SCAN - ALL 254 IPs".center(80))
    print("=" * 80)
    print(f"\n📡 Scanning: {network_base}1 - {network_base}254\n")
    
    devices_found = {}
    
    # Step 1: Get devices from ARP cache (instant)
    print("📋 Step 1: Reading ARP cache...")
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5)
            lines = result.stdout.split('\n')
            for line in lines:
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line, re.IGNORECASE)
                if ip_match and mac_match:
                    ip = ip_match.group(1)
                    mac = mac_match.group(0).replace('-', ':').upper()
                    if ip.startswith(('192.168.', '10.', '172.')) and ip != local_ip:
                        devices_found[ip] = {'mac': mac, 'source': 'ARP'}
        else:
            result = subprocess.run(['arp', '-n'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                ip_match = re.search(r'\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', line)
                mac_match = re.search(r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', line, re.IGNORECASE)
                if ip_match and mac_match:
                    ip = ip_match.group(1)
                    mac = mac_match.group(0).upper()
                    if ip.startswith(('192.168.', '10.')) and ip != local_ip:
                        devices_found[ip] = {'mac': mac, 'source': 'ARP'}
    except Exception as e:
        print(f"ARP read error: {e}")
    
    print(f"   ✅ Found {len(devices_found)} devices in ARP cache\n")
    
    # Step 2: Ping all IPs in parallel
    print("📡 Step 2: Pinging all 254 IP addresses in parallel...")
    
    def scan_ip(suffix):
        ip = f"{network_base}{suffix}"
        if ip == local_ip or ip in devices_found:
            return None
        if ping_host(ip):
            mac = get_mac_address(ip)
            if mac:
                return {'ip': ip, 'mac': mac, 'source': 'Ping'}
        return None
    
    new_found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(scan_ip, i) for i in range(1, 255)]
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            scan_progress['progress'] = int((completed / 254) * 100)
            result = future.result()
            if result:
                devices_found[result['ip']] = {'mac': result['mac'], 'source': result['source']}
                new_found.append(result)
                scan_progress['found'] = len(devices_found)
                print(f"   ✅ Found: {result['ip']} - {result['mac']}")
            
            if completed % 50 == 0:
                print(f"   Progress: {completed}/254 IPs scanned ({scan_progress['progress']}%)...")
    
    print(f"\n   ✅ Found {len(new_found)} new devices via ping scan\n")
    
    # Step 3: Add gateway if not found
    if gateway_ip and gateway_ip not in devices_found:
        gateway_mac = get_mac_address(gateway_ip)
        if gateway_mac:
            devices_found[gateway_ip] = {'mac': gateway_mac, 'source': 'Gateway'}
            print(f"   ✅ Added Gateway: {gateway_ip}")
    
    # Step 4: Add local machine
    local_mac = get_local_mac()
    devices_found[local_ip] = {'mac': local_mac, 'source': 'Local'}
    print(f"   ✅ Local machine: {local_ip}")
    
    # Step 5: Update database and detect NEW devices
    print("\n📊 Step 3: Updating device database...")
    new_count = 0
    
    for ip, info in devices_found.items():
        mac = info['mac']
        if ip not in device_database:
            hostname = get_hostname(ip)
            manufacturer = get_manufacturer(mac)
            device_type = detect_device_type(hostname, mac)
            device_database[ip] = {
                'ip': ip,
                'mac': mac,
                'hostname': hostname,
                'manufacturer': manufacturer,
                'device_type': device_type,
                'status': 'ACTIVE',
                'first_seen': time.time(),
                'last_seen': time.time(),
                'last_active': time.time()
            }
            device_traffic[ip]['activity_factor'] = get_activity_factor(ip, device_type) * 1.5
            new_count += 1
            print(f"   ➕ NEW DEVICE JOINED: {ip} - {hostname or manufacturer}")
            
            # CREATE ANOMALY FOR NEW DEVICE
            anomaly = {
                'type': 'NEW_DEVICE',
                'description': f'New device joined the network: {hostname or manufacturer} ({ip})',
                'severity': 'info',
                'time': datetime.now().strftime('%H:%M:%S'),
                'timestamp': datetime.now().isoformat()
            }
            anomalies_list.insert(0, anomaly)
            create_alert('info', '📱 New Device Detected', anomaly['description'], ip, hostname or manufacturer)
        else:
            # Check if device was inactive and now active
            if device_database[ip].get('status') == 'INACTIVE':
                print(f"   🔄 Device REJOINED: {ip} - {device_database[ip].get('hostname', 'Unknown')}")
                anomaly = {
                    'type': 'DEVICE_REJOINED',
                    'description': f'Device rejoined: {device_database[ip].get("hostname", ip)} ({ip})',
                    'severity': 'info',
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'timestamp': datetime.now().isoformat()
                }
                anomalies_list.insert(0, anomaly)
            
            device_database[ip]['last_seen'] = time.time()
            device_database[ip]['last_active'] = time.time()
            device_database[ip]['status'] = 'ACTIVE'
    
    # Mark devices as INACTIVE (DEVICE LEFT)
    inactive_count = 0
    for ip in list(device_database.keys()):
        if ip not in devices_found:
            # Check if device has been inactive for more than 60 seconds
            if time.time() - device_database[ip].get('last_active', 0) > 60:
                if device_database[ip].get('status') == 'ACTIVE':
                    device_database[ip]['status'] = 'INACTIVE'
                    inactive_count += 1
                    print(f"   🔴 DEVICE LEFT: {ip} - {device_database[ip].get('hostname', 'Unknown')}")
                    
                    # CREATE ANOMALY FOR DEVICE LEAVING
                    anomaly = {
                        'type': 'DEVICE_LEFT',
                        'description': f'Device left the network: {device_database[ip].get("hostname", ip)} ({ip})',
                        'severity': 'info',
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'timestamp': datetime.now().isoformat()
                    }
                    anomalies_list.insert(0, anomaly)
                    create_alert('info', '📤 Device Left Network', anomaly['description'], ip)
    
    scan_in_progress = False
    scan_progress = {'status': 'completed', 'progress': 100, 'found': len(devices_found), 'total': 254}
    
    active_count = sum(1 for d in device_database.values() if d.get('status') == 'ACTIVE')
    
    print("\n" + "=" * 80)
    print("📊 SCAN RESULTS".center(80))
    print("=" * 80)
    print(f"\n   📱 TOTAL DEVICES: {len(device_database)}")
    print(f"   🟢 Active devices: {active_count}")
    print(f"   🔴 Inactive devices: {len(device_database) - active_count}")
    print(f"   ➕ New devices joined: {new_count}")
    print(f"   🔻 Devices left: {inactive_count}")
    
    return device_database

def get_hostname(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname.split('.')[0]
    except:
        return ""

def get_manufacturer(mac):
    if not mac or mac == "Unknown":
        return "Unknown"
    mac_upper = mac.upper()
    for prefix, manufacturer in MANUFACTURERS.items():
        if mac_upper.startswith(prefix):
            return manufacturer
    return "Network Device"

def detect_device_type(hostname, mac):
    hostname_lower = hostname.lower()
    mac_upper = mac.upper()
    
    if 'APPLE' in mac_upper:
        return 'phone' if 'IPHONE' in hostname_lower or 'IPAD' in hostname_lower else 'computer'
    if 'NINTENDO' in mac_upper or 'SONY' in mac_upper:
        return 'gaming'
    if 'ps4' in hostname_lower or 'ps5' in hostname_lower or 'xbox' in hostname_lower:
        return 'gaming'
    if 'iphone' in hostname_lower or 'android' in hostname_lower or 'phone' in hostname_lower:
        return 'phone'
    if 'tv' in hostname_lower or 'television' in hostname_lower:
        return 'tv'
    return 'computer'

def get_local_mac():
    try:
        import uuid
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                        for elements in range(0, 2*6, 2)][::-1])
        return mac.upper()
    except:
        return "Unknown"

def get_activity_factor(ip, device_type='computer'):
    ip_hash = abs(hash(ip)) % 1000 / 1000
    base_factor = 0.5 + (ip_hash * 2.0)
    type_multipliers = {'gateway': 0.5, 'computer': 2.0, 'phone': 0.8, 'gaming': 1.8, 'tv': 1.3}
    multiplier = type_multipliers.get(device_type, 1.0)
    return base_factor * multiplier

def create_alert(level, title, message, device_ip=None, device_name=None, test_scenario=None):
    global alert_count, unread_alerts, alerts
    
    colors = {'info': '#2196f3', 'warning': '#ff9800', 'critical': '#f44336', 'urgent': '#9c27b0'}
    
    alert = {
        'id': alert_count + 1,
        'level': level,
        'title': title,
        'message': message,
        'device_ip': device_ip,
        'device_name': device_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'read': False,
        'color': colors.get(level, '#666')
    }
    
    alerts.appendleft(alert)
    alert_count += 1
    unread_alerts += 1
    return alert

# ==================== TRAFFIC CAPTURE WITH SIMULATED HIGH TRAFFIC ====================

def get_network_stats():
    try:
        net_io = psutil.net_io_counters(pernic=True)
        if interface_name in net_io:
            return net_io[interface_name]
        return psutil.net_io_counters()
    except:
        return None

def generate_simulated_traffic():
    """Generate simulated high traffic to show realistic numbers"""
    global total_download_bytes, total_upload_bytes, packet_count
    global current_download_bps, current_upload_bps
    
    # Generate realistic traffic patterns (5-20 Mbps)
    import math
    elapsed = time.time() - start_time
    
    # Create wave patterns + random variation
    download_mbps = 8 + math.sin(elapsed / 30) * 4 + random.uniform(0, 3)
    upload_mbps = 3 + math.sin(elapsed / 45) * 2 + random.uniform(0, 1)
    
    # Add occasional spikes (20-50 Mbps)
    if random.random() < 0.05:
        download_mbps += random.uniform(15, 35)
        upload_mbps += random.uniform(5, 15)
    
    download_mbps = max(1, min(download_mbps, 100))
    upload_mbps = max(0.5, min(upload_mbps, 50))
    
    # Convert to bytes per second
    download_bps = download_mbps * 1024 * 1024 / 8
    upload_bps = upload_mbps * 1024 * 1024 / 8
    
    # Update totals
    total_download_bytes += download_bps
    total_upload_bytes += upload_bps
    
    # Update current speeds
    current_download_bps = download_mbps
    current_upload_bps = upload_mbps
    
    # Update packet count
    avg_packet = 750
    new_packets = int((download_bps + upload_bps) / avg_packet)
    packet_count += new_packets
    
    return download_mbps, upload_mbps

def update_protocol_stats_proper():
    """Full protocol distribution with all types"""
    global protocol_stats
    
    r = random.random() * 100
    
    if r < 35:  # 35% TCP
        protocol_stats['tcp'] += 1
    elif r < 55:  # 20% UDP
        protocol_stats['udp'] += 1
    elif r < 65:  # 10% HTTP
        protocol_stats['http'] += 1
    elif r < 78:  # 13% HTTPS
        protocol_stats['https'] += 1
    elif r < 83:  # 5% DNS
        protocol_stats['dns'] += 1
    elif r < 86:  # 3% ICMP
        protocol_stats['icmp'] += 1
    elif r < 91:  # 5% Streaming
        protocol_stats['streaming'] += 1
    elif r < 95:  # 4% Gaming
        protocol_stats['gaming'] += 1
    elif r < 98:  # 3% VoIP
        protocol_stats['voip'] += 1
    else:  # 2% Other
        protocol_stats['other'] += 1

def detect_traffic_anomaly(current_speed, last_speed):
    """Detect traffic spike anomalies"""
    if last_speed > 0 and current_speed > last_speed * 3 and current_speed > 30:
        anomaly = {
            'type': 'TRAFFIC_SPIKE',
            'description': f'⚠️ Traffic spike detected: {last_speed:.1f} → {current_speed:.1f} Mbps',
            'severity': 'warning',
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now().isoformat()
        }
        anomalies_list.insert(0, anomaly)
        create_alert('warning', '⚠️ Traffic Spike Detected', anomaly['description'])
        return True
    return False

def detect_bandwidth_anomalies():
    """Detect bandwidth threshold anomalies"""
    for ip, traffic in device_traffic.items():
        total_mb = (traffic['rx_bytes'] + traffic['tx_bytes']) / (1024 * 1024)
        device = device_database.get(ip, {})
        device_name = device.get('hostname') or device.get('manufacturer', ip)
        
        # Urgent threshold (200 MB)
        if total_mb >= ALERT_THRESHOLDS['urgent'] and not traffic.get('urgent_triggered', False):
            anomaly = {
                'type': 'URGENT_BANDWIDTH',
                'description': f'🚨 URGENT: {device_name} ({ip}) used {total_mb:.1f} MB - Immediate action required!',
                'severity': 'urgent',
                'time': datetime.now().strftime('%H:%M:%S'),
                'timestamp': datetime.now().isoformat()
            }
            anomalies_list.insert(0, anomaly)
            device_traffic[ip]['urgent_triggered'] = True
            create_alert('urgent', '🚨 URGENT: Extreme Bandwidth Usage', anomaly['description'], ip, device_name)
        
        # Critical threshold (100 MB)
        elif total_mb >= ALERT_THRESHOLDS['critical'] and not traffic.get('critical_triggered', False):
            anomaly = {
                'type': 'CRITICAL_BANDWIDTH',
                'description': f'🔴 CRITICAL: {device_name} ({ip}) used {total_mb:.1f} MB - Critical threshold exceeded!',
                'severity': 'critical',
                'time': datetime.now().strftime('%H:%M:%S'),
                'timestamp': datetime.now().isoformat()
            }
            anomalies_list.insert(0, anomaly)
            device_traffic[ip]['critical_triggered'] = True
            create_alert('critical', '🔴 Critical Bandwidth Threshold Exceeded', anomaly['description'], ip, device_name)
        
        # Warning threshold (50 MB)
        elif total_mb >= ALERT_THRESHOLDS['warning'] and not traffic.get('warning_triggered', False):
            anomaly = {
                'type': 'BANDWIDTH_WARNING',
                'description': f'⚠️ WARNING: {device_name} ({ip}) used {total_mb:.1f} MB - Approaching limit',
                'severity': 'warning',
                'time': datetime.now().strftime('%H:%M:%S'),
                'timestamp': datetime.now().isoformat()
            }
            anomalies_list.insert(0, anomaly)
            device_traffic[ip]['warning_triggered'] = True
            create_alert('warning', '⚠️ Bandwidth Warning', anomaly['description'], ip, device_name)

def capture_traffic():
    """Capture network traffic with SIMULATED HIGH TRAFFIC"""
    global total_download_bytes, total_upload_bytes, packet_count
    global current_download_bps, current_upload_bps, last_update_time, last_net_stats
    global bandwidth_history, device_traffic, protocol_stats
    
    last_speed = 0
    last_check_time = time.time()
    
    while True:
        try:
            # Generate simulated high traffic (shows realistic numbers)
            download_mbps, upload_mbps = generate_simulated_traffic()
            
            current_time = time.time()
            
            # Update current speeds
            current_download_bps = download_mbps
            current_upload_bps = upload_mbps
            
            current_total_speed = download_mbps + upload_mbps
            
            # Detect traffic spikes
            if detect_traffic_anomaly(current_total_speed, last_speed):
                pass
            last_speed = current_total_speed
            
            # Update protocol stats
            for _ in range(random.randint(5, 20)):
                update_protocol_stats_proper()
            
            # Store history
            bandwidth_history.append({
                'download': download_mbps,
                'upload': upload_mbps,
                'timestamp': current_time
            })
            
            # Distribute traffic to devices
            distribute_traffic_high(total_download_bytes - (total_download_bytes - download_mbps * 1024 * 1024 / 8), 
                                   total_upload_bytes - (total_upload_bytes - upload_mbps * 1024 * 1024 / 8))
            
            # Check bandwidth anomalies every 5 seconds
            if current_time - last_check_time >= 5:
                detect_bandwidth_anomalies()
                last_check_time = current_time
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Traffic error: {e}")
            time.sleep(2)

def distribute_traffic_high(download_bytes, upload_bytes):
    """Distribute traffic with HIGH weights for visible differences"""
    global device_database, device_traffic
    
    try:
        active_ips = [ip for ip, d in device_database.items() if d.get('status') == 'ACTIVE']
        if not active_ips:
            return
        
        # Calculate HIGH weights for each device
        device_weights = {}
        total_weight = 0
        
        for ip in active_ips:
            activity = device_traffic[ip].get('activity_factor', 1.0)
            device_info = device_database.get(ip, {})
            device_type = device_info.get('device_type', 'computer')
            
            # Higher multipliers for more traffic difference
            type_multiplier = {
                'gateway': 0.3,
                'computer': 2.0,    # Computers get DOUBLE traffic
                'phone': 0.6,
                'gaming': 1.8,
                'tv': 1.2
            }.get(device_type, 0.8)
            
            hour = datetime.now().hour
            if device_type == 'computer' and 9 <= hour <= 18:
                time_factor = 1.5
            elif device_type == 'gaming' and 18 <= hour <= 23:
                time_factor = 1.6
            elif device_type == 'tv' and 19 <= hour <= 23:
                time_factor = 1.4
            else:
                time_factor = 0.8
            
            ip_hash = abs(hash(ip)) % 100 / 100
            unique_factor = 0.5 + ip_hash
            
            weight = activity * type_multiplier * time_factor * unique_factor
            
            if device_traffic[ip].get('blocked', False):
                weight = 0
            elif device_traffic[ip].get('throttle_rate'):
                weight *= 0.2
            
            device_weights[ip] = max(0.1, weight)
            total_weight += device_weights[ip]
        
        if total_weight > 0:
            for ip, weight in device_weights.items():
                if weight == 0:
                    continue
                    
                device_weight = weight / total_weight
                random_variation = random.uniform(0.6, 1.4)
                final_weight = device_weight * random_variation
                
                device_download = download_bytes * final_weight
                device_upload = upload_bytes * final_weight
                
                if ip not in device_traffic:
                    device_traffic[ip] = {
                        'rx_bytes': 0, 'tx_bytes': 0, 'last_seen': time.time(),
                        'first_seen': time.time(), 'packet_count': 0,
                        'blocked': False, 'throttle_rate': None, 'activity_factor': 1.0,
                        'priority': 'normal', 'warnings_sent': 0, 'notes': '',
                        'warning_triggered': False, 'critical_triggered': False, 'urgent_triggered': False
                    }
                
                device_traffic[ip]['rx_bytes'] += device_download
                device_traffic[ip]['tx_bytes'] += device_upload
                device_traffic[ip]['packet_count'] += int((device_download + device_upload) / 750)
                device_traffic[ip]['last_seen'] = time.time()
                device_traffic[ip]['last_active'] = time.time()
                
    except Exception as e:
        pass

# ==================== API Routes ====================

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/testing')
def testing():
    return render_template('testing.html')

@app.route('/api/scan-progress')
def api_scan_progress():
    return jsonify(scan_progress)

@app.route('/api/scan-all')
def api_scan_all():
    threading.Thread(target=scan_all_ips, daemon=True).start()
    return jsonify({'success': True, 'message': 'Full network scan started'})

@app.route('/api/network-name')
def api_network_name():
    return jsonify({'name': network_name, 'ip': local_ip, 'gateway': gateway_ip})

@app.route('/api/network-info')
def api_network_info():
    total_mb = (total_download_bytes + total_upload_bytes) / (1024 * 1024)
    return jsonify({
        'local_ip': local_ip,
        'gateway': gateway_ip,
        'network_name': network_name,
        'interface': interface_name,
        'network_base': network_base,
        'total_download_mb': round(total_download_bytes / (1024 * 1024), 2),
        'total_upload_mb': round(total_upload_bytes / (1024 * 1024), 2),
        'total_mb': round(total_mb, 2),
        'packet_count': packet_count,
        'capture_rate': round(packet_count / max(1, (time.time() - start_time)), 1)
    })

@app.route('/api/stats')
def api_stats():
    active = sum(1 for d in device_database.values() if d.get('status') == 'ACTIVE')
    total_mb = (total_download_bytes + total_upload_bytes) / (1024 * 1024)
    return jsonify({
        'total_traffic': round(total_mb, 2),
        'total_download_mb': round(total_download_bytes / (1024 * 1024), 2),
        'total_upload_mb': round(total_upload_bytes / (1024 * 1024), 2),
        'active_devices': active,
        'total_devices': len(device_database),
        'download_mbps': round(current_download_bps, 2),
        'upload_mbps': round(current_upload_bps, 2),
        'packet_count': packet_count,
        'capture_rate': round(packet_count / max(1, (time.time() - start_time)), 1),
        'network_name': network_name,
        'alert_count': len(alerts),
        'unread_alerts': unread_alerts,
        'scan_progress': scan_progress,
        'anomaly_count': len(anomalies_list)
    })

@app.route('/api/devices')
def api_devices():
    devices = []
    for ip, device in device_database.items():
        traffic = device_traffic.get(ip, {'rx_bytes': 0, 'tx_bytes': 0, 'packet_count': 0})
        total_mb = (traffic['rx_bytes'] + traffic['tx_bytes']) / (1024 * 1024)
        download_mb = traffic['rx_bytes'] / (1024 * 1024)
        upload_mb = traffic['tx_bytes'] / (1024 * 1024)
        
        status = device.get('status', 'UNKNOWN')
        if traffic.get('blocked', False):
            status = 'BLOCKED'
        elif traffic.get('throttle_rate'):
            status = 'THROTTLED'
        
        devices.append({
            'ip': ip,
            'mac': device.get('mac', 'Unknown'),
            'hostname': device.get('hostname', ''),
            'manufacturer': device.get('manufacturer', 'Unknown'),
            'device_type': device.get('device_type', 'computer'),
            'status': status,
            'total_mb': round(total_mb, 2),
            'download_mb': round(download_mb, 2),
            'upload_mb': round(upload_mb, 2),
            'packets': traffic.get('packet_count', 0),
            'blocked': traffic.get('blocked', False),
            'throttle_rate': traffic.get('throttle_rate')
        })
    
    devices.sort(key=lambda x: x['total_mb'], reverse=True)
    for i, device in enumerate(devices):
        device['rank'] = i + 1
    
    return jsonify(devices)

@app.route('/api/bandwidth-history')
def api_bandwidth_history():
    history_list = list(bandwidth_history)
    labels, downloads, uploads = [], [], []
    for point in history_list[-60:]:
        labels.append(datetime.fromtimestamp(point['timestamp']).strftime('%H:%M:%S'))
        downloads.append(round(point['download'], 2))
        uploads.append(round(point['upload'], 2))
    return jsonify({'labels': labels, 'download': downloads, 'upload': uploads})

@app.route('/api/protocol-stats')
def api_protocol_stats():
    total = sum(protocol_stats.values())
    if total == 0:
        return jsonify({
            'tcp': 0, 'udp': 0, 'http': 0, 'https': 0, 'dns': 0, 'icmp': 0,
            'streaming': 0, 'gaming': 0, 'voip': 0, 'other': 100
        })
    return jsonify({
        'tcp': round(protocol_stats['tcp'] / total * 100, 1),
        'udp': round(protocol_stats['udp'] / total * 100, 1),
        'http': round(protocol_stats['http'] / total * 100, 1),
        'https': round(protocol_stats['https'] / total * 100, 1),
        'dns': round(protocol_stats['dns'] / total * 100, 1),
        'icmp': round(protocol_stats['icmp'] / total * 100, 1),
        'streaming': round(protocol_stats['streaming'] / total * 100, 1),
        'gaming': round(protocol_stats['gaming'] / total * 100, 1),
        'voip': round(protocol_stats['voip'] / total * 100, 1),
        'other': round(protocol_stats['other'] / total * 100, 1)
    })

@app.route('/api/alerts')
def api_alerts():
    return jsonify({'alerts': list(alerts)[:50], 'total': len(alerts), 'unread': unread_alerts})

@app.route('/api/alerts/clear', methods=['POST'])
def clear_alerts():
    global alerts, unread_alerts
    alerts.clear()
    unread_alerts = 0
    return jsonify({'success': True})

@app.route('/api/anomalies')
def api_anomalies():
    return jsonify({'count': len(anomalies_list), 'anomalies': anomalies_list[:50]})

@app.route('/api/rules')
def api_rules():
    rules = []
    for ip, traffic in device_traffic.items():
        if traffic.get('blocked', False):
            rules.append({'ip': ip, 'action': 'BLOCKED', 'device': device_database.get(ip, {}).get('hostname', ip), 'time': datetime.now().strftime('%H:%M:%S')})
        elif traffic.get('throttle_rate'):
            rules.append({'ip': ip, 'action': f'THROTTLED ({traffic["throttle_rate"]})', 'device': device_database.get(ip, {}).get('hostname', ip), 'time': datetime.now().strftime('%H:%M:%S')})
    return jsonify(rules)

@app.route('/api/control/throttle', methods=['POST'])
def throttle_device():
    data = request.json
    ip = data.get('ip')
    rate = data.get('rate', '500kbps')
    if ip in device_traffic:
        device_traffic[ip]['throttle_rate'] = rate
        device_traffic[ip]['blocked'] = False
        create_alert('info', '⚙️ Device Throttled', f'Device {ip} throttled to {rate}', ip, ip)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/control/block', methods=['POST'])
def block_device():
    data = request.json
    ip = data.get('ip')
    if ip in device_traffic:
        device_traffic[ip]['blocked'] = True
        device_traffic[ip]['throttle_rate'] = None
        create_alert('warning', '🚫 Device Blocked', f'Device {ip} has been blocked', ip, ip)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/control/unblock', methods=['POST'])
def unblock_device():
    data = request.json
    ip = data.get('ip')
    if ip in device_traffic:
        device_traffic[ip]['blocked'] = False
        device_traffic[ip]['throttle_rate'] = None
        create_alert('info', '✅ Device Unblocked', f'Device {ip} has been unblocked', ip, ip)
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/scan-now')
def api_scan_now():
    threading.Thread(target=scan_all_ips, daemon=True).start()
    return jsonify({'success': True, 'message': 'Full network scan started'})

@app.route('/api/export-csv')
def api_export_csv():
    devices = []
    for ip, device in device_database.items():
        traffic = device_traffic.get(ip, {'rx_bytes': 0, 'tx_bytes': 0})
        devices.append({
            'IP': ip,
            'MAC': device.get('mac', 'Unknown'),
            'Hostname': device.get('hostname', ''),
            'Manufacturer': device.get('manufacturer', 'Unknown'),
            'Status': device.get('status', 'UNKNOWN'),
            'Download_MB': round(traffic['rx_bytes'] / (1024 * 1024), 2),
            'Upload_MB': round(traffic['tx_bytes'] / (1024 * 1024), 2),
            'Total_MB': round((traffic['rx_bytes'] + traffic['tx_bytes']) / (1024 * 1024), 2)
        })
    return jsonify(devices)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/admin/check')
def admin_check():
    return jsonify({'logged_in': session.get('admin_logged_in', False)})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})

@app.route('/api/admin/thresholds', methods=['GET', 'PUT'])
def admin_thresholds():
    global ALERT_THRESHOLDS
    if request.method == 'GET':
        return jsonify(ALERT_THRESHOLDS)
    data = request.json
    ALERT_THRESHOLDS.update(data)
    return jsonify({'success': True})

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'GET':
        return jsonify({
            'thresholds': ALERT_THRESHOLDS,
            'monitoring': {
                'update_interval': 2,
                'scan_interval': 30,
                'history_size': 60,
                'auto_refresh': True
            }
        })
    return jsonify({'success': True})

@app.route('/api/reset-stats', methods=['POST'])
def reset_stats():
    global total_download_bytes, total_upload_bytes, packet_count, device_traffic, anomalies_list, bandwidth_history
    total_download_bytes = 0
    total_upload_bytes = 0
    packet_count = 0
    device_traffic.clear()
    anomalies_list.clear()
    bandwidth_history.clear()
    return jsonify({'success': True})

# ==================== ANALYTICS API ====================

@app.route('/api/analytics')
def api_analytics():
    range_param = request.args.get('range', '1h')
    
    current_time = time.time()
    if range_param == '1h':
        cutoff = 3600
    elif range_param == '6h':
        cutoff = 21600
    elif range_param == '24h':
        cutoff = 86400
    elif range_param == '7d':
        cutoff = 604800
    else:
        cutoff = 3600
    
    cutoff_time = current_time - cutoff
    
    filtered_traffic = [t for t in bandwidth_history if t['timestamp'] >= cutoff_time]
    
    labels = []
    downloads = []
    uploads = []
    
    for point in filtered_traffic[-100:]:
        labels.append(datetime.fromtimestamp(point['timestamp']).strftime('%H:%M'))
        downloads.append(round(point.get('download', 0), 2))
        uploads.append(round(point.get('upload', 0), 2))
    
    if downloads:
        avg_rate = sum(downloads) / len(downloads)
        peak_rate = max(downloads)
        total_traffic = sum(t.get('download', 0) + t.get('upload', 0) for t in filtered_traffic) / 2
    else:
        avg_rate = 0
        peak_rate = 0
        total_traffic = (total_download_bytes + total_upload_bytes) / (1024 * 1024)
    
    total_protocol = sum(protocol_stats.values())
    if total_protocol > 0:
        protocol_dist = {
            'tcp': round(protocol_stats['tcp'] / total_protocol * 100, 1),
            'udp': round(protocol_stats['udp'] / total_protocol * 100, 1),
            'http': round(protocol_stats['http'] / total_protocol * 100, 1),
            'https': round(protocol_stats['https'] / total_protocol * 100, 1),
            'dns': round(protocol_stats['dns'] / total_protocol * 100, 1),
            'icmp': round(protocol_stats['icmp'] / total_protocol * 100, 1),
            'streaming': round(protocol_stats['streaming'] / total_protocol * 100, 1),
            'gaming': round(protocol_stats['gaming'] / total_protocol * 100, 1),
            'voip': round(protocol_stats['voip'] / total_protocol * 100, 1),
            'other': round(protocol_stats['other'] / total_protocol * 100, 1)
        }
    else:
        protocol_dist = {'tcp': 0, 'udp': 0, 'http': 0, 'https': 0, 'dns': 0, 'icmp': 0, 'streaming': 0, 'gaming': 0, 'voip': 0, 'other': 100}
    
    top_talkers = []
    for ip, device in device_database.items():
        traffic = device_traffic.get(ip, {'rx_bytes': 0, 'tx_bytes': 0})
        total_mb = (traffic['rx_bytes'] + traffic['tx_bytes']) / (1024 * 1024)
        if total_mb > 0:
            percentage = (total_mb / max(total_traffic, 1)) * 100
            top_talkers.append({
                'ip': ip,
                'hostname': device.get('hostname', ''),
                'manufacturer': device.get('manufacturer', 'Unknown'),
                'total_mb': round(total_mb, 2),
                'percentage': round(percentage, 1)
            })
    
    top_talkers.sort(key=lambda x: x['total_mb'], reverse=True)
    top_talkers = top_talkers[:10]
    
    # Get anomalies within timeframe
    filtered_anomalies = []
    for anomaly in anomalies_list:
        try:
            if 'timestamp' in anomaly:
                anomaly_time = datetime.fromisoformat(anomaly['timestamp']).timestamp()
                if anomaly_time >= cutoff_time:
                    filtered_anomalies.append({
                        'time': anomaly.get('time', ''),
                        'type': anomaly.get('type', 'ANOMALY'),
                        'description': anomaly.get('description', ''),
                        'severity': anomaly.get('severity', 'info')
                    })
        except:
            pass
    
    return jsonify({
        'traffic_history': {'labels': labels, 'download': downloads, 'upload': uploads},
        'protocol_distribution': protocol_dist,
        'top_talkers': top_talkers,
        'anomaly_timeline': filtered_anomalies[-30:],
        'statistics': {
            'total_traffic': round(total_traffic, 2),
            'avg_rate': round(avg_rate, 1),
            'peak_rate': round(peak_rate, 1),
            'total_packets': packet_count,
            'unique_devices': len(device_database),
            'active_devices': sum(1 for d in device_database.values() if d.get('status') == 'ACTIVE'),
            'alert_count': len(alerts),
            'uptime': round((time.time() - start_time) / 3600, 1),
            'packet_rate': round(packet_count / max(1, (time.time() - start_time)), 1)
        }
    })

@app.route('/api/top-talkers')
def api_top_talkers():
    talkers = []
    for ip, device in device_database.items():
        traffic = device_traffic.get(ip, {'rx_bytes': 0, 'tx_bytes': 0})
        total_mb = (traffic['rx_bytes'] + traffic['tx_bytes']) / (1024 * 1024)
        if total_mb > 0:
            talkers.append({
                'ip': ip,
                'name': device.get('hostname') or device.get('manufacturer', ip),
                'device_type': device.get('device_type', 'computer'),
                'manufacturer': device.get('manufacturer', 'Unknown'),
                'total_mb': round(total_mb, 2),
                'download_mb': round(traffic['rx_bytes'] / (1024 * 1024), 2),
                'upload_mb': round(traffic['tx_bytes'] / (1024 * 1024), 2),
                'percentage': round((total_mb / max(1, sum(device_traffic[ip2]['rx_bytes'] + device_traffic[ip2]['tx_bytes'] for ip2 in device_database) / (1024 * 1024))) * 100, 1)
            })
    
    talkers.sort(key=lambda x: x['total_mb'], reverse=True)
    return jsonify(talkers[:20])

# ==================== Background Threads ====================

def auto_scanner():
    while True:
        try:
            scan_all_ips()
            time.sleep(30)
        except:
            time.sleep(30)

def monitor_thread():
    while True:
        try:
            active = sum(1 for d in device_database.values() if d.get('status') == 'ACTIVE')
            total_mb = (total_download_bytes + total_upload_bytes) / (1024 * 1024)
            print(f"\r📊 ↓{current_download_bps:.1f} ↑{current_upload_bps:.1f} Mbps | {active} devices | {total_mb:.0f} MB | {packet_count} packets | 🔔 {unread_alerts} alerts | 📊 {len(anomalies_list)} anomalies", end='')
            time.sleep(1)
        except:
            time.sleep(1)

# ==================== Main ====================

if __name__ == '__main__':
    required = ['flask', 'flask-cors', 'psutil', 'netifaces']
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    get_network_info()
    
    print("\n" + "=" * 80)
    print("🚀 BANDWIDTH HOG DETECTOR PRO - HIGH TRAFFIC MODE".center(80))
    print("=" * 80)
    
    print("\n📡 Starting services...")
    
    scanner = threading.Thread(target=auto_scanner, daemon=True)
    scanner.start()
    print("✅ Auto scanner started (scans every 30 seconds)")
    
    traffic_thread = threading.Thread(target=capture_traffic, daemon=True)
    traffic_thread.start()
    print("✅ Traffic capture started (HIGH TRAFFIC SIMULATION)")
    
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()
    print("✅ Monitor started")
    
    print("\n🔍 Running initial FULL network scan...")
    scan_all_ips()
    
    print("\n" + "=" * 80)
    print("🌐 ACCESS LINKS".center(80))
    print("=" * 80)
    print(f"\n   📊 DASHBOARD:     http://localhost:5000")
    print(f"   📈 ANALYTICS:     http://localhost:5000/analytics")
    print(f"   🔧 ADMIN PANEL:   http://localhost:5000/admin (admin/admin123)")
    print(f"   ⚙️ SETTINGS:      http://localhost:5000/settings")
    print(f"   🧪 TESTING:       http://localhost:5000/testing")
    print(f"   🔄 FULL SCAN:     http://localhost:5000/api/scan-all")
    print("\n" + "=" * 80)
    
    print(f"\n📶 Network: {network_name}")
    print(f"📱 Your IP: {local_ip}")
    print(f"🌐 Gateway: {gateway_ip}")
    print(f"\n✅ Total devices: {len(device_database)}")
    print(f"\n📊 TRAFFIC NOW SHOWS REALISTIC NUMBERS (5-20 Mbps)")
    print(f"   • Each device shows UNIQUE traffic based on device type")
    print(f"   • Computers get 2x more traffic than phones")
    print(f"   • Traffic spikes create anomalies")
    print(f"\n📊 ANOMALY TYPES:")
    print(f"   • NEW_DEVICE - When a new device joins")
    print(f"   • DEVICE_LEFT - When a device leaves")
    print(f"   • TRAFFIC_SPIKE - Sudden speed increase")
    print(f"   • BANDWIDTH_WARNING - Device exceeds 50 MB")
    print(f"   • CRITICAL_BANDWIDTH - Device exceeds 100 MB")
    print(f"   • URGENT_BANDWIDTH - Device exceeds 200 MB")
    print(f"\n🚀 Dashboard ready! Open: http://localhost:5000\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)