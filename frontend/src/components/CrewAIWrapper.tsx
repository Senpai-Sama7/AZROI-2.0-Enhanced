import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PlayIcon, PlusIcon } from '@heroicons/react/24/outline';
import CrewDashboard from './CrewDashboard';
import type { CrewSession, CrewMetrics } from '../types/crewai';
import { crewAPIService } from '../services/crewapi';

const CrewAIWrapper: React.FC = () => {
  const [sessions, setSessions] = useState<CrewSession[]>([]);
  const [currentSession, setCurrentSession] = useState<CrewSession | null>(null);
  const [metrics, setMetrics] = useState<CrewMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const sessionData = await crewAPIService.getSessions();
      setSessions(sessionData);
      
      // Set the most recent session as current if available
      if (sessionData.length > 0) {
        const latestSession = sessionData[sessionData.length - 1];
        setCurrentSession(latestSession);
        
        // Load metrics for the current session
        if (latestSession.id) {
          const sessionMetrics = await crewAPIService.getSessionMetrics(latestSession.id);
          setMetrics(sessionMetrics);
        }
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load CrewAI sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleSessionAction = async (action: 'start' | 'pause' | 'stop' | 'restart') => {
    if (!currentSession?.id) return;

    try {
      switch (action) {
        case 'start':
          await crewAPIService.startSession(currentSession.id);
          break;
        case 'pause':
          await crewAPIService.pauseSession(currentSession.id);
          break;
        case 'stop':
          await crewAPIService.stopSession(currentSession.id);
          break;
        case 'restart':
          // Stop then start
          await crewAPIService.stopSession(currentSession.id);
          await crewAPIService.startSession(currentSession.id);
          break;
      }
      
      // Reload session data
      await loadSessions();
    } catch (err) {
      console.error(`Failed to ${action} session:`, err);
      setError(err instanceof Error ? err.message : `Failed to ${action} session`);
    }
  };

  const handleAgentAction = async (agentId: string, action: 'pause' | 'resume' | 'reset') => {
    try {
      switch (action) {
        case 'pause':
          await crewAPIService.pauseAgent(agentId);
          break;
        case 'resume':
          await crewAPIService.resumeAgent(agentId);
          break;
        case 'reset':
          await crewAPIService.resetAgent(agentId);
          break;
      }
      
      // Reload session data
      await loadSessions();
    } catch (err) {
      console.error(`Failed to ${action} agent:`, err);
      setError(err instanceof Error ? err.message : `Failed to ${action} agent`);
    }
  };

  const handleTaskAction = async (taskId: string, action: 'retry' | 'skip' | 'prioritize') => {
    try {
      switch (action) {
        case 'retry':
          await crewAPIService.retryTask(taskId);
          break;
        case 'skip':
          await crewAPIService.skipTask(taskId);
          break;
        case 'prioritize':
          await crewAPIService.prioritizeTask(taskId);
          break;
      }
      
      // Reload session data
      await loadSessions();
    } catch (err) {
      console.error(`Failed to ${action} task:`, err);
      setError(err instanceof Error ? err.message : `Failed to ${action} task`);
    }
  };

  const createNewSession = () => {
    setShowCreateModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="w-8 h-8 border-2 border-pink-600 border-t-transparent rounded-full"
        />
        <span className="ml-3 text-gray-300">Loading CrewAI sessions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6 backdrop-blur-sm">
        <h3 className="text-red-400 font-semibold mb-2">CrewAI Error</h3>
        <p className="text-red-300 mb-4">{error}</p>
        <button
          onClick={loadSessions}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!currentSession && sessions.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-8 backdrop-blur-sm max-w-md mx-auto">
          <PlayIcon className="w-16 h-16 text-gray-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">Welcome to CrewAI</h3>
          <p className="text-gray-400 mb-6">
            Create your first crew session to start orchestrating AI agents working together.
          </p>
          <button
            onClick={createNewSession}
            className="flex items-center gap-2 mx-auto px-6 py-3 bg-pink-600 hover:bg-pink-700 text-white rounded-lg transition-colors"
          >
            <PlusIcon className="w-5 h-5" />
            Create New Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Session Selection Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">CrewAI Management</h2>
          <p className="text-gray-400">
            Orchestrate multiple AI agents working together on complex tasks
          </p>
        </div>
        <button
          onClick={createNewSession}
          className="flex items-center gap-2 px-4 py-2 bg-pink-600 hover:bg-pink-700 text-white rounded-lg transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Session
        </button>
      </div>

      {/* Session Info */}
      {currentSession && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">{currentSession.name}</h3>
              <p className="text-gray-400">{currentSession.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                currentSession.status === 'active' ? 'bg-green-500/20 text-green-400' :
                currentSession.status === 'paused' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {currentSession.status}
              </span>
              <select
                value={currentSession.id}
                onChange={(e) => {
                  const selectedSession = sessions.find(s => s.id === e.target.value);
                  setCurrentSession(selectedSession || null);
                }}
                className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1 text-white text-sm"
              >
                {sessions.map(session => (
                  <option key={session.id} value={session.id}>
                    {session.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* CrewAI Dashboard */}
      {currentSession && (
        <CrewDashboard
          session={currentSession}
          metrics={metrics}
          onSessionAction={handleSessionAction}
          onAgentAction={handleAgentAction}
          onTaskAction={handleTaskAction}
        />
      )}

      {/* Create Session Modal - placeholder for now */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">Create New Session</h3>
            <p className="text-gray-400 mb-4">
              Session creation UI will be implemented in the next update.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-pink-600 hover:bg-pink-700 text-white rounded-lg transition-colors"
              >
                Coming Soon
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrewAIWrapper;
