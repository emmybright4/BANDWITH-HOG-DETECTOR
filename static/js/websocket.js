// WebSocket Connection Manager - COMPLETE UPDATED VERSION
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.updateCallbacks = [];
        this.controlCallbacks = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 2000; // Start with 2 seconds
        this.connectionPromise = null;
        this.debug = true; // Set to false to disable debug logs
        
        this.init();
    }
    
    init() {
        console.log('🔌 Initializing WebSocket Manager...');
        this.connect();
    }
    
    connect() {
        try {
            console.log('📡 Connecting to WebSocket server...');
            
            // Create socket connection with options
            this.socket = io('http://localhost:5000', {
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay,
                reconnectionDelayMax: 10000,
                timeout: 20000,
                transports: ['websocket', 'polling'] // Try websocket first, fallback to polling
            });
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('❌ WebSocket connection error:', error);
            this.attemptReconnect();
        }
    }
    
    setupEventHandlers() {
        // Connection established
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected successfully!');
            console.log('   Socket ID:', this.socket.id);
            console.log('   Transport:', this.socket.io.engine.transport.name);
            
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 2000;
            this.updateConnectionStatus(true);
            
            // Request initial data
            this.emit('request_update', { timestamp: Date.now() });
        });
        
        // Connection error
        this.socket.on('connect_error', (error) => {
            console.error('❌ WebSocket connection error:', error);
            this.connected = false;
            this.updateConnectionStatus(false);
        });
        
        // Disconnection
        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected. Reason:', reason);
            this.connected = false;
            this.updateConnectionStatus(false);
            
            if (reason === 'io server disconnect') {
                // Server disconnected, attempt reconnect
                setTimeout(() => this.connect(), 1000);
            }
            // Otherwise auto-reconnect will handle it
        });
        
        // Reconnection attempts
        this.socket.io.on('reconnect_attempt', (attempt) => {
            console.log(`🔄 Reconnection attempt #${attempt}`);
            this.reconnectAttempts = attempt;
        });
        
        this.socket.io.on('reconnect', () => {
            console.log('✅ Reconnected successfully!');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        });
        
        this.socket.io.on('reconnect_error', (error) => {
            console.error('❌ Reconnection error:', error);
        });
        
        this.socket.io.on('reconnect_failed', () => {
            console.error('❌ Reconnection failed after', this.maxReconnectAttempts, 'attempts');
            this.showReconnectionFailed();
        });
        
        // Dashboard updates from server
        this.socket.on('dashboard_update', (data) => {
            if (this.debug) {
                console.log('📊 Received dashboard update:', {
                    update_id: data.update_id,
                    timestamp: new Date(data.timestamp * 1000).toLocaleTimeString(),
                    has_data: !!data.data
                });
            }
            
            // Log first few packets for debugging
            if (data.update_id <= 5 && this.debug) {
                console.log('   Update details:', data);
            }
            
            // Call all registered update callbacks
            this.updateCallbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error('❌ Error in update callback:', e);
                }
            });
        });
        
        // Control updates from server
        this.socket.on('control_update', (data) => {
            console.log('🎮 Received control update:', data);
            
            this.controlCallbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error('❌ Error in control callback:', e);
                }
            });
        });
        
        // Ping/Pong for latency testing
        this.socket.on('ping_response', (data) => {
            console.log('🏓 Ping response:', data);
        });
        
        // Error handling
        this.socket.on('error', (error) => {
            console.error('❌ WebSocket error:', error);
        });
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('system-status');
        if (statusElement) {
            const dot = statusElement.querySelector('.status-dot');
            const text = statusElement.querySelector('span:last-child');
            
            if (connected) {
                dot.className = 'status-dot online';
                text.textContent = 'System Online';
            } else {
                dot.className = 'status-dot offline';
                text.textContent = 'System Offline';
            }
        }
        
        // Also update connection status indicator if exists
        const connectionStatus = document.getElementById('connectionStatus');
        if (connectionStatus) {
            connectionStatus.className = connected ? 'status connected' : 'status disconnected';
            connectionStatus.textContent = connected ? '● Connected' : '● Disconnected';
        }
    }
    
    showReconnectionFailed() {
        // Show user-friendly message
        const toast = document.createElement('div');
        toast.className = 'toast-error';
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Lost connection to server. Please refresh the page.</span>
            </div>
        `;
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => toast.remove(), 5000);
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
            console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${Math.round(delay/1000)}s`);
            
            setTimeout(() => {
                if (!this.connected) {
                    this.connect();
                }
            }, delay);
        } else {
            console.error('❌ Max reconnection attempts reached');
            this.showReconnectionFailed();
        }
    }
    
    onUpdate(callback) {
        if (typeof callback === 'function') {
            this.updateCallbacks.push(callback);
            console.log(`✅ Update callback registered. Total callbacks: ${this.updateCallbacks.length}`);
        } else {
            console.error('❌ onUpdate: callback must be a function');
        }
    }
    
    onControl(callback) {
        if (typeof callback === 'function') {
            this.controlCallbacks.push(callback);
            console.log(`✅ Control callback registered. Total callbacks: ${this.controlCallbacks.length}`);
        }
    }
    
    emit(event, data) {
        if (this.connected && this.socket) {
            this.socket.emit(event, data);
            if (this.debug) {
                console.log(`📤 Emitted event '${event}':`, data);
            }
        } else {
            console.warn(`⚠️ Cannot emit '${event}': WebSocket not connected`);
        }
    }
    
    // Test method to check connection health
    testConnection() {
        return new Promise((resolve, reject) => {
            if (!this.connected) {
                reject(new Error('WebSocket not connected'));
                return;
            }
            
            const start = Date.now();
            this.socket.emit('ping', { time: start }, (response) => {
                const latency = Date.now() - start;
                console.log(`🏓 Pong received! Latency: ${latency}ms`);
                resolve({ latency, response });
            });
            
            // Timeout after 5 seconds
            setTimeout(() => reject(new Error('Ping timeout')), 5000);
        });
    }
    
    // Get connection stats
    getStats() {
        return {
            connected: this.connected,
            socketId: this.socket?.id || null,
            reconnectAttempts: this.reconnectAttempts,
            transport: this.socket?.io.engine.transport.name || 'unknown',
            updateCallbacks: this.updateCallbacks.length,
            controlCallbacks: this.controlCallbacks.length
        };
    }
}

// Create global instance
console.log('🚀 Creating WebSocketManager instance...');
const wsManager = new WebSocketManager();

// Expose to window for debugging
window.wsManager = wsManager;

// Add test function to window for easy testing
window.testWebSocket = async function() {
    console.log('🧪 Testing WebSocket connection...');
    console.log('Current stats:', wsManager.getStats());
    
    try {
        const result = await wsManager.testConnection();
        console.log('✅ Test successful:', result);
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
};

// Auto-run test after 2 seconds (for debugging)
setTimeout(() => {
    if (wsManager.connected) {
        console.log('✅ WebSocket is connected. Socket ID:', wsManager.socket?.id);
    } else {
        console.log('⚠️ WebSocket not yet connected. Attempts:', wsManager.reconnectAttempts);
    }
}, 2000);

console.log('✅ WebSocketManager initialized');