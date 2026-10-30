// Dashboard JavaScript - Main controller
class DashboardController {
    constructor() {
        this.devices = [];
        this.bandwidthChart = null;
        this.protocolChart = null;
        this.updateInterval = null;
        this.lastUpdate = Date.now();
        this.lastDownload = 0;
    }
    
    async init() {
        this.initCharts();
        await this.refreshData();
        this.startAutoRefresh();
    }
    
    initCharts() {
        const ctx1 = document.getElementById('bandwidthChart').getContext('2d');
        this.bandwidthChart = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    { label: 'Download (Mbps)', data: [], borderColor: '#4361ee', backgroundColor: 'rgba(67, 97, 238, 0.1)', tension: 0.4, fill: true },
                    { label: 'Upload (Mbps)', data: [], borderColor: '#06d6a0', backgroundColor: 'rgba(6, 214, 160, 0.1)', tension: 0.4, fill: true }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'top' } },
                scales: { y: { beginAtZero: true, title: { display: true, text: 'Mbps' } } }
            }
        });
        
        const ctx2 = document.getElementById('protocolChart').getContext('2d');
        this.protocolChart = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: ['TCP', 'UDP', 'HTTP', 'HTTPS', 'Other'],
                datasets: [{ data: [0, 0, 0, 0, 0], backgroundColor: ['#4361ee', '#06d6a0', '#ffd166', '#ef476f', '#999'] }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
    
    async refreshData() {
        await Promise.all([
            this.fetchStats(),
            this.fetchDevices(),
            this.fetchBandwidthHistory(),
            this.fetchProtocolStats(),
            this.fetchAnomalies(),
            this.fetchRules()
        ]);
        
        this.lastUpdate = Date.now();
        const lastUpdateSpan = document.getElementById('last-update');
        if (lastUpdateSpan) lastUpdateSpan.textContent = 'Just now';
    }
    
    async fetchStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            const totalTrafficSpan = document.getElementById('total-traffic');
            const packetsCapturedSpan = document.getElementById('packets-captured');
            const activeDevicesSpan = document.getElementById('active-devices');
            const captureRateSpan = document.getElementById('capture-rate');
            const wifiNameSpan = document.getElementById('wifi-name');
            
            if (totalTrafficSpan) totalTrafficSpan.textContent = `${data.total_traffic} MB`;
            if (packetsCapturedSpan) packetsCapturedSpan.textContent = data.packet_count.toLocaleString();
            if (activeDevicesSpan) activeDevicesSpan.textContent = data.active_devices;
            if (captureRateSpan) captureRateSpan.textContent = `${data.capture_rate}/s`;
            if (wifiNameSpan) wifiNameSpan.textContent = data.network_name || 'Wi-Fi';
            
            // Calculate trend
            if (this.lastDownload && data.download_mbps) {
                const trend = ((data.download_mbps - this.lastDownload) / this.lastDownload * 100).toFixed(0);
                const trendSpan = document.getElementById('traffic-trend');
                if (trendSpan) trendSpan.textContent = `${trend}%`;
            }
            this.lastDownload = data.download_mbps;
            
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }
    
    async fetchDevices() {
        try {
            const response = await fetch('/api/devices');
            this.devices = await response.json();
            
            const tbody = document.getElementById('devices-body');
            if (!tbody) return;
            
            if (this.devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="loading">No devices found</td></tr>';
                return;
            }
            
            // Update device select dropdown
            const select = document.getElementById('device-select');
            if (select) {
                select.innerHTML = '<option value="">Select Device</option>' + 
                    this.devices.map(d => `<option value="${d.ip}">${d.hostname || d.ip}</option>`).join('');
            }
            
            // Render table
            tbody.innerHTML = this.devices.map(device => `
                <tr>
                    <td>#${device.rank}</td>
                    <td><code>${device.ip}</code></td>
                    <td>${device.hostname || '-'}</td>
                    <td><strong>${device.total_mb} MB</strong></td>
                    <td class="trend-up">▼ ${device.download_mb} MB</td>
                    <td class="trend-down">▲ ${device.upload_mb} MB</td>
                    <td>${device.packets.toLocaleString()}</td>
                    <td>
                        <span class="status-badge status-${device.status.toLowerCase()}">${device.status}</span>
                    </td>
                    <td>
                        <button class="btn-action" onclick="window.dashboard?.throttleDevice('${device.ip}')" title="Throttle">
                            <i class="fas fa-tachometer-alt"></i>
                        </button>
                        <button class="btn-action" onclick="window.dashboard?.blockDevice('${device.ip}')" title="Block">
                            <i class="fas fa-ban"></i>
                        </button>
                        <button class="btn-action" onclick="window.dashboard?.unblockDevice('${device.ip}')" title="Unblock">
                            <i class="fas fa-check-circle"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            console.error('Error fetching devices:', error);
        }
    }
    
    async fetchBandwidthHistory() {
        try {
            const response = await fetch('/api/bandwidth-history');
            const data = await response.json();
            
            if (this.bandwidthChart) {
                this.bandwidthChart.data.labels = data.labels;
                this.bandwidthChart.data.datasets[0].data = data.download;
                this.bandwidthChart.data.datasets[1].data = data.upload;
                this.bandwidthChart.update();
            }
        } catch (error) {
            console.error('Error fetching bandwidth history:', error);
        }
    }
    
    async fetchProtocolStats() {
        try {
            const response = await fetch('/api/protocol-stats');
            const data = await response.json();
            
            if (this.protocolChart) {
                this.protocolChart.data.datasets[0].data = [data.tcp, data.udp, data.http, data.https, data.other || 0];
                this.protocolChart.update();
            }
        } catch (error) {
            console.error('Error fetching protocol stats:', error);
        }
    }
    
    async fetchAnomalies() {
        try {
            const response = await fetch('/api/anomalies');
            const data = await response.json();
            
            const anomalyCountSpan = document.getElementById('anomaly-count');
            const anomalyTrendSpan = document.getElementById('anomaly-trend');
            const container = document.getElementById('anomaly-container');
            
            if (anomalyCountSpan) anomalyCountSpan.textContent = data.count;
            if (anomalyTrendSpan) anomalyTrendSpan.textContent = data.count;
            
            if (!container) return;
            
            if (data.anomalies.length === 0) {
                container.innerHTML = '<p class="text-muted">No anomalies detected</p>';
                return;
            }
            
            container.innerHTML = data.anomalies.slice(0, 10).map(a => `
                <div class="anomaly-item">
                    <i class="fas fa-exclamation-triangle" style="color: #ffd166;"></i>
                    <strong>${a.time}</strong> - ${a.description}
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error fetching anomalies:', error);
        }
    }
    
    async fetchRules() {
        try {
            const response = await fetch('/api/rules');
            const rules = await response.json();
            
            const container = document.getElementById('rules-container');
            if (!container) return;
            
            if (rules.length === 0) {
                container.innerHTML = '<p class="text-muted">No active rules</p>';
                return;
            }
            
            container.innerHTML = rules.map(r => `
                <div class="rule-item">
                    <i class="fas fa-gavel"></i>
                    <strong>${r.device}</strong> (${r.ip}) - ${r.action}
                    <br><small>${r.time}</small>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Error fetching rules:', error);
        }
    }
    
    async throttleDevice(ip, rate = '500kbps') {
        try {
            const response = await fetch('/api/control/throttle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip, rate })
            });
            if (response.ok) {
                this.refreshData();
                alert(`Device ${ip} throttled to ${rate}`);
            }
        } catch (error) {
            console.error('Error throttling device:', error);
        }
    }
    
    async blockDevice(ip) {
        try {
            const response = await fetch('/api/control/block', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            if (response.ok) {
                this.refreshData();
                alert(`Device ${ip} blocked`);
            }
        } catch (error) {
            console.error('Error blocking device:', error);
        }
    }
    
    async unblockDevice(ip) {
        try {
            const response = await fetch('/api/control/unblock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip })
            });
            if (response.ok) {
                this.refreshData();
                alert(`Device ${ip} unblocked`);
            }
        } catch (error) {
            console.error('Error unblocking device:', error);
        }
    }
    
    async exportToCSV() {
        try {
            const response = await fetch('/api/export-csv');
            const devices = await response.json();
            
            let csv = 'IP,MAC,Hostname,Status,Download_MB,Upload_MB,Total_MB\n';
            devices.forEach(d => {
                csv += `"${d.IP}","${d.MAC}","${d.Hostname}","${d.Status}",${d.Download_MB},${d.Upload_MB},${d.Total_MB}\n`;
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bandwidth_report_${new Date().toISOString().slice(0,19)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error exporting CSV:', error);
        }
    }
    
    startAutoRefresh() {
        this.updateInterval = setInterval(() => {
            this.refreshData();
            
            // Update last update time
            const now = Date.now();
            const diff = Math.floor((now - this.lastUpdate) / 1000);
            const lastUpdateSpan = document.getElementById('last-update');
            if (lastUpdateSpan) {
                if (diff < 60) {
                    lastUpdateSpan.textContent = `${diff}s ago`;
                } else {
                    lastUpdateSpan.textContent = 'Just now';
                }
            }
        }, 2000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardController();
    window.dashboard.init();
});