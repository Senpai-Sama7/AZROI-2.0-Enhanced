import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  PlayIcon,
  PauseIcon,
  StopIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import type { CrewSession } from '../../types/crewai';

interface SessionControlsProps {
  session: CrewSession;
  onAction: (action: 'start' | 'pause' | 'stop' | 'restart') => void;
  className?: string;
}

const SessionControls: React.FC<SessionControlsProps> = ({
  session,
  onAction,
  className = ''
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleAction = async (action: 'start' | 'pause' | 'stop' | 'restart') => {
    setIsProcessing(true);
    try {
      await onAction(action);
    } finally {
      setTimeout(() => setIsProcessing(false), 1000);
    }
  };

  const getActionButton = () => {
    switch (session.status) {
      case 'planning':
      case 'paused':
        return {
          action: 'start' as const,
          icon: PlayIcon,
          label: 'Start Session',
          color: 'bg-green-500 hover:bg-green-600'
        };
      case 'executing':
        return {
          action: 'pause' as const,
          icon: PauseIcon,
          label: 'Pause Session',
          color: 'bg-yellow-500 hover:bg-yellow-600'
        };
      case 'completed':
      case 'failed':
        return {
          action: 'restart' as const,
          icon: ArrowPathIcon,
          label: 'Restart Session',
          color: 'bg-blue-500 hover:bg-blue-600'
        };
      default:
        return {
          action: 'start' as const,
          icon: PlayIcon,
          label: 'Start Session',
          color: 'bg-green-500 hover:bg-green-600'
        };
    }
  };

  const primaryAction = getActionButton();
  const PrimaryIcon = primaryAction.icon;

  return (
    <div className={`session-controls ${className}`}>
      <div className="flex items-center space-x-4">
        {/* Primary Action Button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => handleAction(primaryAction.action)}
          disabled={isProcessing}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium text-white transition-colors ${primaryAction.color} ${
            isProcessing ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isProcessing ? (
            <Cog6ToothIcon className="w-5 h-5 animate-spin" />
          ) : (
            <PrimaryIcon className="w-5 h-5" />
          )}
          <span>{primaryAction.label}</span>
        </motion.button>

        {/* Secondary Actions */}
        <div className="flex items-center space-x-2">
          {session.status === 'executing' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleAction('stop')}
              disabled={isProcessing}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-white bg-red-500 hover:bg-red-600 transition-colors"
            >
              <StopIcon className="w-4 h-4" />
              <span>Stop</span>
            </motion.button>
          )}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-gray-300 bg-gray-600 hover:bg-gray-700 transition-colors"
          >
            <Cog6ToothIcon className="w-4 h-4" />
            <span>Settings</span>
          </motion.button>
        </div>

        {/* Session Info */}
        <div className="flex-1 flex items-center justify-end space-x-6 text-sm text-gray-300">
          <div className="flex items-center space-x-2">
            <ChartBarIcon className="w-4 h-4" />
            <span>Iteration {session.current_iteration} / {session.max_iterations}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-green-400" />
            <span>{session.agents.filter(a => a.status !== 'idle').length} active agents</span>
          </div>

          <div className="flex items-center space-x-2">
            <span>Progress: {session.progress_percentage}%</span>
            <div className="w-20 bg-gray-700 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${session.progress_percentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 p-4 bg-black/30 rounded-lg border border-gray-600"
        >
          <SessionSettingsPanel session={session} onClose={() => setShowSettings(false)} />
        </motion.div>
      )}
    </div>
  );
};

// Session Settings Panel Component
const SessionSettingsPanel: React.FC<{
  session: CrewSession;
  onClose: () => void;
}> = ({ session, onClose }) => {
  const [settings, setSettings] = useState({
    maxIterations: session.max_iterations,
    workflow: session.workflow,
    autoRestart: false,
    verboseLogging: true,
    collaborationTimeout: 30,
    taskTimeout: 300
  });

  const handleSave = () => {
    // TODO: Implement settings save
    console.log('Saving session settings:', settings);
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Session Settings</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Max Iterations
          </label>
          <input
            type="number"
            value={settings.maxIterations}
            onChange={(e) => setSettings(prev => ({ ...prev, maxIterations: parseInt(e.target.value) }))}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            min="1"
            max="100"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Workflow Type
          </label>
          <select
            value={settings.workflow}
            onChange={(e) => setSettings(prev => ({ ...prev, workflow: e.target.value as any }))}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option value="sequential">Sequential</option>
            <option value="hierarchical">Hierarchical</option>
            <option value="consensus">Consensus</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Collaboration Timeout (seconds)
          </label>
          <input
            type="number"
            value={settings.collaborationTimeout}
            onChange={(e) => setSettings(prev => ({ ...prev, collaborationTimeout: parseInt(e.target.value) }))}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            min="10"
            max="300"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Task Timeout (seconds)
          </label>
          <input
            type="number"
            value={settings.taskTimeout}
            onChange={(e) => setSettings(prev => ({ ...prev, taskTimeout: parseInt(e.target.value) }))}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            min="60"
            max="3600"
          />
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="autoRestart"
            checked={settings.autoRestart}
            onChange={(e) => setSettings(prev => ({ ...prev, autoRestart: e.target.checked }))}
            className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded"
          />
          <label htmlFor="autoRestart" className="text-sm text-gray-300">
            Auto-restart on completion
          </label>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="verboseLogging"
            checked={settings.verboseLogging}
            onChange={(e) => setSettings(prev => ({ ...prev, verboseLogging: e.target.checked }))}
            className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded"
          />
          <label htmlFor="verboseLogging" className="text-sm text-gray-300">
            Enable verbose logging
          </label>
        </div>
      </div>

      <div className="flex space-x-3 pt-4 border-t border-gray-700">
        <button
          onClick={handleSave}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
        >
          Save Settings
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default SessionControls;
