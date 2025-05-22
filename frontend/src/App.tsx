import React, { useState, useCallback, useEffect, useRef } from 'react';
import Header from './components/Header';
import GoalInputPanel from './components/GoalInputPanel';
import ArchitectDashboard from './components/ArchitectDashboard';
import MonitoringPanel from './components/MonitoringPanel';
import ConfigPanel from './components/ConfigPanel';
import HelpSettingsModal from './components/HelpSettingsModal';
import GemstoneCanvas from './components/GemstoneCanvas'; 
import StarryBackground from './components/StarryBackground';
import type { ArchitectGoal, Agent, ArchitectOutput, WebSocketMessage } from './types';
import { ViewMode } from './types';
import Button from './components/common/Button'; 
import Icon from './components/common/Icon'; 
import { ICON_QUESTION_MARK_CIRCLE } from './constants';
import { useBatchedUpdates, useOptimizedAgentUpdates } from './services/websocketOptimization';
import './components/styles/starry-background.css';

// App.tsx serves as the main application orchestrator
const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>(ViewMode.GOAL_INPUT);
  const [currentGoal, setCurrentGoal] = useState<ArchitectGoal | null>(null);
  const [goalId, setGoalId] = useState<string | null>(null); 
  const [isHelpModalOpen, setIsHelpModalOpen] = useState<boolean>(false);
  
  // Use optimized state management for WebSocket messages
  const [agents, setAgents, updateAgent] = useOptimizedAgentUpdates([]);
  const [outputs, setOutputs, batchAddOutputs] = useBatchedUpdates<ArchitectOutput>([], 150);
  const [processingError, setProcessingError] = useState<string | null>(null); 

  const ws = useRef<WebSocket | null>(null);
  const activeGoalIdForWs = useRef<string | null>(null); // Tracks the goal ID for the current WebSocket

  const handleNavigate = useCallback((view: ViewMode) => {
    if (view === ViewMode.HELP_SETTINGS) {
      setIsHelpModalOpen(true);
    } else {
      setIsHelpModalOpen(false); 
      setCurrentView(view);
    }
  }, []);
  
  const closeHelpModal = useCallback(() => {
    setIsHelpModalOpen(false);
  }, []);

  const connectWebSocket = (currentGoalIdFromBackend: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN && activeGoalIdForWs.current !== currentGoalIdFromBackend) {
      console.log("Closing previous WebSocket for", activeGoalIdForWs.current, "before opening new for", currentGoalIdFromBackend);
      ws.current.onclose = null; 
      ws.current.close();
      ws.current = null;
    } else if (ws.current && ws.current.readyState === WebSocket.OPEN && activeGoalIdForWs.current === currentGoalIdFromBackend) {
      console.log("WebSocket already open for current goal ID:", currentGoalIdFromBackend);
      return; // Already connected for this goal
    }
    
    activeGoalIdForWs.current = currentGoalIdFromBackend;

    const newWs = new WebSocket(`ws://localhost:8001/ws/logs/${currentGoalIdFromBackend}`);
    ws.current = newWs;
    console.log("Attempting to connect WebSocket for goal ID:", currentGoalIdFromBackend);

    newWs.onopen = () => {
      if (activeGoalIdForWs.current !== currentGoalIdFromBackend) {
        console.warn("WebSocket opened for a stale goal ID. Closing.", currentGoalIdFromBackend, activeGoalIdForWs.current);
        newWs.close();
        return;
      }
      console.log("WebSocket connected for goal ID:", currentGoalIdFromBackend);
      setOutputs(prev => {
        const newLog = { type: 'log', title: 'WebSocket Status', content: `Connected to Architect Core (Goal ID: ${currentGoalIdFromBackend}).`, timestamp: new Date(), sourceAgent: 'System', level: 'INFO' } as ArchitectOutput;
        return [...prev.filter(o => o.sourceAgent !== 'WebSocket_Connection_Placeholder'), newLog];
      });
    };

    // Helper to handle WebSocket messages and prevent UI freezing with high message volumes
    let pendingLogMessages: ArchitectOutput[] = [];
    let logMessageThrottleTimeout: number | null = null;

    const processPendingLogMessages = () => {
      if (pendingLogMessages.length > 0) {
        batchAddOutputs(pendingLogMessages);
        pendingLogMessages = [];
      }
      logMessageThrottleTimeout = null;
    };

    newWs.onmessage = (event) => {
      if (activeGoalIdForWs.current !== currentGoalIdFromBackend) {
        console.warn("WebSocket message received for a stale goal ID. Ignoring.", event.data, "Stale Goal ID:", currentGoalIdFromBackend, "Active WS Goal ID:", activeGoalIdForWs.current);
        return;
      }
      // Clean up any pending log message timeouts
      if (logMessageThrottleTimeout) {
        clearTimeout(logMessageThrottleTimeout);
        processPendingLogMessages(); // Process any remaining pending messages
      }
      
      try {
        // Handle potential message format issues
        let message: WebSocketMessage;
        try {
          message = JSON.parse(event.data as string);
        } catch (parseError) {
          console.error("Error parsing WebSocket message:", parseError);
          setOutputs(prev => [...prev, { 
            type: 'log', 
            title: 'Message Format Error', 
            content: `Failed to parse message from backend: ${typeof event.data === 'string' ? event.data.substring(0, 100) + '...' : 'Non-string data'}`, 
            timestamp: new Date(), 
            sourceAgent: 'System', 
            level: 'ERROR' 
          } as ArchitectOutput]);
          return;
        }

        // Validate required fields
        if (!message.type) {
          console.error("WebSocket message missing required 'type' field:", message);
          return;
        }

        if (message.goal_id !== currentGoalIdFromBackend) {
          console.warn("Message goal_id mismatch. Current:", currentGoalIdFromBackend, "Msg:", message.goal_id, ". Ignoring.");
          return;
        }
        
        switch (message.type) {
          case 'log':
            // Batch log messages to prevent UI freezing with high volume
            const logOutput = { 
              ...message, 
              type: 'log', 
              title: `Log: ${message.source || 'System'}`, 
              timestamp: new Date(message.timestamp) 
            } as ArchitectOutput;
            
            pendingLogMessages.push(logOutput);
            
            // Process immediately for important messages
            if (message.level === 'ERROR' || message.level === 'WARNING') {
              processPendingLogMessages();
            } 
            // Or throttle for regular messages
            else if (logMessageThrottleTimeout === null) {
              logMessageThrottleTimeout = window.setTimeout(processPendingLogMessages, 150);
            }
            break;
          case 'agent_update':
            updateAgent({ ...message.agent });
            break;
          case 'output_artifact':
            setOutputs(prev => [...prev, { 
              ...message.output, 
              timestamp: new Date(message.output.timestamp) 
            } as ArchitectOutput]);
            break;
          case 'goal_status_update':
            setCurrentGoal(g => g && g.id === message.goal_id ? {...g, status: message.status, processingError: message.error_message || g.processingError || null } : g);
            if (message.status === 'error' && message.error_message && goalId === message.goal_id) {
                setProcessingError(message.error_message);
            } else if (message.status !== 'error' && goalId === message.goal_id) {
                setProcessingError(null);
            }
            if (message.status === 'completed' || message.status === 'error') {
                if (ws.current && ws.current.readyState === WebSocket.OPEN && activeGoalIdForWs.current === message.goal_id) {
                    console.log(`Goal ${message.status}, closing WebSocket for goal ID: ${message.goal_id}`);
                    ws.current.onclose = null; 
                    ws.current.close();
                    activeGoalIdForWs.current = null;
                }
            }
            break;
          case 'error':
             const generalErrorMsg = `Backend Error: ${message.message}`;
             setOutputs(prev => [...prev, { type: 'log', title: 'Backend Error', content: generalErrorMsg, timestamp: new Date(message.timestamp), sourceAgent: 'System', level: 'ERROR' } as ArchitectOutput]);
             if (message.goal_id && message.goal_id === goalId) {
                setCurrentGoal(g => g ? { ...g, status: 'error', processingError: message.message } : null);
             }
             setProcessingError(generalErrorMsg);
             break;
          default:
            console.warn("Received unknown WebSocket message type:", message);
        }

      } catch (error) {
        console.error("Error processing WebSocket message:", error);
        const rawData = typeof event.data === 'string' ? event.data.substring(0, 100) + '...' : 'Non-string data';
        setOutputs(prev => [...prev, { type: 'log', title: 'WebSocket Error', content: `Error processing message data: ${rawData}`, timestamp: new Date(), sourceAgent: 'System', level: 'ERROR' } as ArchitectOutput]);
      }
    };

    newWs.onclose = (event) => {
      // Log disconnect only if it's for the *truly* active goal's WS and wasn't explicitly closed by terminal state
      if (activeGoalIdForWs.current === currentGoalIdFromBackend && currentGoal?.status !== 'completed' && currentGoal?.status !== 'error') {
        console.log("WebSocket disconnected for goal ID:", currentGoalIdFromBackend, "Reason:", event.reason, "Code:", event.code);
        const logMessage = `WebSocket to Architect Core disconnected. Code: ${event.code}, Reason: ${event.reason || 'No reason'}. Updates may not be received.`;
        setOutputs(prev => [...prev, { type: 'log', title: 'WebSocket Status', content: logMessage, timestamp: new Date(), sourceAgent: 'System', level: 'WARNING' } as ArchitectOutput]);
        
        // Attempt to reconnect if this was an abnormal closure and we're not in a terminal state
        if (event.code !== 1000 && event.code !== 1001) {
          setTimeout(() => {
            if (activeGoalIdForWs.current === currentGoalIdFromBackend && 
                (!currentGoal || (currentGoal.status !== 'completed' && currentGoal.status !== 'error'))) {
              console.log("Attempting to reconnect WebSocket for goal ID:", currentGoalIdFromBackend);
              setOutputs(prev => [...prev, { 
                type: 'log', 
                title: 'WebSocket Status', 
                content: 'Attempting to reconnect to Architect Core...', 
                timestamp: new Date(), 
                sourceAgent: 'System', 
                level: 'INFO' 
              } as ArchitectOutput]);
              connectWebSocket(currentGoalIdFromBackend);
            }
          }, 2000); // Wait 2 seconds before reconnecting
        }
      }
      // Do not clear activeGoalIdForWs.current here as it helps identify stale messages if a reconnect is attempted.
      // It gets cleared when a new connection starts or on explicit close.
      if (ws.current === newWs) { // Only nullify ws.current if it's this specific instance
        ws.current = null;
      }
    };

    newWs.onerror = (errorEvent) => {
      if (activeGoalIdForWs.current !== currentGoalIdFromBackend) {
        console.warn("WebSocket error for a stale goal ID. Ignoring.", currentGoalIdFromBackend, activeGoalIdForWs.current);
        return;
      }
      console.error("WebSocket error for goal ID:", currentGoalIdFromBackend, errorEvent);
      const errorMessage = 'WebSocket connection error with Architect Core.';
      setOutputs(prev => {
        const phExists = prev.find(o => o.sourceAgent === 'WebSocket_Connection_Placeholder');
        if (phExists) return prev.map(o => o.sourceAgent === 'WebSocket_Connection_Placeholder' ? {...o, title: 'WebSocket Error', content: errorMessage, level: 'ERROR'} as ArchitectOutput : o);
        return [...prev, { type: 'log', title: 'WebSocket Error', content: errorMessage, timestamp: new Date(), sourceAgent: 'System', level: 'ERROR' } as ArchitectOutput];
      });
      if (currentGoal && currentGoal.id === currentGoalIdFromBackend) {
        setCurrentGoal(g => g ? { ...g, status: 'error', processingError: errorMessage } : g);
        setProcessingError(errorMessage);
      }
    };
  };

  const handleGoalSubmit = useCallback(async (goalText: string, analysis?: string) => {
    setProcessingError(null); 
    const tempFrontendGoalId = 'frontend-goal-' + Date.now().toString();
    
    const newGoalInitialState: ArchitectGoal = {
      id: tempFrontendGoalId, 
      text: goalText,
      analysis: analysis,
      status: 'pending',
    };
    setCurrentGoal(newGoalInitialState);
    setGoalId(tempFrontendGoalId); // Set global goalId to frontend's temp ID
    
    // Reset for new goal submission
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("Closing existing WebSocket for new goal submission.");
      ws.current.onclose = null; // Prevent old onclose logic
      ws.current.close();
      ws.current = null;
    }
    activeGoalIdForWs.current = null; // Clear active WS goal ID ref explicitly

    setCurrentView(ViewMode.DASHBOARD); 
    setIsHelpModalOpen(false);
    setAgents([]); 
    setOutputs([
        { type: 'log', title: 'Vision Submission', content: `Transmitting vision: "${goalText}"`, timestamp: new Date(), sourceAgent: 'Frontend', level: 'INFO' } as ArchitectOutput,
        { type: 'log', title: 'System', content: 'Attempting backend connection...', timestamp: new Date(), sourceAgent: 'WebSocket_Connection_Placeholder', level: 'INFO' } as ArchitectOutput
    ]);

    try {
      setCurrentGoal(g => g ? { ...g, status: 'processing' } : null);

      const response = await fetch('http://localhost:8001/api/process_goal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goalText, analysis: analysis || "" }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error during backend goal processing initialization." }));
        throw new Error(errorData.detail || `HTTP error ${response.status}`);
      }

      const result = await response.json();
      const receivedBackendGoalId = result.goal_id as string;
      
      setGoalId(receivedBackendGoalId); 
      setCurrentGoal(g => g ? { ...g, id: receivedBackendGoalId, status: 'processing' } : null);
      
      setOutputs(prev => prev.map(o => o.sourceAgent === 'WebSocket_Connection_Placeholder' ? 
        { ...o, content: `Backend Goal ID: ${receivedBackendGoalId}. Establishing real-time link...`, level: 'INFO' } as ArchitectOutput : o
      ));
      connectWebSocket(receivedBackendGoalId);

    } catch (error) {
      console.error("Error submitting goal to backend:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error during goal submission.";
      setCurrentGoal(g => g ? { ...g, status: 'error', processingError: `Submission failed: ${errorMessage}` } : null);
      setProcessingError(`Submission failed: ${errorMessage}`);
      setOutputs(prev => prev.map(o => o.sourceAgent === 'WebSocket_Connection_Placeholder' ? 
        { ...o, title: 'Submission Error', content: `Error: ${errorMessage}`, level: 'ERROR' } as ArchitectOutput : o
      ).filter(o => o.sourceAgent !== 'WebSocket_Connection_Placeholder' || o.level === 'ERROR'));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 
  
  useEffect(() => { // Cleanup WebSocket on component unmount or when goalId (backend confirmed) changes
    const currentWsInstance = ws.current;
    return () => {
      if (currentWsInstance && currentWsInstance.readyState === WebSocket.OPEN) {
        console.log("Cleaning up WebSocket on unmount/goalId change. Goal ID was:", currentWsInstance.url.split('/').pop());
        currentWsInstance.onclose = null;
        currentWsInstance.close();
      }
      // activeGoalIdForWs.current should be cleared when initiating a new connection or on explicit close.
    };
  }, [goalId]); 

  const renderView = () => {
    switch (currentView) {
      case ViewMode.GOAL_INPUT:
        return <GoalInputPanel onGoalSubmit={handleGoalSubmit} currentGoal={currentGoal} />;
      case ViewMode.DASHBOARD:
        return <ArchitectDashboard currentGoal={currentGoal} agents={agents} outputs={outputs} processingError={processingError || currentGoal?.processingError} />;
      case ViewMode.MONITORING:
        return <MonitoringPanel />;
      case ViewMode.CONFIG:
        return <ConfigPanel />;
      default: 
        return <GoalInputPanel onGoalSubmit={handleGoalSubmit} currentGoal={currentGoal} />;
    }
  };

  const HEADER_HEIGHT = "60px"; // Approximate header height (adjust based on actual Header.tsx styling)
  const FOOTER_HEIGHT_APPROX = "60px"; // Estimated space for fixed footer

  return (
    <div className="min-h-screen flex flex-col text-gray-200 relative overflow-y-auto custom-scrollbar">
      {/* Apply the starry background as a fixed element */}
      <StarryBackground />
      
      <Header currentView={currentView} onNavigate={handleNavigate} />
      
      <main 
        className="relative w-full max-w-full mx-auto flex flex-col lg:flex-row items-stretch justify-center flex-grow"
        style={{ paddingTop: HEADER_HEIGHT, paddingBottom: FOOTER_HEIGHT_APPROX }}
      >
        {/* Left Column: Main Content Area */}
        <div className="lg:w-[60%] xl:w-[55%] w-full p-3 md:p-4 flex flex-col justify-start animate-fade-in z-10 overflow-y-auto custom-scrollbar" style={{maxHeight: `calc(100vh - ${HEADER_HEIGHT} - ${FOOTER_HEIGHT_APPROX})` }}>
           <div className="w-full max-w-3xl mx-auto mt-1 lg:mt-3"> 
            <h1 className="text-3xl md:text-4xl lg:text-5xl text-white font-bold mb-6 heading-font">
              Autonomous AI Architect
            </h1>
            <p className="text-xl text-gray-300 mb-8">
              Turn your vision into reality with AI-powered development.
            </p>
            {renderView()}
          </div>
        </div>

        {/* Right Column: Gemstone Visualization (Sticky on large screens) */}
        <div 
          className="lg:w-[40%] xl:w-[45%] w-full mt-4 lg:mt-0 flex items-center justify-center min-h-[250px] sm:min-h-[300px] md:min-h-[400px] lg:min-h-0 z-0 p-2 lg:sticky"
          style={{ top: HEADER_HEIGHT, height: `calc(100vh - ${HEADER_HEIGHT})`}} // Make sticky below header
        >
          <GemstoneCanvas />
        </div>
      </main>
      
      <HelpSettingsModal isOpen={isHelpModalOpen} onClose={closeHelpModal} />
      
      <footer className="fixed bottom-2 right-2 md:bottom-3 md:right-3 z-30 space-y-1.5 flex flex-col items-end" aria-label="Application Footer">
        <Button 
            onClick={() => handleNavigate(ViewMode.HELP_SETTINGS)}
            variant="primary"
            size="sm" 
            className="!px-3 !py-1.5 md:!px-3.5 md:!py-2 shadow-lg !rounded-full bg-pink-600 hover:bg-pink-700"
            leftIcon={<Icon path={ICON_QUESTION_MARK_CIRCLE} />}
            aria-label="Help and Settings"
        >
            Help
        </Button>
        <div className="text-xs text-gray-400/70 text-right bg-black/50 backdrop-blur-sm px-2 py-0.5 rounded-md shadow">
            <p>© {new Date().getFullYear()} AI Architect.</p>
            <p className="text-gray-500/80">Gemstone V3</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
