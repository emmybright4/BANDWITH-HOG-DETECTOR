#!/usr/bin/env python3
"""
Network Traffic Manager
Coordinates all network traffic modules
"""

import time
import threading
from .packet_capture import PacketCapture
from .traffic_accounting import TrafficAccounting
from .anomaly_detection import AnomalyDetector
from .control_module import ControlModule

class NetworkTrafficManager:
    """
    Central manager for all network traffic operations
    """
    
    def __init__(self, config):
        self.config = config
        self.running = False
        self.interface = config.get('interface', 'Wi-Fi')
        self.packet_count = 0
        self.last_print = time.time()
        
        print(f"\n🔧 Initializing NetworkTrafficManager on {self.interface}...")
        
        # Initialize modules
        print("   Creating PacketCapture...")
        self.capture = PacketCapture(
            interface=self.interface,
            promiscuous=config.get('promiscuous', True)
        )
        
        print("   Creating TrafficAccounting...")
        self.accounting = TrafficAccounting()
        
        print("   Creating AnomalyDetector...")
        self.anomaly_detector = AnomalyDetector(config.get('anomaly_detection', {}))
        
        print("   Creating ControlModule...")
        self.control = ControlModule()
        
        # Statistics
        self.stats = {
            'start_time': time.time(),
            'updates': 0,
            'packets_processed': 0
        }
        
        # Register callbacks
        print("   Registering packet callback...")
        self.capture.register_callback(self._on_packet)
        print("✅ Callback registered")
        
    def _on_packet(self, packet):
        """Handle captured packet"""
        try:
            # Count packets
            self.packet_count += 1
            self.stats['packets_processed'] += 1
            
            # Print every 10 packets to show activity
            if self.packet_count % 10 == 0:
                now = time.time()
                if now - self.last_print > 2:  # Don't spam too much
                    print(f"📦 Received {self.packet_count} packets so far")
                    self.last_print = now
            
            # Update accounting
            self.accounting.process_packet(packet)
            
            # Check for anomalies
            anomalies = self.anomaly_detector.analyze_packet(packet)
            if anomalies:
                self.stats['last_anomaly'] = time.time()
                print(f"⚠️ Anomaly detected: {anomalies}")
                
        except Exception as e:
            print(f"❌ Error in _on_packet: {e}")
            
    def start(self):
        """Start all monitoring"""
        print(f"\n🚀 Starting Network Traffic Manager on {self.interface}...")
        self.running = True
        
        # Start capture
        self.capture.start_capture()
        
        # Start analysis thread
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        print("✅ Analysis thread started")
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print("✅ Cleanup thread started")
        
        print(f"✅ Network Traffic Manager started on {self.interface}")
        
    def _analysis_loop(self):
        """Periodic analysis thread"""
        while self.running:
            try:
                time.sleep(5)
                
                # Get top consumers
                top_consumers = self.accounting.get_top_consumers(20)
                
                # Print status
                traffic_stats = self.accounting.get_total_traffic()
                print(f"\n📊 Analysis Update:")
                print(f"   Packets processed: {self.stats['packets_processed']}")
                print(f"   Total traffic: {traffic_stats['total_mb']:.2f} MB")
                print(f"   Active devices: {traffic_stats['active_devices']}")
                
                if top_consumers:
                    print(f"   Top devices:")
                    for i, device in enumerate(top_consumers[:3], 1):
                        print(f"      {i}. {device['ip']}: {device['total_mb']:.2f} MB")
                else:
                    print(f"   No devices found yet - waiting for traffic...")
                
                # Analyze for anomalies
                anomalies = self.anomaly_detector.analyze_traffic(
                    top_consumers, self.accounting
                )
                
                # Update stats
                self.stats['updates'] += 1
                self.stats['last_analysis'] = time.time()
                
            except Exception as e:
                print(f"❌ Analysis error: {e}")
                time.sleep(5)
                
    def _cleanup_loop(self):
        """Periodic cleanup thread"""
        while self.running:
            try:
                time.sleep(60)
                self.control.cleanup_expired()
                print("🧹 Cleaned up expired rules")
            except Exception as e:
                print(f"❌ Cleanup error: {e}")
            
    def stop(self):
        """Stop all monitoring"""
        self.running = False
        self.capture.stop()
        print("🛑 Network Traffic Manager stopped")
        
    def get_dashboard_data(self):
        """Get all data for dashboard"""
        try:
            return {
                'capture_stats': self.capture.get_stats(),
                'traffic_stats': self.accounting.get_total_traffic(),
                'top_consumers': self.accounting.get_top_consumers(10),
                'anomalies': self.anomaly_detector.get_recent_anomalies(5),
                'active_rules': self.control.get_active_rules(),
                'control_history': self.control.get_history(10),
                'manager_stats': {
                    'uptime': time.time() - self.stats['start_time'],
                    'packets_processed': self.stats['packets_processed'],
                    'updates': self.stats['updates']
                }
            }
        except Exception as e:
            print(f"❌ Error getting dashboard data: {e}")
            return {
                'capture_stats': {'total_packets': 0, 'total_bytes': 0},
                'traffic_stats': {'total_mb': 0, 'active_devices': 0},
                'top_consumers': [],
                'anomalies': [],
                'active_rules': {},
                'control_history': [],
                'manager_stats': {'uptime': 0, 'packets_processed': 0}
            }
        
    def control_device(self, action, ip, **kwargs):
        """Control a device"""
        print(f"🎮 Control action: {action} on {ip}")
        if action == 'throttle':
            return self.control.throttle(ip, kwargs.get('rate', '500kbps'), kwargs.get('duration', 1800))
        elif action == 'block':
            return self.control.block(ip, kwargs.get('duration', 3600))
        elif action == 'unblock':
            return self.control.unblock(ip)
        elif action == 'prioritize':
            return self.control.prioritize(ip, kwargs.get('min_rate', '10mbps'))
        else:
            return False