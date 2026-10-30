// Chart Utilities - NO DashboardManager class here!
console.log('📊 ChartUtils loading...');

const ChartUtils = {
    /**
     * Format bytes to human readable format
     * @param {number} bytes - Bytes to format
     * @returns {string} Formatted string (e.g., "1.5 MB")
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Format bits per second to human readable format
     * @param {number} bits - Bits per second
     * @returns {string} Formatted string (e.g., "1.5 Mbps")
     */
    formatBits(bits) {
        if (bits === 0) return '0 bps';
        const k = 1000;
        const sizes = ['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps'];
        const i = Math.floor(Math.log(bits) / Math.log(k));
        return parseFloat((bits / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Create time labels for charts
     * @param {number} count - Number of labels to create
     * @returns {string[]} Array of time strings
     */
    createTimeLabels(count = 20) {
        const labels = [];
        const now = new Date();
        for (let i = count - 1; i >= 0; i--) {
            const time = new Date(now - i * 2000);
            labels.push(time.toLocaleTimeString());
        }
        return labels;
    },
    
    /**
     * Update chart colors based on theme
     * @param {Chart} chart - Chart.js instance
     * @param {boolean} isDark - Whether dark mode is enabled
     */
    updateChartColors(chart, isDark) {
        if (!chart) return;
        const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
        const textColor = isDark ? '#ffffff' : '#666666';
        
        if (chart.options.scales?.y) {
            chart.options.scales.y.grid.color = gridColor;
            chart.options.scales.y.ticks.color = textColor;
        }
        if (chart.options.scales?.x) {
            chart.options.scales.x.grid.color = gridColor;
            chart.options.scales.x.ticks.color = textColor;
        }
        chart.update();
    },
    
    /**
     * Create a bandwidth chart
     * @param {string} canvasId - ID of canvas element
     * @returns {Chart} Chart.js instance
     */
    createBandwidthChart(canvasId) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Download',
                        data: [],
                        borderColor: '#4361ee',
                        backgroundColor: 'rgba(67, 97, 238, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    },
                    {
                        label: 'Upload',
                        data: [],
                        borderColor: '#06d6a0',
                        backgroundColor: 'rgba(6, 214, 160, 0.1)',
                        tension: 0.4,
                        fill: true,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        title: {
                            display: true,
                            text: 'Mbps'
                        }
                    },
                    x: {
                        grid: { display: false },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: { 
                        display: true,
                        position: 'top',
                        labels: { 
                            boxWidth: 12,
                            color: '#666'
                        }
                    },
                    tooltip: { 
                        mode: 'index', 
                        intersect: false,
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff'
                    }
                }
            }
        });
    },
    
    /**
     * Create a protocol distribution chart
     * @param {string} canvasId - ID of canvas element
     * @returns {Chart} Chart.js instance
     */
    createProtocolChart(canvasId) {
        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['TCP', 'UDP', 'ICMP', 'Other'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#4361ee', '#06d6a0', '#ffd166', '#ef476f'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { 
                        display: true,
                        position: 'bottom',
                        labels: { 
                            boxWidth: 12,
                            color: '#666'
                        }
                    },
                    tooltip: { 
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    },
    
    /**
     * Update bandwidth chart with new data
     * @param {Chart} chart - Chart.js instance
     * @param {number} download - Download speed in Mbps
     * @param {number} upload - Upload speed in Mbps
     */
    updateBandwidthChart(chart, download, upload) {
        if (!chart) return;
        
        const now = new Date().toLocaleTimeString();
        
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(download || 0);
        chart.data.datasets[1].data.push(upload || 0);
        
        // Keep last 30 points
        const maxPoints = 30;
        if (chart.data.labels.length > maxPoints) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[1].data.shift();
        }
        
        chart.update('none');
    },
    
    /**
     * Update protocol chart with packet counts
     * @param {Chart} chart - Chart.js instance
     * @param {Object} stats - Capture statistics
     */
    updateProtocolChart(chart, stats) {
        if (!chart || !stats) return;
        
        chart.data.datasets[0].data = [
            stats.tcp_packets || 0,
            stats.udp_packets || 0,
            stats.icmp_packets || 0,
            stats.other_packets || 0
        ];
        
        chart.update();
    },
    
    /**
     * Create empty dataset for charts
     * @returns {Object} Empty chart data
     */
    createEmptyDataset() {
        return {
            labels: [],
            datasets: []
        };
    }
};

// Make it globally available
window.ChartUtils = ChartUtils;

// Also export as module if in Node.js environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartUtils;
}

console.log('✅ ChartUtils loaded successfully');