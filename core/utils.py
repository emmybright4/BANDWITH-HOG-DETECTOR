#!/usr/bin/env python3
"""
Utility Functions Module - Updated
Helper functions for the application
"""

import os
import sys
import logging
import platform
from datetime import datetime

def is_windows():
    """Check if running on Windows"""
    return platform.system() == "Windows"

def check_root_privileges():
    """Check if the script is running with admin/root privileges"""
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:  # Unix-like
        try:
            return os.geteuid() == 0
        except:
            return False

def check_admin_privileges():
    """Alias for check_root_privileges (more accurate name for Windows)"""
    return check_root_privileges()
        
def setup_logging():
    """Setup logging configuration"""
    log_file = f"bandwidth_hog_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)
    
def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
def format_bytes(bytes_value):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"
    
def get_network_interfaces():
    """Get list of available network interfaces"""
    try:
        import psutil # type: ignore
        interfaces = psutil.net_if_addrs()
        return list(interfaces.keys())
    except Exception as e:
        print(f"⚠️ Could not get interfaces: {e}")
        # Return common interface names based on OS
        if is_windows():
            return ['Wi-Fi', 'Ethernet', 'vEthernet']
        else:
            return ['eth0', 'wlan0', 'en0']
        
def validate_ip(ip):
    """Validate IP address format"""
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, ip):
        parts = ip.split('.')
        for part in parts:
            if int(part) > 255:
                return False
        return True
    return False
    
def safe_execute(func, default=None):
    """Safely execute a function, returning default on error"""
    try:
        return func()
    except Exception:
        return default

def get_python_version():
    """Get current Python version as string"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"