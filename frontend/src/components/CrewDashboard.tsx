import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  PlayIcon, 
  PauseIcon, 
  StopIcon, 
  CogIcon,
  ChartBarIcon,
  UsersIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import type { CrewSession, CrewAgent, CrewTask, CrewMetrics } from '../types/crewai';
import AgentCard from './CrewAI/AgentCard';
import TaskBoard from './CrewAI/TaskBoard';
import CollaborationGraph from './CrewAI/CollaborationGraph';
import MetricsPanel from './CrewAI/MetricsPanel';
import SessionControls from './CrewAI/SessionControls';

interface CrewDashboardProps {
  session: CrewSession | null;
  metrics: CrewMetrics | null;
  onSessionAction: (action: 'start' | 'pause' | 'stop' | 'restart') => void;
  onAgentAction: (agentId: string, action: 'pause' | 'resume' | 'reset') => void;
  onTaskAction: (taskId: string, action: 'retry' | 'skip' | 'prioritize') => void;
  className?: string;
}

const CrewDashboard: React.FC<CrewDashboardProps> = ({
  session,
  metrics,
  onSessionAction,
  onAgentAction,
  onTaskAction,
  className = ''
}) => {
  const [activeView, setActiveView] = useState<'overview' | 'agents' | 'tasks' | 'collaboration' | 'metrics'>('overview');
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'executing':
      case 'in_progress':
        return 'text-blue-400';
      case 'completed':
        return 'text-green-400';
      case 'failed':
      case 'error':
        return 'text-red-400';
      case 'paused':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executing':
      case 'in_progress':
        return <PlayIcon className="w-4 h-4" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4" />;
      case 'failed':
      case 'error':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      case 'paused':
        return <PauseIcon className="w-4 h-4" />;
      default:
        return <InformationCircleIcon className="w-4 h-4" />;
    }
  };

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Session Header */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">
              {session?.name || 'No Active Session'}
            </h2>
            {session && (
              <p className="text-gray-300">{session.goal}</p>
            )}
          </div>
          {session && (
            <div className={`flex items-center space-x-2 ${getStatusColor(session.status)}`}>
              {getStatusIcon(session.status)}
              <span className="font-medium capitalize">{session.status}</span>
            </div>
          )}
        </div>

        {session && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <UsersIcon className="w-5 h-5 text-blue-400" />
                <span className="text-sm text-gray-300">Agents</span>
              </div>
              <div className="text-2xl font-bold text-white">{session.agents.length}</div>
            </div>
            
            <div className="bg-green-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <CheckCircleIcon className="w-5 h-5 text-green-400" />
                <span className="text-sm text-gray-300">Completed</span>
              </div>
              <div className="text-2xl font-bold text-white">
                {session.tasks.filter(t => t.status === 'completed').length}
              </div>
            </div>
            
            <div className="bg-purple-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <ChartBarIcon className="w-5 h-5 text-purple-400" />
                <span className="text-sm text-gray-300">Progress</span>
              </div>
              <div className="text-2xl font-bold text-white">{session.progress_percentage}%</div>
            </div>
            
            <div className="bg-orange-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <ClockIcon className="w-5 h-5 text-orange-400" />
                <span className="text-sm text-gray-300">Iteration</span>
              </div>
              <div className="text-2xl font-bold text-white">
                {session.current_iteration} / {session.max_iterations}
              </div>
            </div>
          </div>
        )}

        {session && <SessionControls session={session} onAction={onSessionAction} />}
      </div>

      {/* Quick Stats */}
      {session && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Active Agents</h3>
            <div className="space-y-3">
              {session.agents.slice(0, 3).map(agent => (
                <div key={agent.id} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      agent.status === 'executing' ? 'bg-blue-400' :
                      agent.status === 'completed' ? 'bg-green-400' :
                      agent.status === 'error' ? 'bg-red-400' : 'bg-gray-400'
                    }`} />
                    <span className="text-white font-medium">{agent.name}</span>
                  </div>
                  <span className="text-sm text-gray-400">{agent.role}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Recent Tasks</h3>
            <div className="space-y-3">
              {session.tasks
                .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                .slice(0, 3)
                .map(task => (
                  <div key={task.id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        task.status === 'in_progress' ? 'bg-blue-400' :
                        task.status === 'completed' ? 'bg-green-400' :
                        task.status === 'failed' ? 'bg-red-400' : 'bg-gray-400'
                      }`} />
                      <span className="text-white font-medium truncate max-w-[200px]">
                        {task.title}
                      </span>
                    </div>
                    <span className={`text-sm px-2 py-1 rounded ${
                      task.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                      task.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                      task.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {task.priority}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderContent = () => {
    if (!session) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <UsersIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Active Crew Session</h3>
            <p className="text-gray-400">Start a new crew session to begin collaborative AI work</p>
          </div>
        </div>
      );
    }

    switch (activeView) {
      case 'overview':
        return renderOverview();
      case 'agents':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {session.agents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                isSelected={selectedAgent === agent.id}
                onSelect={() => setSelectedAgent(agent.id)}
                onAction={(action) => onAgentAction(agent.id, action)}
              />
            ))}
          </div>
        );
      case 'tasks':
        return (
          <TaskBoard
            tasks={session.tasks}
            agents={session.agents}
            selectedTask={selectedTask}
            onTaskSelect={setSelectedTask}
            onTaskAction={onTaskAction}
          />
        );
      case 'collaboration':
        return (
          <CollaborationGraph
            agents={session.agents}
            tasks={session.tasks}
            sessionId={session.id}
          />
        );
      case 'metrics':
        return metrics ? (
          <MetricsPanel metrics={metrics} session={session} />
        ) : (
          <div className="text-center py-8">
            <ChartBarIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-400">No metrics data available</p>
          </div>
        );
      default:
        return renderOverview();
    }
  };

  return (
    <div className={`crew-dashboard ${className}`}>
      {/* Navigation Tabs */}
      <div className="mb-6">
        <nav className="flex space-x-1 bg-black/20 rounded-lg p-1">
          {[
            { id: 'overview', label: 'Overview', icon: InformationCircleIcon },
            { id: 'agents', label: 'Agents', icon: UsersIcon },
            { id: 'tasks', label: 'Tasks', icon: CheckCircleIcon },
            { id: 'collaboration', label: 'Collaboration', icon: CogIcon },
            { id: 'metrics', label: 'Metrics', icon: ChartBarIcon }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveView(id as any)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-all ${
                activeView === id
                  ? 'bg-blue-500 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white hover:bg-white/10'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeView}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {renderContent()}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default CrewDashboard;
