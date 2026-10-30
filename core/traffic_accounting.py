#!/usr/bin/env python3
"""
Traffic Accounting Module
Tracks bandwidth usage per device
"""

import time
from collections import defaultdict, deque
import threading

class TrafficAccounting:
    """
    Tracks and analyzes bandwidth usage per IP
    """
    
    def __init__(self, history_size=3600):
        self.traffic_data = {}
        self.history = defaultdict(lambda: deque(maxlen=60))
        self.lock = threading.Lock()
        self.history_size = history_size
        self.packet_count = 0
        self.last_print = time.time()
        print("✅ TrafficAccounting initialized")
        
    def process_packet(self, packet):
        """Process a packet and update accounting"""
        self.packet_count += 1
        
        # Print every 10 packets to show activity
        if self.packet_count % 10 == 0:
            now = time.time()
            if now - self.last_print > 2:
                print(f"📊 Accounting: Received packet #{self.packet_count}")
                print(f"   Packet details: {packet.get('src_ip')} -> {packet.get('dst_ip')} ({packet.get('size')} bytes)")
                self.last_print = now
        
        with self.lock:
            src_ip = packet['src_ip']
            dst_ip = packet['dst_ip']
            size = packet['size']
            protocol = packet.get('protocol', 'UNKNOWN')
            
            # Skip localhost
            if src_ip.startswith('127.') or dst_ip.startswith('127.'):
                return
                
            # Initialize if new IP
            if src_ip not in self.traffic_data:
                self.traffic_data[src_ip] = {
                    'bytes_sent': 0,
                    'bytes_recv': 0,
                    'packets_sent': 0,
                    'packets_recv': 0,
                    'tcp_sent': 0,
                    'udp_sent': 0,
                    'icmp_sent': 0,
                    'tcp_recv': 0,
                    'udp_recv': 0,
                    'icmp_recv': 0,
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'total_bytes': 0
                }
                print(f"   ➕ New device detected: {src_ip}")
                
            if dst_ip not in self.traffic_data:
                self.traffic_data[dst_ip] = {
                    'bytes_sent': 0,
                    'bytes_recv': 0,
                    'packets_sent': 0,
                    'packets_recv': 0,
                    'tcp_sent': 0,
                    'udp_sent': 0,
                    'icmp_sent': 0,
                    'tcp_recv': 0,
                    'udp_recv': 0,
                    'icmp_recv': 0,
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'total_bytes': 0
                }
                print(f"   ➕ New device detected: {dst_ip}")
                
            # Update source stats
            src = self.traffic_data[src_ip]
            src['bytes_sent'] += size
            src['packets_sent'] += 1
            src['last_seen'] = time.time()
            src['total_bytes'] = src['bytes_sent'] + src['bytes_recv']
            
            if protocol == 'TCP':
                src['tcp_sent'] += 1
            elif protocol == 'UDP':
                src['udp_sent'] += 1
            elif protocol == 'ICMP':
                src['icmp_sent'] += 1
                
            # Update destination stats
            dst = self.traffic_data[dst_ip]
            dst['bytes_recv'] += size
            dst['packets_recv'] += 1
            dst['last_seen'] = time.time()
            dst['total_bytes'] = dst['bytes_sent'] + dst['bytes_recv']
            
            if protocol == 'TCP':
                dst['tcp_recv'] += 1
            elif protocol == 'UDP':
                dst['udp_recv'] += 1
            elif protocol == 'ICMP':
                dst['icmp_recv'] += 1
                
            # Update history
            self.history[src_ip].append({
                'timestamp': time.time(),
                'bytes': size,
                'type': 'sent'
            })
            self.history[dst_ip].append({
                'timestamp': time.time(),
                'bytes': size,
                'type': 'recv'
            })
            
    def get_top_consumers(self, n=10):
        """Get top N bandwidth consumers"""
        with self.lock:
            consumers = []
            device_count = len(self.traffic_data)
            
            if device_count > 0:
                print(f"🔍 Getting top consumers from {device_count} devices")
            
            for ip, data in self.traffic_data.items():
                if data['total_bytes'] > 0:
                    consumers.append({
                        'ip': ip,
                        'total_bytes': data['total_bytes'],
                        'total_mb': data['total_bytes'] / (1024 * 1024),
                        'sent_mb': data['bytes_sent'] / (1024 * 1024),
                        'recv_mb': data['bytes_recv'] / (1024 * 1024),
                        'packets': data['packets_sent'] + data['packets_recv'],
                        'packets_sent': data['packets_sent'],
                        'packets_recv': data['packets_recv'],
                        'tcp_sent': data['tcp_sent'],
                        'udp_sent': data['udp_sent'],
                        'icmp_sent': data['icmp_sent'],
                        'tcp_recv': data['tcp_recv'],
                        'udp_recv': data['udp_recv'],
                        'icmp_recv': data['icmp_recv'],
                        'first_seen': data['first_seen'],
                        'last_seen': data['last_seen']
                    })
            
            result = sorted(consumers, key=lambda x: x['total_bytes'], reverse=True)[:n]
            
            if result:
                print(f"   Found {len(result)} consumers with data")
                for i, device in enumerate(result[:3], 1):
                    print(f"      {i}. {device['ip']}: {device['total_mb']:.2f} MB")
            else:
                print(f"   No consumers found - traffic_data has {device_count} devices but all have 0 bytes")
                
            return result
            
    def get_device_history(self, ip, minutes=5):
        """Get traffic history for a specific device"""
        with self.lock:
            if ip in self.history:
                now = time.time()
                return [
                    h for h in self.history[ip]
                    if now - h['timestamp'] <= minutes * 60
                ]
            return []
            
    def get_active_devices(self, timeout=300):
        """Get devices active in the last timeout seconds"""
        with self.lock:
            now = time.time()
            active = [
                ip for ip, data in self.traffic_data.items()
                if now - data['last_seen'] <= timeout
            ]
            if active:
                print(f"   Active devices: {len(active)}")
            return active
            
    def get_total_traffic(self):
        """Get total traffic statistics"""
        with self.lock:
            total_bytes = sum(d['total_bytes'] for d in self.traffic_data.values())
            active = len(self.get_active_devices())
            total = len(self.traffic_data)
            
            print(f"📈 Total traffic: {total_bytes/(1024*1024):.2f} MB, Active: {active}, Total devices: {total}")
            
            return {
                'total_bytes': total_bytes,
                'total_mb': total_bytes / (1024 * 1024),
                'active_devices': active,
                'total_devices': total
            }
            
    def reset(self):
        """Reset all accounting data"""
        with self.lock:
            self.traffic_data.clear()
            self.history.clear()
            self.packet_count = 0
            print("🔄 Accounting data reset")