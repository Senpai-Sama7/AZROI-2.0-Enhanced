import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import GoalInputPanel from './components/GoalInputPanel';
import ArchitectDashboard from './components/ArchitectDashboard';
import CrewAIWrapper from './components/CrewAIWrapper';
import MonitoringPanel from './components/MonitoringPanel';
import ConfigPanel from './components/ConfigPanel';
import HelpSettingsModal from './components/HelpSettingsModal';
import StarryBackground from './components/StarryBackground';
import type { ArchitectGoal, Agent, ArchitectOutput, SystemStatus, WebSocketMessage } from './types';

import './index.css';

const App: React.FC = () => {
  // Core state
  const [currentGoal, setCurrentGoal] = useState<ArchitectGoal | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [outputs, setOutputs] = useState<ArchitectOutput[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [processingError, setProcessingError] = useState<string | null>(null);
  
  // UI state
  const [activePanel, setActivePanel] = useState<'input' | 'dashboard' | 'crew' | 'monitoring' | 'config'>('input');
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // WebSocket state
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [wsReconnectAttempts, setWsReconnectAttempts] = useState(0);
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (wsConnection?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      const ws = new WebSocket('ws://localhost:8001/ws');
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnection(ws);
        setWsReconnectAttempts(0);
        setLastHeartbeat(new Date());
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
          setLastHeartbeat(new Date());
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setWsConnection(null);
        
        // Attempt reconnection with exponential backoff
        if (wsReconnectAttempts < 5) {
          const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000);
          setTimeout(() => {
            setWsReconnectAttempts(prev => prev + 1);
            connectWebSocket();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setProcessingError('WebSocket connection error. Real-time updates may be delayed.');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setProcessingError('Failed to establish real-time connection.');
    }
  }, [wsConnection, wsReconnectAttempts]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.event) {
      case 'initial_state':
        if (message.data.goals) {
          const latestGoal = message.data.goals[message.data.goals.length - 1];
          if (latestGoal) setCurrentGoal(latestGoal);
        }
        if (message.data.agents) {
          setAgents(message.data.agents);
        }
        if (message.data.outputs) {
          setOutputs(message.data.outputs);
        }
        break;

      case 'goal_update':
        if (message.data.goal_id && message.data.goal_status) {
          setCurrentGoal(prev => prev ? {
            ...prev,
            status: message.data.goal_status as ArchitectGoal['status']
          } : null);
        }
        break;

      case 'agent_update':
        if (message.data.agent) {
          setAgents(prev => {
            const existingIndex = prev.findIndex(a => a.id === message.data.agent!.id);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = message.data.agent!;
              return updated;
            } else {
              return [...prev, message.data.agent!];
            }
          });
        }
        break;

      case 'output_update':
        if (message.data.output) {
          setOutputs(prev => [...prev, message.data.output!]);
          
          // Auto-switch to dashboard when outputs start coming in
          if (activePanel === 'input' && currentGoal?.status !== 'pending') {
            setActivePanel('dashboard');
          }
        }
        break;

      case 'error':
        setProcessingError(message.data.error || 'Unknown error occurred');
        break;

      case 'heartbeat':
        setLastHeartbeat(new Date());
        break;

      default:
        console.log('Unknown WebSocket message type:', message.event);
    }
  }, [activePanel, currentGoal]);

  // Initialize WebSocket connection
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, []);

  // Fetch system status periodically
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await fetch('http://localhost:8001/api/health');
        if (response.ok) {
          const status = await response.json();
          setSystemStatus(status);
        }
      } catch (error) {
        console.error('Failed to fetch system status:', error);
      }
    };

    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Every 30 seconds

    return () => clearInterval(interval);
  }, []);

  // Goal submission handler
  const handleGoalSubmit = async (goalText: string, aiAnalysis?: string) => {
    setIsSubmitting(true);
    setProcessingError(null);

    try {
      const response = await fetch('http://localhost:8001/api/goals', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: goalText }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit goal');
      }

      const result = await response.json();
      
      // Create goal object with client-side analysis
      const newGoal: ArchitectGoal = {
        id: result.goal_id,
        text: goalText,
        status: 'pending',
        analysis: aiAnalysis,
        submitTime: new Date().toISOString(),
      };

      setCurrentGoal(newGoal);
      setAgents([]);
      setOutputs([]);
      setActivePanel('dashboard');

    } catch (error) {
      console.error('Goal submission error:', error);
      setProcessingError(error instanceof Error ? error.message : 'Failed to submit goal');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Panel navigation
  const navigationItems = [
    { id: 'input' as const, label: 'New Goal', isActive: activePanel === 'input' },
    { id: 'dashboard' as const, label: 'Architect', isActive: activePanel === 'dashboard', disabled: !currentGoal },
    { id: 'crew' as const, label: 'CrewAI', isActive: activePanel === 'crew' },
    { id: 'monitoring' as const, label: 'Monitoring', isActive: activePanel === 'monitoring' },
    { id: 'config' as const, label: 'Config', isActive: activePanel === 'config' }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white relative overflow-hidden">
      <StarryBackground />
      
      <div className="relative z-10 min-h-screen flex flex-col">
        <div className="container mx-auto px-4 py-6 flex-1">
          <Header onHelpClick={() => setIsHelpModalOpen(true)} />
          
          {/* Navigation */}
          <nav className="mt-6 mb-8">
            <div className="flex space-x-1 bg-gray-800/50 p-1 rounded-lg backdrop-blur-sm border border-gray-700/50">
              {navigationItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => !item.disabled && setActivePanel(item.id)}
                  disabled={item.disabled}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                    item.isActive
                      ? 'bg-pink-600 text-white shadow-sm'
                      : item.disabled
                      ? 'text-gray-500 cursor-not-allowed'
                      : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
                  }`}
                >
                  {item.label}
                  {item.id === 'crew' && (
                    <span className="ml-1 text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded-full">
                      NEW
                    </span>
                  )}
                </button>
              ))}
            </div>
          </nav>

          {/* Main Content */}
          <div className="relative">
            {activePanel === 'input' && (
              <GoalInputPanel 
                onSubmit={handleGoalSubmit}
                isSubmitting={isSubmitting}
                processingError={processingError}
              />
            )}
            
            {activePanel === 'dashboard' && (
              <ArchitectDashboard 
                currentGoal={currentGoal}
                agents={agents}
                outputs={outputs}
                processingError={processingError}
              />
            )}
            
            {activePanel === 'crew' && (
              <CrewAIWrapper />
            )}
            
            {activePanel === 'monitoring' && (
              <MonitoringPanel 
                systemStatus={systemStatus}
                wsConnection={wsConnection}
                lastHeartbeat={lastHeartbeat}
              />
            )}
            
            {activePanel === 'config' && (
              <ConfigPanel />
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="container mx-auto px-4 py-4 text-center text-xs text-gray-500 border-t border-gray-800">
          <p>Autonomous AI Architect v2.0 | 
            {wsConnection?.readyState === WebSocket.OPEN ? (
              <span className="text-green-400 ml-1">● Connected</span>
            ) : (
              <span className="text-red-400 ml-1">● Disconnected</span>
            )}
            <span className="ml-4 text-gray-600">
              Multi-Agent AI Orchestration with CrewAI Integration
            </span>
          </p>
        </footer>
      </div>

      {/* Help & Settings Modal */}
      {isHelpModalOpen && (
        <HelpSettingsModal onClose={() => setIsHelpModalOpen(false)} />
      )}
    </div>
  );
};

export default App;
