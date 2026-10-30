#!/usr/bin/env python3
"""
Anomaly Detection Module
Detects unusual network behavior
"""

import time
import statistics
from collections import defaultdict, deque
import threading

class AnomalyDetector:
    """
    Detects network anomalies like bandwidth spikes, connection floods
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.baselines = defaultdict(lambda: deque(maxlen=60))
        self.anomalies = deque(maxlen=100)
        self.lock = threading.Lock()
        
        # Thresholds
        self.bandwidth_threshold = self.config.get('bandwidth_spike_threshold', 2.5)
        self.packet_threshold = self.config.get('packet_flood_threshold', 1000)
        self.connection_threshold = self.config.get('connection_threshold', 100)
        
    def analyze_packet(self, packet):
        """Analyze a single packet for anomalies"""
        anomalies = []
        
        # Check for oversized packets
        if packet['size'] > 65535:
            anomalies.append({
                'type': 'OVERSIZED_PACKET',
                'severity': 'MEDIUM',
                'ip': packet['src_ip'],
                'details': f"Packet size: {packet['size']} bytes",
                'timestamp': time.time()
            })
            
        # Check for suspicious ports
        suspicious_ports = [22, 23, 3389, 445, 1433]
        if 'dport' in packet and packet['dport'] in suspicious_ports:
            anomalies.append({
                'type': 'SUSPICIOUS_PORT',
                'severity': 'HIGH',
                'ip': packet['src_ip'],
                'details': f"Connection to port {packet['dport']}",
                'timestamp': time.time()
            })
            
        return anomalies
        
    def analyze_traffic(self, traffic_data, accounting):
        """Analyze aggregated traffic for anomalies"""
        anomalies = []
        now = time.time()
        
        for device in traffic_data:
            ip = device['ip']
            
            # Update baseline
            with self.lock:
                self.baselines[ip].append({
                    'timestamp': now,
                    'bytes': device['total_bytes'],
                    'packets': device['packets']
                })
                
            # Check for bandwidth spike
            if self._is_bandwidth_spike(ip):
                anomalies.append({
                    'type': 'BANDWIDTH_SPIKE',
                    'severity': 'HIGH',
                    'ip': ip,
                    'details': f"Unusual bandwidth usage detected",
                    'timestamp': now
                })
                
            # Check for packet flood
            if self._is_packet_flood(ip):
                anomalies.append({
                    'type': 'PACKET_FLOOD',
                    'severity': 'CRITICAL',
                    'ip': ip,
                    'details': f"High packet rate detected",
                    'timestamp': now
                })
                
            # Check for protocol imbalance
            if self._check_protocol_imbalance(device):
                anomalies.append({
                    'type': 'PROTOCOL_IMBALANCE',
                    'severity': 'LOW',
                    'ip': ip,
                    'details': f"Unusual protocol distribution",
                    'timestamp': now
                })
                
        # Record anomalies
        for anomaly in anomalies:
            with self.lock:
                self.anomalies.append(anomaly)
                
        return anomalies
        
    def _is_bandwidth_spike(self, ip):
        """Check if bandwidth usage is anomalous"""
        with self.lock:
            if ip not in self.baselines or len(self.baselines[ip]) < 5:
                return False
                
            values = [b['bytes'] for b in self.baselines[ip]]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 1
            
            latest = values[-1]
            return abs(latest - mean) > self.bandwidth_threshold * stdev
            
    def _is_packet_flood(self, ip):
        """Check for packet flood"""
        with self.lock:
            if ip not in self.baselines or len(self.baselines[ip]) < 5:
                return False
                
            recent = list(self.baselines[ip])[-5:]
            packet_rate = sum(p['packets'] for p in recent) / len(recent)
            
            return packet_rate > self.packet_threshold
            
    def _check_protocol_imbalance(self, device):
        """Check for unusual protocol distribution"""
        total = device['packets']
        if total < 100:
            return False
            
        tcp_ratio = (device['tcp_sent'] + device['tcp_recv']) / total
        udp_ratio = (device['udp_sent'] + device['udp_recv']) / total
        
        # Flag if >95% of traffic is one protocol
        return tcp_ratio > 0.95 or udp_ratio > 0.95
        
    def get_recent_anomalies(self, limit=10):
        """Get recent anomalies"""
        with self.lock:
            return list(self.anomalies)[-limit:]
            
    def get_anomaly_stats(self):
        """Get anomaly statistics"""
        with self.lock:
            return {
                'total': len(self.anomalies),
                'by_severity': {
                    'LOW': sum(1 for a in self.anomalies if a['severity'] == 'LOW'),
                    'MEDIUM': sum(1 for a in self.anomalies if a['severity'] == 'MEDIUM'),
                    'HIGH': sum(1 for a in self.anomalies if a['severity'] == 'HIGH'),
                    'CRITICAL': sum(1 for a in self.anomalies if a['severity'] == 'CRITICAL')
                }
            }