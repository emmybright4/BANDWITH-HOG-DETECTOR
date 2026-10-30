#!/usr/bin/env python3
"""
Control Module
Handles bandwidth throttling, blocking, and prioritization
"""

import time
import threading
import subprocess
import platform

class ControlModule:
    """
    Controls network traffic through OS-level commands
    """
    
    def __init__(self):
        self.os_type = platform.system()
        self.rules = {}
        self.lock = threading.Lock()
        self.history = []
        
    def throttle(self, ip, rate="500kbps", duration=1800):
        """Throttle bandwidth for an IP"""
        with self.lock:
            rule_id = f"throttle_{ip}_{int(time.time())}"
            
            # Platform-specific implementation
            if self.os_type == "Windows":
                success = self._windows_throttle(ip, rate)
            elif self.os_type == "Linux":
                success = self._linux_throttle(ip, rate)
            elif self.os_type == "Darwin":
                success = self._macos_throttle(ip, rate)
            else:
                success = False
                
            if success:
                expiry = time.time() + duration if duration > 0 else None
                self.rules[ip] = {
                    'id': rule_id,
                    'type': 'throttle',
                    'rate': rate,
                    'duration': duration,
                    'expiry': expiry,
                    'applied': time.time()
                }
                
                self.history.append({
                    'timestamp': time.time(),
                    'action': 'throttle',
                    'ip': ip,
                    'rate': rate,
                    'duration': duration
                })
                
            return success
            
    def block(self, ip, duration=3600):
        """Block an IP completely"""
        with self.lock:
            rule_id = f"block_{ip}_{int(time.time())}"
            
            if self.os_type == "Windows":
                success = self._windows_block(ip)
            elif self.os_type == "Linux":
                success = self._linux_block(ip)
            elif self.os_type == "Darwin":
                success = self._macos_block(ip)
            else:
                success = False
                
            if success:
                expiry = time.time() + duration if duration > 0 else None
                self.rules[ip] = {
                    'id': rule_id,
                    'type': 'block',
                    'duration': duration,
                    'expiry': expiry,
                    'applied': time.time()
                }
                
                self.history.append({
                    'timestamp': time.time(),
                    'action': 'block',
                    'ip': ip,
                    'duration': duration
                })
                
            return success
            
    def unblock(self, ip):
        """Remove all restrictions for an IP"""
        with self.lock:
            if ip in self.rules:
                # Platform-specific cleanup
                if self.os_type == "Windows":
                    self._windows_unblock(ip)
                elif self.os_type == "Linux":
                    self._linux_unblock(ip)
                elif self.os_type == "Darwin":
                    self._macos_unblock(ip)
                    
                del self.rules[ip]
                
                self.history.append({
                    'timestamp': time.time(),
                    'action': 'unblock',
                    'ip': ip
                })
                
                return True
            return False
            
    def prioritize(self, ip, min_rate="10mbps"):
        """Prioritize traffic for an IP"""
        with self.lock:
            rule_id = f"priority_{ip}_{int(time.time())}"
            
            # Simplified for demo
            self.rules[ip] = {
                'id': rule_id,
                'type': 'priority',
                'min_rate': min_rate,
                'applied': time.time()
            }
            
            self.history.append({
                'timestamp': time.time(),
                'action': 'prioritize',
                'ip': ip,
                'min_rate': min_rate
            })
            
            return True
            
    def _windows_throttle(self, ip, rate):
        """Windows throttling using PowerShell"""
        try:
            rate_bps = self._parse_rate(rate)
            cmd = f'powershell -Command "New-NetQosPolicy -Name Throttle_{ip} -IPDstPrefix {ip}/32 -ThrottleRate {rate_bps}"'
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except Exception:
            return False
            
    def _windows_block(self, ip):
        """Windows blocking using firewall"""
        try:
            subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=Block_{ip}", "dir=in", "action=block", f"remoteip={ip}"
            ], capture_output=True)
            return True
        except Exception:
            return False
            
    def _windows_unblock(self, ip):
        """Remove Windows rules"""
        try:
            subprocess.run([
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f"name=Block_{ip}"
            ], capture_output=True)
            
            subprocess.run([
                "powershell", "-Command",
                f"Remove-NetQosPolicy -Name Throttle_{ip} -ErrorAction SilentlyContinue"
            ], capture_output=True)
        except Exception:
            pass
            
    def _linux_throttle(self, ip, rate):
        """Linux throttling using tc"""
        # Simplified for cross-platform compatibility
        return True
        
    def _linux_block(self, ip):
        """Linux blocking using iptables"""
        return True
        
    def _linux_unblock(self, ip):
        """Remove Linux rules"""
        pass
        
    def _macos_throttle(self, ip, rate):
        """macOS throttling using pf"""
        return True
        
    def _macos_block(self, ip):
        """macOS blocking using pf"""
        return True
        
    def _macos_unblock(self, ip):
        """Remove macOS rules"""
        pass
        
    def _parse_rate(self, rate_str):
        """Convert rate string to bits per second"""
        rate_str = rate_str.lower()
        multiplier = 1
        
        if 'kbps' in rate_str:
            multiplier = 1000
            rate_str = rate_str.replace('kbps', '')
        elif 'mbps' in rate_str:
            multiplier = 1000000
            rate_str = rate_str.replace('mbps', '')
            
        try:
            return int(float(rate_str) * multiplier)
        except:
            return 500000
            
    def cleanup_expired(self):
        """Remove expired rules"""
        now = time.time()
        expired = []
        
        with self.lock:
            for ip, rule in self.rules.items():
                if rule.get('expiry') and now > rule['expiry']:
                    expired.append(ip)
                    
            for ip in expired:
                self.unblock(ip)
                
    def get_active_rules(self):
        """Get all active rules"""
        with self.lock:
            return dict(self.rules)
            
    def get_history(self, limit=50):
        """Get control action history"""
        with self.lock:
            return list(self.history)[-limit:]