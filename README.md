# Bandwidth Hog Detector with Consumption Reduction

A powerful network monitoring tool that identifies which devices are consuming the most bandwidth and **automatically reduces their consumption** through throttling or blocking.

## Features

### 📊 Detection
- Real-time packet capture and analysis
- Top 10 bandwidth consumers identification
- Live bandwidth usage graphs
- Per-IP traffic accounting (sent/received)

### 🚦 Reduction/Action Features (⭐ NEW)
- **Automatic Throttling** - Slow down bandwidth hogs automatically
- **Automatic Blocking** - Completely block devices that exceed limits
- **Manual Control** - Throttle/block any device with simple commands
- **Priority Mode** - Guarantee minimum bandwidth for important devices
- **Time-based Rules** - Different rules for different times of day
- **Threshold-based Automation** - Set it and forget it

### 🎮 Interactive Interface
- Color-coded live dashboard
- Simple command menu (T=Throttle, B=Block, U=Unblock)
- Configuration menu for easy setup
- Real-time status updates

## How It Works

1. **DETECT** - Captures network packets and identifies top consumers
2. **DECIDE** - Checks against your rules and thresholds
3. **REDUCE** - Applies throttling or blocking automatically
4. **REPORT** - Shows you what actions were taken

## Installation

### Prerequisites
- Python 3.7 or higher
- Root/Administrator privileges
- Network interface in promiscuous mode

### Steps

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt