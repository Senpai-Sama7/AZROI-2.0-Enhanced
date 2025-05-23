/**
 * WebSocket optimization utilities for the Autonomous AI Architect frontend.
 * Provides connection management, reconnection logic, and message queuing.
 */

export interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  reconnectBackoff?: 'linear' | 'exponential';
}

export interface WebSocketMessage {
  event: string;
  data: any;
  timestamp?: string;
}

export interface WebSocketManagerEvents {
  onOpen?: () => void;
  onMessage?: (message: WebSocketMessage) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;
  onReconnect?: (attempt: number) => void;
  onMaxReconnectAttemptsReached?: () => void;
}

export class OptimizedWebSocketManager {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private events: WebSocketManagerEvents;
  private reconnectAttempts = 0;
  private reconnectTimeoutId: number | null = null;
  private heartbeatIntervalId: number | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private isConnecting = false;
  private lastHeartbeat: Date | null = null;
  private connectionQuality: 'good' | 'poor' | 'disconnected' = 'disconnected';

  constructor(config: WebSocketConfig, events: WebSocketManagerEvents = {}) {
    this.config = {
      reconnectInterval: 1000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      reconnectBackoff: 'exponential',
      ...config
    };
    this.events = events;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    this.connectionQuality = 'disconnected';

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventListeners();
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.clearReconnectTimeout();
    this.clearHeartbeatInterval();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.reconnectAttempts = 0;
    this.isConnecting = false;
    this.connectionQuality = 'disconnected';
  }

  /**
   * Send a message to the server
   */
  sendMessage(message: WebSocketMessage): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        const messageWithTimestamp = {
          ...message,
          timestamp: new Date().toISOString()
        };
        this.ws.send(JSON.stringify(messageWithTimestamp));
        return true;
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        this.queueMessage(message);
        return false;
      }
    } else {
      this.queueMessage(message);
      return false;
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): {
    isConnected: boolean;
    quality: 'good' | 'poor' | 'disconnected';
    lastHeartbeat: Date | null;
    reconnectAttempts: number;
  } {
    return {
      isConnected: this.ws?.readyState === WebSocket.OPEN,
      quality: this.connectionQuality,
      lastHeartbeat: this.lastHeartbeat,
      reconnectAttempts: this.reconnectAttempts
    };
  }

  /**
   * Force a reconnection attempt
   */
  forceReconnect(): void {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.connect();
  }

  private setupEventListeners(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.connectionQuality = 'good';
      this.lastHeartbeat = new Date();
      
      this.clearReconnectTimeout();
      this.startHeartbeat();
      this.processMessageQueue();
      
      this.events.onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.lastHeartbeat = new Date();
        this.updateConnectionQuality();
        
        // Handle heartbeat messages
        if (message.event === 'heartbeat') {
          this.sendMessage({ event: 'heartbeat_ack', data: {} });
          return;
        }
        
        this.events.onMessage?.(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.isConnecting = false;
      this.connectionQuality = 'disconnected';
      this.clearHeartbeatInterval();
      
      this.events.onClose?.(event);
      
      // Don't reconnect if this was a normal closure
      if (event.code !== 1000) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.isConnecting = false;
      this.events.onError?.(error);
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.warn('Max WebSocket reconnection attempts reached');
      this.events.onMaxReconnectAttemptsReached?.();
      return;
    }

    this.clearReconnectTimeout();

    let delay = this.config.reconnectInterval;
    
    if (this.config.reconnectBackoff === 'exponential') {
      delay = Math.min(
        this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts),
        30000 // Max 30 seconds
      );
    } else {
      delay = this.config.reconnectInterval * (this.reconnectAttempts + 1);
    }

    this.reconnectTimeoutId = window.setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`WebSocket reconnection attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts}`);
      
      this.events.onReconnect?.(this.reconnectAttempts);
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.clearHeartbeatInterval();
    
    this.heartbeatIntervalId = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendMessage({ event: 'ping', data: {} });
        this.updateConnectionQuality();
      }
    }, this.config.heartbeatInterval);
  }

  private updateConnectionQuality(): void {
    if (!this.lastHeartbeat) {
      this.connectionQuality = 'poor';
      return;
    }

    const timeSinceHeartbeat = Date.now() - this.lastHeartbeat.getTime();
    
    if (timeSinceHeartbeat < this.config.heartbeatInterval) {
      this.connectionQuality = 'good';
    } else if (timeSinceHeartbeat < this.config.heartbeatInterval * 2) {
      this.connectionQuality = 'poor';
    } else {
      this.connectionQuality = 'disconnected';
    }
  }

  private queueMessage(message: WebSocketMessage): void {
    if (this.messageQueue.length >= this.config.messageQueueSize) {
      this.messageQueue.shift(); // Remove oldest message
    }
    
    this.messageQueue.push(message);
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }

  private clearHeartbeatInterval(): void {
    if (this.heartbeatIntervalId) {
      clearInterval(this.heartbeatIntervalId);
      this.heartbeatIntervalId = null;
    }
  }
}

/**
 * Create a WebSocket manager with default configuration for the Autonomous AI Architect
 */
export function createWebSocketManager(
  url: string = 'ws://localhost:8001/ws',
  events: WebSocketManagerEvents = {}
): OptimizedWebSocketManager {
  return new OptimizedWebSocketManager(
    {
      url,
      reconnectInterval: 2000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      messageQueueSize: 50,
      reconnectBackoff: 'exponential'
    },
    events
  );
}

/**
 * WebSocket message types for type safety
 */
export const WS_MESSAGE_TYPES = {
  AGENT_UPDATE: 'agent_update',
  OUTPUT_UPDATE: 'output_update',
  GOAL_UPDATE: 'goal_update',
  ERROR: 'error',
  HEARTBEAT: 'heartbeat',
  PING: 'ping',
  PONG: 'pong'
} as const;

export type WSMessageType = typeof WS_MESSAGE_TYPES[keyof typeof WS_MESSAGE_TYPES];
