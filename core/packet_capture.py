#!/usr/bin/env python3
"""
Packet Capture Module
Captures network packets using Scapy
"""

import time
import threading
from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP, ICMP
import psutil

class PacketCapture:
    """
    Network packet capture engine
    Handles low-level packet capture and filtering
    """
    
    def __init__(self, interface="Wi-Fi", promiscuous=True):
        self.interface = interface
        self.promiscuous = promiscuous
        self.running = False
        self.packet_count = 0
        self.packet_queue = []
        self.lock = threading.Lock()
        self.callbacks = []
        self.stats = {
            'total_bytes': 0,
            'total_packets': 0,
            'tcp_packets': 0,
            'udp_packets': 0,
            'icmp_packets': 0,
            'other_packets': 0,
            'start_time': time.time()
        }
        
    def register_callback(self, callback):
        """Register a callback for packet processing"""
        self.callbacks.append(callback)
        
    def packet_handler(self, packet):
        """Process each captured packet"""
        try:
            if IP in packet:
                ip_layer = packet[IP]
                packet_info = {
                    'src_ip': ip_layer.src,
                    'dst_ip': ip_layer.dst,
                    'size': len(packet),
                    'protocol': self._get_protocol(packet),
                    'timestamp': time.time(),
                    'raw_packet': packet
                }
                
                # Update stats
                with self.lock:
                    self.stats['total_bytes'] += packet_info['size']
                    self.stats['total_packets'] += 1
                    
                    if TCP in packet:
                        self.stats['tcp_packets'] += 1
                        packet_info['sport'] = packet[TCP].sport
                        packet_info['dport'] = packet[TCP].dport
                    elif UDP in packet:
                        self.stats['udp_packets'] += 1
                        packet_info['sport'] = packet[UDP].sport
                        packet_info['dport'] = packet[UDP].dport
                    elif ICMP in packet:
                        self.stats['icmp_packets'] += 1
                    else:
                        self.stats['other_packets'] += 1
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(packet_info)
                    except Exception:
                        pass
                        
        except Exception:
            pass
            
    def _get_protocol(self, packet):
        """Determine packet protocol"""
        if TCP in packet:
            return 'TCP'
        elif UDP in packet:
            return 'UDP'
        elif ICMP in packet:
            return 'ICMP'
        else:
            return 'OTHER'
            
    def start_capture(self):
        """Start packet capture"""
        self.running = True
        print(f"📡 Starting packet capture on {self.interface}...")
        
        def capture_loop():
            try:
                sniff(
                    iface=self.interface,
                    prn=self.packet_handler,
                    store=0,
                    promisc=self.promiscuous,
                    stop_filter=lambda x: not self.running
                )
            except Exception as e:
                print(f"❌ Capture error: {e}")
                print("   Make sure Npcap/WinPcap is installed!")
                
        self.capture_thread = threading.Thread(target=capture_loop, daemon=True)
        self.capture_thread.start()
        print(f"✅ Capture thread started")
        
    def stop(self):
        """Stop packet capture"""
        self.running = False
        print("🛑 Stopping packet capture...")
        
    def get_stats(self):
        """Get capture statistics"""
        with self.lock:
            elapsed = time.time() - self.stats['start_time']
            return {
                'total_bytes': self.stats['total_bytes'],
                'total_mb': self.stats['total_bytes'] / (1024 * 1024),
                'total_packets': self.stats['total_packets'],
                'tcp_packets': self.stats['tcp_packets'],
                'udp_packets': self.stats['udp_packets'],
                'icmp_packets': self.stats['icmp_packets'],
                'other_packets': self.stats['other_packets'],
                'packets_per_second': self.stats['total_packets'] / elapsed if elapsed > 0 else 0,
                'mbps': (self.stats['total_bytes'] * 8) / (elapsed * 1024 * 1024) if elapsed > 0 else 0,
                'elapsed': elapsed
            }
            
    def reset_stats(self):
        """Reset statistics"""
        with self.lock:
            self.stats = {
                'total_bytes': 0,
                'total_packets': 0,
                'tcp_packets': 0,
                'udp_packets': 0,
                'icmp_packets': 0,
                'other_packets': 0,
                'start_time': time.time()
            }