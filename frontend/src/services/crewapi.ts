import type { 
  CrewSession, 
  CrewAgent, 
  CrewTask, 
  CrewMetrics, 
  TaskExecution,
  AgentCollaboration,
  CrewWebSocketMessage 
} from '../types/crewai';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws';

class CrewAPIService {
  private wsConnection: WebSocket | null = null;
  private wsReconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventListeners: Map<string, Set<Function>> = new Map();

  // REST API Methods
  async createSession(sessionData: {
    name: string;
    goal: string;
    workflow: 'sequential' | 'hierarchical' | 'consensus';
    max_iterations?: number;
    agents: Partial<CrewAgent>[];
  }): Promise<CrewSession> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(sessionData),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    return await response.json();
  }

  async getSession(sessionId: string): Promise<CrewSession> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.statusText}`);
    }

    return await response.json();
  }

  async getSessions(): Promise<CrewSession[]> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions`);
    
    if (!response.ok) {
      throw new Error(`Failed to get sessions: ${response.statusText}`);
    }

    return await response.json();
  }

  async startSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}/start`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to start session: ${response.statusText}`);
    }
  }

  async pauseSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to pause session: ${response.statusText}`);
    }
  }

  async stopSession(sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}/stop`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to stop session: ${response.statusText}`);
    }
  }

  async getSessionMetrics(sessionId: string): Promise<CrewMetrics> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}/metrics`);
    
    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }

    return await response.json();
  }

  async getAgent(agentId: string): Promise<CrewAgent> {
    const response = await fetch(`${API_BASE_URL}/api/crew/agents/${agentId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get agent: ${response.statusText}`);
    }

    return await response.json();
  }

  async pauseAgent(agentId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/agents/${agentId}/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to pause agent: ${response.statusText}`);
    }
  }

  async resumeAgent(agentId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/agents/${agentId}/resume`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to resume agent: ${response.statusText}`);
    }
  }

  async resetAgent(agentId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/agents/${agentId}/reset`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to reset agent: ${response.statusText}`);
    }
  }

  async getTask(taskId: string): Promise<CrewTask> {
    const response = await fetch(`${API_BASE_URL}/api/crew/tasks/${taskId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get task: ${response.statusText}`);
    }

    return await response.json();
  }

  async retryTask(taskId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/tasks/${taskId}/retry`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to retry task: ${response.statusText}`);
    }
  }

  async skipTask(taskId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/tasks/${taskId}/skip`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to skip task: ${response.statusText}`);
    }
  }

  async prioritizeTask(taskId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/crew/tasks/${taskId}/prioritize`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Failed to prioritize task: ${response.statusText}`);
    }
  }

  async getTaskExecution(executionId: string): Promise<TaskExecution> {
    const response = await fetch(`${API_BASE_URL}/api/crew/executions/${executionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get task execution: ${response.statusText}`);
    }

    return await response.json();
  }

  async getSessionCollaborations(sessionId: string): Promise<AgentCollaboration[]> {
    const response = await fetch(`${API_BASE_URL}/api/crew/sessions/${sessionId}/collaborations`);
    
    if (!response.ok) {
      throw new Error(`Failed to get collaborations: ${response.statusText}`);
    }

    return await response.json();
  }

  // WebSocket Methods
  connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.wsConnection?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      try {
        this.wsConnection = new WebSocket(WS_URL);

        this.wsConnection.onopen = () => {
          console.log('CrewAI WebSocket connected');
          this.wsReconnectAttempts = 0;
          resolve();
        };

        this.wsConnection.onmessage = (event) => {
          try {
            const message: CrewWebSocketMessage = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.wsConnection.onclose = (event) => {
          console.log('CrewAI WebSocket disconnected:', event.code, event.reason);
          this.handleWebSocketReconnect();
        };

        this.wsConnection.onerror = (error) => {
          console.error('CrewAI WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  disconnectWebSocket(): void {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  private handleWebSocketMessage(message: CrewWebSocketMessage): void {
    // Emit event to all listeners for this event type
    const listeners = this.eventListeners.get(message.event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(message.data);
        } catch (error) {
          console.error('Error in WebSocket event listener:', error);
        }
      });
    }

    // Also emit to 'all' listeners
    const allListeners = this.eventListeners.get('all');
    if (allListeners) {
      allListeners.forEach(listener => {
        try {
          listener(message);
        } catch (error) {
          console.error('Error in WebSocket all event listener:', error);
        }
      });
    }
  }

  private handleWebSocketReconnect(): void {
    if (this.wsReconnectAttempts < this.maxReconnectAttempts) {
      this.wsReconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.wsReconnectAttempts - 1);
      
      console.log(`Attempting to reconnect WebSocket in ${delay}ms (attempt ${this.wsReconnectAttempts})`);
      
      setTimeout(() => {
        this.connectWebSocket().catch(error => {
          console.error('WebSocket reconnection failed:', error);
        });
      }, delay);
    } else {
      console.error('Max WebSocket reconnection attempts reached');
    }
  }

  // Event subscription methods
  on(event: string, listener: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(listener);
  }

  off(event: string, listener: Function): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(listener);
    }
  }

  // Subscribe to all session events
  subscribeToSession(sessionId: string): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify({
        action: 'subscribe',
        session_id: sessionId
      }));
    }
  }

  // Unsubscribe from session events
  unsubscribeFromSession(sessionId: string): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify({
        action: 'unsubscribe',
        session_id: sessionId
      }));
    }
  }

  // Send custom message to backend
  sendMessage(message: any): void {
    if (this.wsConnection?.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }

  // Get WebSocket connection status
  getConnectionStatus(): 'connecting' | 'open' | 'closing' | 'closed' {
    if (!this.wsConnection) return 'closed';
    
    switch (this.wsConnection.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'open';
      case WebSocket.CLOSING: return 'closing';
      case WebSocket.CLOSED: return 'closed';
      default: return 'closed';
    }
  }
}

// Create singleton instance
export const crewAPIService = new CrewAPIService();

// Helper hooks for React components
export const useCrewWebSocket = () => {
  const [connectionStatus, setConnectionStatus] = React.useState<'connecting' | 'open' | 'closing' | 'closed'>('closed');

  React.useEffect(() => {
    const updateStatus = () => {
      setConnectionStatus(crewAPIService.getConnectionStatus());
    };

    // Update status periodically
    const interval = setInterval(updateStatus, 1000);
    updateStatus();

    return () => clearInterval(interval);
  }, []);

  const connect = React.useCallback(() => {
    return crewAPIService.connectWebSocket();
  }, []);

  const disconnect = React.useCallback(() => {
    crewAPIService.disconnectWebSocket();
  }, []);

  const subscribe = React.useCallback((event: string, listener: Function) => {
    crewAPIService.on(event, listener);
    return () => crewAPIService.off(event, listener);
  }, []);

  return {
    connectionStatus,
    connect,
    disconnect,
    subscribe
  };
};

export default crewAPIService;
