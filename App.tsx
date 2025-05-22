import React, { useState, useCallback, useEffect } from 'react';
import Header from './components/Header';
import GoalInputPanel from './components/GoalInputPanel';
import ArchitectDashboard from './components/ArchitectDashboard';
import MonitoringPanel from './components/MonitoringPanel';
import ConfigPanel from './components/ConfigPanel';
import HelpSettingsModal from './components/HelpSettingsModal';
import AnimatedSpaceBackground from './components/AnimatedSpaceBackground'; // Import the new background
import type { ArchitectGoal, Agent, ArchitectOutput } from './types';
import { ViewMode } from './types'; 

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>(ViewMode.GOAL_INPUT);
  const [currentGoal, setCurrentGoal] = useState<ArchitectGoal | null>(null);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState<boolean>(false);
  
  const [agents, setAgents] = useState<Agent[]>([]);
  const [outputs, setOutputs] = useState<ArchitectOutput[]>([]);

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

  const handleGoalSubmit = useCallback((goalText: string, analysis?: string) => {
    const newGoal: ArchitectGoal = {
      id: Date.now().toString(),
      text: goalText,
      analysis: analysis,
      status: 'processing',
    };
    setCurrentGoal(newGoal);
    setCurrentView(ViewMode.DASHBOARD); 
    setIsHelpModalOpen(false);

    setAgents([
      { id: '1', name: 'Project Manager', role: 'Manages overall project flow', status: 'active', currentTask: 'Decomposing main goal into sub-tasks.' },
      { id: '2', name: 'Lead Architect', role: 'Designs system architecture', status: 'idle' },
    ]);
    setOutputs([{ type: 'log', title: 'Goal Received', content: `New goal set: ${goalText}`, timestamp: new Date() }]);

    setTimeout(() => {
      setAgents(prev => prev.map(a => a.id === '1' ? {...a, status: 'completed', currentTask: 'Goal decomposition complete.'} : a));
      setAgents(prev => prev.map(a => a.id === '2' ? {...a, status: 'active', currentTask: 'Designing initial architecture based on decomposed tasks.'} : a));
      setOutputs(prev => [...prev, { type: 'log', title: 'Project Manager Update', content: 'Project Manager completed goal decomposition.', timestamp: new Date() }]);
      setOutputs(prev => [...prev, { type: 'plan', title: 'Initial Project Plan', content: '1. Define microservice endpoints.\n2. Select database technology.\n3. Design CI/CD pipeline.', timestamp: new Date() }]);
    }, 3000);

    setTimeout(() => {
       setAgents(prev => prev.map(a => a.id === '2' ? {...a, status: 'completed', currentTask: 'Initial architecture designed.'} : a));
       setCurrentGoal(g => g ? {...g, status: 'completed'} : null);
       setOutputs(prev => [...prev, { type: 'log', title: 'Lead Architect Update', content: 'Lead Architect completed initial design.', timestamp: new Date() }]);
       setOutputs(prev => [...prev, { type: 'report', title: 'Architecture Overview', content: 'System will use FastAPI, React, and PostgreSQL, deployed on Cloud Run.', timestamp: new Date() }]);
    }, 6000);

  }, []);
  
  useEffect(() => {
    if (currentGoal && currentGoal.status === 'pending') { 
        setAgents([]);
        setOutputs([]);
    }
  }, [currentGoal]);

  const renderView = () => {
    switch (currentView) {
      case ViewMode.GOAL_INPUT:
        return <GoalInputPanel onGoalSubmit={handleGoalSubmit} currentGoal={currentGoal} />;
      case ViewMode.DASHBOARD:
        return <ArchitectDashboard currentGoal={currentGoal} agents={agents} outputs={outputs} />;
      case ViewMode.MONITORING:
        return <MonitoringPanel />;
      case ViewMode.CONFIG:
        return <ConfigPanel />;
      default:
        return <GoalInputPanel onGoalSubmit={handleGoalSubmit} currentGoal={currentGoal} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-transparent text-gem-light-achromatic relative"> {/* Changed bg to transparent */}
      <AnimatedSpaceBackground /> {/* Add the animated background */}
      <Header currentView={currentView} onNavigate={handleNavigate} />
      <main className="flex-grow container mx-auto p-4 sm:p-6 lg:p-8 animate-fade-in relative z-10"> {/* Ensure main content is above background */}
        {renderView()}
      </main>
      <HelpSettingsModal isOpen={isHelpModalOpen} onClose={closeHelpModal} />
      <footer className="text-center p-6 text-xs text-gem-muted-grey border-t border-gem-ebony-surface/30 relative z-10 bg-gem-ebony/70 backdrop-blur-xs">
        © {new Date().getFullYear()} Autonomous AI Architect UI. <span className="iridescent-text opacity-80">Crafted with precision and vision.</span>
      </footer>
    </div>
  );
};

export default App;