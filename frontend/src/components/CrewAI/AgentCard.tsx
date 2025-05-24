import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  UserIcon,
  CogIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  WrenchScrewdriverIcon
} from '@heroicons/react/24/outline';
import type { CrewAgent } from '../../types/crewai';

interface AgentCardProps {
  agent: CrewAgent;
  isSelected: boolean;
  onSelect: () => void;
  onAction: (action: 'pause' | 'resume' | 'reset') => void;
  className?: string;
}

const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  isSelected,
  onSelect,
  onAction,
  className = ''
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'executing':
      case 'thinking':
        return 'bg-blue-500';
      case 'collaborating':
        return 'bg-purple-500';
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'idle':
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executing':
        return <PlayIcon className="w-4 h-4" />;
      case 'thinking':
        return <CogIcon className="w-4 h-4 animate-spin" />;
      case 'collaborating':
        return <UserIcon className="w-4 h-4" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4" />;
      case 'error':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      default:
        return <PauseIcon className="w-4 h-4" />;
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      className={`agent-card glass-card p-6 cursor-pointer transition-all ${
        isSelected ? 'ring-2 ring-blue-500' : ''
      } ${className}`}
      onClick={onSelect}
    >
      {/* Agent Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
              <UserIcon className="w-6 h-6 text-white" />
            </div>
            <div className={`absolute -bottom-1 -right-1 w-4 h-4 ${getStatusColor(agent.status)} rounded-full flex items-center justify-center`}>
              {getStatusIcon(agent.status)}
            </div>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
            <p className="text-sm text-gray-400">{agent.role}</p>
          </div>
        </div>
        
        <div className="flex space-x-1">
          {agent.status === 'executing' || agent.status === 'thinking' ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction('pause');
              }}
              className="p-1 hover:bg-white/10 rounded"
            >
              <PauseIcon className="w-4 h-4 text-gray-400" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction('resume');
              }}
              className="p-1 hover:bg-white/10 rounded"
            >
              <PlayIcon className="w-4 h-4 text-gray-400" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAction('reset');
            }}
            className="p-1 hover:bg-white/10 rounded"
          >
            <ArrowPathIcon className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Current Task */}
      {agent.current_task && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-400">Current Task</span>
          </div>
          <p className="text-sm text-gray-300 bg-black/20 rounded p-2">
            {agent.current_task}
          </p>
        </div>
      )}

      {/* Agent Goal */}
      <div className="mb-4">
        <p className="text-sm text-gray-300">{agent.goal}</p>
      </div>

      {/* Performance Metrics */}
      {agent.performance_metrics && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="text-center">
            <div className="text-lg font-bold text-green-400">
              {agent.performance_metrics.tasks_completed}
            </div>
            <div className="text-xs text-gray-400">Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-blue-400">
              {Math.round(agent.performance_metrics.success_rate * 100)}%
            </div>
            <div className="text-xs text-gray-400">Success</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-purple-400">
              {Math.round(agent.performance_metrics.avg_execution_time)}s
            </div>
            <div className="text-xs text-gray-400">Avg Time</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-orange-400">
              {Math.round(agent.performance_metrics.collaboration_score * 100)}%
            </div>
            <div className="text-xs text-gray-400">Collab</div>
          </div>
        </div>
      )}

      {/* Tools and Capabilities */}
      <div className="space-y-3">
        <div>
          <div className="flex items-center space-x-2 mb-2">
            <WrenchScrewdriverIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-400">Tools ({agent.tools.length})</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {agent.tools.slice(0, 3).map((tool, index) => (
              <span
                key={index}
                className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded"
              >
                {tool}
              </span>
            ))}
            {agent.tools.length > 3 && (
              <span className="text-xs text-gray-400">
                +{agent.tools.length - 3} more
              </span>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center space-x-2 mb-2">
            <ChartBarIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs font-medium text-gray-400">Capabilities</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {agent.capabilities.slice(0, 2).map((capability, index) => (
              <span
                key={index}
                className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded"
              >
                {capability}
              </span>
            ))}
            {agent.capabilities.length > 2 && (
              <span className="text-xs text-gray-400">
                +{agent.capabilities.length - 2} more
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Detailed View Toggle */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setShowDetails(!showDetails);
        }}
        className="w-full mt-4 text-xs text-gray-400 hover:text-white transition-colors"
      >
        {showDetails ? 'Show Less' : 'Show Details'}
      </button>

      {/* Detailed Information */}
      {showDetails && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 pt-4 border-t border-gray-700"
        >
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium text-white mb-1">Backstory</h4>
              <p className="text-xs text-gray-300">{agent.backstory}</p>
            </div>
            
            {agent.memory_context && (
              <div>
                <h4 className="text-sm font-medium text-white mb-1">Memory Context</h4>
                <p className="text-xs text-gray-300 bg-black/20 rounded p-2">
                  {agent.memory_context}
                </p>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-400">Created:</span>
                <div className="text-white">
                  {new Date(agent.created_at).toLocaleDateString()}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Updated:</span>
                <div className="text-white">
                  {new Date(agent.updated_at).toLocaleTimeString()}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default AgentCard;
