#!/usr/bin/env python3
"""
User Interface Module - WINDOWS COMPATIBLE VERSION
Handles console display and user interaction without Unix-specific modules
"""

import os
import sys
import time
from datetime import datetime
import msvcrt  # Windows-specific keyboard input
import threading

try:
    from colorama import init, Fore, Back, Style
    init()  # Initialize colorama
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Create dummy color classes
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''

from tabulate import tabulate # type: ignore

class UserInterface:
    """Handles all user interface operations - Windows compatible"""
    
    def __init__(self):
        self.input_buffer = ""
        self.last_update = 0
        self.input_thread_running = False
        self.current_input = ""
        self.input_ready = False
        
    def display_dashboard(self, top_consumers, active_rules, config):
        """Display the main dashboard"""
        self.clear_screen()
        
        # Header
        self._print_header()
        
        # Main content
        self._print_top_consumers(top_consumers)
        print()
        self._print_active_rules(active_rules)
        print()
        self._print_control_menu()
        print()
        self._print_status_line(config)
        
    def _print_header(self):
        """Print application header"""
        print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
        title = "🦍 BANDWIDTH HOG DETECTOR & CONTROLLER"
        print(Fore.YELLOW + Style.BRIGHT + title.center(60) + Style.RESET_ALL)
        print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
        print(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
    def _print_top_consumers(self, consumers):
        """Print top bandwidth consumers table"""
        print(Fore.GREEN + "📊 TOP BANDWIDTH CONSUMERS" + Style.RESET_ALL)
        print("-" * 80)
        
        if not consumers:
            print("No data yet. Capturing packets...")
            return
            
        # Prepare table data
        table_data = []
        for rank, consumer in enumerate(consumers, 1):
            ip = consumer['ip']
            total = consumer['total_mb']
            sent = consumer['sent_mb']
            recv = consumer['recv_mb']
            status = consumer['control_status']
            
            # Color code based on status
            if status == 'blocked':
                status_display = Fore.RED + "🔴 BLOCKED" + Style.RESET_ALL
            elif status == 'throttle':
                rate = consumer['control_info'].get('rate', 'unknown')
                status_display = Fore.YELLOW + f"⚠️ THROTTLED ({rate})" + Style.RESET_ALL
            elif status == 'priority':
                status_display = Fore.BLUE + "⭐ PRIORITY" + Style.RESET_ALL
            else:
                status_display = Fore.GREEN + "✓ NORMAL" + Style.RESET_ALL
                
            table_data.append([
                rank,
                ip,
                f"{total:.1f} MB",
                f"{sent:.1f} MB",
                f"{recv:.1f} MB",
                status_display
            ])
            
        # Print table
        headers = ["Rank", "IP Address", "Total", "Sent", "Received", "Status"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
    def _print_active_rules(self, rules):
        """Print currently active control rules"""
        print(Fore.MAGENTA + "🔒 ACTIVE CONTROL RULES" + Style.RESET_ALL)
        print("-" * 60)
        
        if not rules:
            print("No active rules")
            return
            
        for ip, rule in rules.items():
            action = rule['action']
            if action == 'blocked':
                status = Fore.RED + "BLOCKED" + Style.RESET_ALL
                expiry = self._format_expiry(rule['until'])
                print(f"  {ip}: {status} (expires {expiry})")
            elif action == 'throttle':
                status = Fore.YELLOW + "THROTTLED" + Style.RESET_ALL
                rate = rule.get('rate', 'unknown')
                expiry = self._format_expiry(rule['until'])
                print(f"  {ip}: {status} to {rate} (expires {expiry})")
                
    def _print_control_menu(self):
        """Print interactive control menu"""
        print(Fore.CYAN + "🎮 CONTROL MENU" + Style.RESET_ALL)
        print("-" * 60)
        print("  [T] Throttle device   [B] Block device     [P] Prioritize")
        print("  [U] Unblock device    [C] Configure rules  [R] Reset stats")
        print("  [Q] Quit")
        print()
        print("Enter command (e.g., 'T 1' to throttle device #1): ")
        
    def _print_status_line(self, config):
        """Print status line with configuration info"""
        auto_status = "ON" if config.get('auto_control', {}).get('enabled', True) else "OFF"
        interface = config.get('interface', 'unknown')
        
        status = f"Auto-Control: {auto_status} | Interface: {interface}"
        print(Fore.CYAN + "─" * 60 + Style.RESET_ALL)
        print(status)
        
    def check_for_input(self):
        """Windows-compatible non-blocking input check"""
        if msvcrt.kbhit():
            return True
        return False
        
    def get_user_input(self):
        """Windows-compatible input getter"""
        try:
            # Read a line of input (simplified for Windows)
            user_input = input().strip().lower()
            
            if not user_input:
                return {'action': 'none'}
                
            parts = user_input.split()
            cmd = parts[0]
            
            # Parse commands
            if cmd == 'q':
                return {'action': 'quit'}
                
            elif cmd == 't' and len(parts) >= 2:
                # Throttle: t 1 or t 192.168.1.100 500kbps
                return self._parse_throttle_command(parts)
                
            elif cmd == 'b' and len(parts) >= 2:
                # Block: b 1 or b 192.168.1.100
                return self._parse_block_command(parts)
                
            elif cmd == 'u' and len(parts) >= 2:
                # Unblock: u 1 or u 192.168.1.100
                return self._parse_unblock_command(parts)
                
            elif cmd == 'p' and len(parts) >= 2:
                # Prioritize: p 1 or p 192.168.1.100
                return self._parse_prioritize_command(parts)
                
            elif cmd == 'c':
                return {'action': 'configure'}
                
            elif cmd == 'r':
                return {'action': 'reset'}
                
            else:
                print(f"Unknown command: {user_input}")
                time.sleep(1)
                return {'action': 'none'}
                
        except Exception as e:
            print(f"Input error: {e}")
            return {'action': 'none'}
            
    def _parse_throttle_command(self, parts):
        """Parse throttle command"""
        # Check if it's a rank or IP
        target = parts[1]
        rate = parts[2] if len(parts) > 2 else '500kbps'
        
        # If it's a number, it's a rank (will be resolved later)
        if target.isdigit():
            return {
                'action': 'throttle',
                'rank': int(target),
                'rate': rate,
                'duration': 1800
            }
        else:
            return {
                'action': 'throttle',
                'ip': target,
                'rate': rate,
                'duration': 1800
            }
            
    def _parse_block_command(self, parts):
        """Parse block command"""
        target = parts[1]
        
        if target.isdigit():
            return {
                'action': 'block',
                'rank': int(target),
                'duration': 3600
            }
        else:
            return {
                'action': 'block',
                'ip': target,
                'duration': 3600
            }
            
    def _parse_unblock_command(self, parts):
        """Parse unblock command"""
        target = parts[1]
        
        if target.isdigit():
            return {
                'action': 'unblock',
                'rank': int(target)
            }
        else:
            return {
                'action': 'unblock',
                'ip': target
            }
            
    def _parse_prioritize_command(self, parts):
        """Parse prioritize command"""
        target = parts[1]
        min_rate = parts[2] if len(parts) > 2 else '10mbps'
        
        if target.isdigit():
            return {
                'action': 'prioritize',
                'rank': int(target),
                'min_rate': min_rate
            }
        else:
            return {
                'action': 'prioritize',
                'ip': target,
                'min_rate': min_rate
            }
            
    def _format_expiry(self, timestamp):
        """Format expiry timestamp"""
        if not timestamp:
            return "permanent"
            
        now = time.time()
        if timestamp <= now:
            return "expired"
            
        remaining = timestamp - now
        if remaining < 60:
            return f"{int(remaining)}s"
        elif remaining < 3600:
            return f"{int(remaining/60)}m"
        else:
            return f"{int(remaining/3600)}h"
            
    def show_message(self, message, color=Fore.GREEN):
        """Show a message to the user"""
        print(f"\n{color}{message}{Style.RESET_ALL}")
        time.sleep(1.5)  # Brief pause to read message
        
    def clear_screen(self):
        """Clear the terminal screen (Windows compatible)"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def configure_rules(self, current_config):
        """Interactive configuration menu"""
        self.clear_screen()
        print(Fore.CYAN + "=" * 60)
        print("CONFIGURATION MENU".center(60))
        print("=" * 60 + Style.RESET_ALL)
        
        print("\nCurrent Configuration:")
        auto_config = current_config.get('auto_control', {})
        thresholds = auto_config.get('thresholds', {})
        actions = auto_config.get('actions', {})
        warning_action = actions.get('warning', {})
        
        print(f"1. Auto-control enabled: {auto_config.get('enabled', True)}")
        print(f"2. Warning threshold: {thresholds.get('warning', 100e6) / (1024*1024):.0f} MB")
        print(f"3. Critical threshold: {thresholds.get('critical', 500e6) / (1024*1024):.0f} MB")
        print(f"4. Check interval: {auto_config.get('check_interval', 10)} seconds")
        print(f"5. Throttle rate: {warning_action.get('rate', '256kbps')}")
        print(f"6. Interface: {current_config.get('interface', 'eth0')}")
        print("\nEnter number to change (or 'q' to quit): ")
        
        choice = input().strip()
        
        if choice == '1':
            if 'auto_control' not in current_config:
                current_config['auto_control'] = {}
            current_config['auto_control']['enabled'] = not auto_config.get('enabled', True)
            self.show_message(f"Auto-control set to {current_config['auto_control']['enabled']}")
            
        elif choice == '2':
            print("Enter warning threshold in MB: ")
            try:
                val = int(input())
                if 'auto_control' not in current_config:
                    current_config['auto_control'] = {}
                if 'thresholds' not in current_config['auto_control']:
                    current_config['auto_control']['thresholds'] = {}
                current_config['auto_control']['thresholds']['warning'] = val * 1024 * 1024
            except:
                pass
                
        elif choice == '3':
            print("Enter critical threshold in MB: ")
            try:
                val = int(input())
                if 'auto_control' not in current_config:
                    current_config['auto_control'] = {}
                if 'thresholds' not in current_config['auto_control']:
                    current_config['auto_control']['thresholds'] = {}
                current_config['auto_control']['thresholds']['critical'] = val * 1024 * 1024
            except:
                pass
                
        elif choice == '4':
            print("Enter check interval in seconds: ")
            try:
                val = int(input())
                if 'auto_control' not in current_config:
                    current_config['auto_control'] = {}
                current_config['auto_control']['check_interval'] = val
            except:
                pass
                
        elif choice == '5':
            print("Enter throttle rate (e.g., 256kbps, 1mbps): ")
            rate = input().strip()
            if 'auto_control' not in current_config:
                current_config['auto_control'] = {}
            if 'actions' not in current_config['auto_control']:
                current_config['auto_control']['actions'] = {}
            if 'warning' not in current_config['auto_control']['actions']:
                current_config['auto_control']['actions']['warning'] = {}
            current_config['auto_control']['actions']['warning']['rate'] = rate
            
        elif choice == '6':
            print("Enter network interface name (e.g., 'Wi-Fi', 'Ethernet'): ")
            current_config['interface'] = input().strip()
            
        return current_config