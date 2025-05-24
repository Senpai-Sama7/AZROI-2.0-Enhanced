import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ClockIcon,
  UserIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon,
  EyeIcon,
  FlagIcon
} from '@heroicons/react/24/outline';
import type { CrewTask, CrewAgent } from '../../types/crewai';

interface TaskBoardProps {
  tasks: CrewTask[];
  agents: CrewAgent[];
  selectedTask: string | null;
  onTaskSelect: (taskId: string) => void;
  onTaskAction: (taskId: string, action: 'retry' | 'skip' | 'prioritize') => void;
  className?: string;
}

const TaskBoard: React.FC<TaskBoardProps> = ({
  tasks,
  agents,
  selectedTask,
  onTaskSelect,
  onTaskAction,
  className = ''
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'created' | 'priority' | 'status'>('created');

  const agentMap = useMemo(() => {
    const map = new Map();
    agents.forEach(agent => map.set(agent.id, agent));
    return map;
  }, [agents]);

  const filteredAndSortedTasks = useMemo(() => {
    let filtered = tasks.filter(task => {
      if (filterStatus !== 'all' && task.status !== filterStatus) return false;
      if (filterPriority !== 'all' && task.priority !== filterPriority) return false;
      return true;
    });

    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'priority':
          const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        case 'status':
          return a.status.localeCompare(b.status);
        case 'created':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });
  }, [tasks, filterStatus, filterPriority, sortBy]);

  const tasksByStatus = useMemo(() => {
    const groups = {
      pending: tasks.filter(t => t.status === 'pending'),
      in_progress: tasks.filter(t => t.status === 'in_progress'),
      review: tasks.filter(t => t.status === 'review'),
      completed: tasks.filter(t => t.status === 'completed'),
      failed: tasks.filter(t => t.status === 'failed')
    };
    return groups;
  }, [tasks]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      case 'in_progress':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'review':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500 text-white';
      case 'high':
        return 'bg-orange-500 text-white';
      case 'medium':
        return 'bg-yellow-500 text-black';
      case 'low':
        return 'bg-green-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'in_progress':
        return <PlayIcon className="w-4 h-4" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4" />;
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      case 'review':
        return <EyeIcon className="w-4 h-4" />;
      default:
        return <ClockIcon className="w-4 h-4" />;
    }
  };

  const TaskCard: React.FC<{ task: CrewTask; isSelected: boolean }> = ({ task, isSelected }) => {
    const agent = agentMap.get(task.agent_id);
    const executionTime = task.execution_time ? `${Math.round(task.execution_time / 1000)}s` : null;

    return (
      <motion.div
        layout
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        whileHover={{ scale: 1.02 }}
        className={`task-card glass-card p-4 cursor-pointer transition-all ${
          isSelected ? 'ring-2 ring-blue-500' : ''
        }`}
        onClick={() => onTaskSelect(task.id)}
      >
        {/* Task Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(task.priority)}`}>
                {task.priority}
              </span>
              <div className={`flex items-center space-x-1 px-2 py-1 rounded text-xs border ${getStatusColor(task.status)}`}>
                {getStatusIcon(task.status)}
                <span className="capitalize">{task.status.replace('_', ' ')}</span>
              </div>
            </div>
            <h3 className="font-semibold text-white text-sm mb-1">{task.title}</h3>
            <p className="text-gray-300 text-xs line-clamp-2">{task.description}</p>
          </div>
          
          <div className="flex space-x-1 ml-2">
            {task.status === 'failed' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTaskAction(task.id, 'retry');
                }}
                className="p-1 hover:bg-white/10 rounded"
                title="Retry task"
              >
                <ArrowPathIcon className="w-4 h-4 text-gray-400" />
              </button>
            )}
            {task.status === 'pending' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTaskAction(task.id, 'prioritize');
                }}
                className="p-1 hover:bg-white/10 rounded"
                title="Prioritize task"
              >
                <FlagIcon className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </div>

        {/* Agent Assignment */}
        {agent && (
          <div className="flex items-center space-x-2 mb-3">
            <UserIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-300">{agent.name}</span>
            <span className="text-xs text-gray-500">({agent.role})</span>
          </div>
        )}

        {/* Dependencies */}
        {task.dependencies.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center space-x-1 mb-1">
              <ChevronRightIcon className="w-3 h-3 text-gray-400" />
              <span className="text-xs text-gray-400">Dependencies</span>
            </div>
            <div className="text-xs text-gray-500">
              {task.dependencies.length} task{task.dependencies.length !== 1 ? 's' : ''} required
            </div>
          </div>
        )}

        {/* Timing Information */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            {executionTime && (
              <div className="flex items-center space-x-1">
                <ClockIcon className="w-3 h-3" />
                <span>{executionTime}</span>
              </div>
            )}
            {task.tools_used && task.tools_used.length > 0 && (
              <span>{task.tools_used.length} tools</span>
            )}
          </div>
          <span>{new Date(task.created_at).toLocaleDateString()}</span>
        </div>

        {/* Progress Bar for In Progress Tasks */}
        {task.status === 'in_progress' && (
          <div className="mt-3">
            <div className="w-full bg-gray-700 rounded-full h-1">
              <div className="bg-blue-500 h-1 rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className={`task-board ${className}`}>
      {/* Controls */}
      <div className="mb-6 glass-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-300">Status:</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-black/30 border border-gray-600 rounded px-2 py-1 text-sm text-white"
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="review">Review</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-300">Priority:</label>
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="bg-black/30 border border-gray-600 rounded px-2 py-1 text-sm text-white"
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-300">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-black/30 border border-gray-600 rounded px-2 py-1 text-sm text-white"
            >
              <option value="created">Created</option>
              <option value="priority">Priority</option>
              <option value="status">Status</option>
            </select>
          </div>

          <div className="flex-1" />

          <div className="text-sm text-gray-300">
            {filteredAndSortedTasks.length} of {tasks.length} tasks
          </div>
        </div>
      </div>

      {/* Kanban Board View */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {Object.entries(tasksByStatus).map(([status, statusTasks]) => (
          <div key={status} className="task-column">
            <div className="mb-4">
              <div className={`flex items-center space-x-2 p-3 rounded-lg ${getStatusColor(status)}`}>
                {getStatusIcon(status)}
                <h3 className="font-semibold capitalize">
                  {status.replace('_', ' ')} ({statusTasks.length})
                </h3>
              </div>
            </div>
            
            <div className="space-y-3">
              <AnimatePresence>
                {statusTasks.map(task => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    isSelected={selectedTask === task.id}
                  />
                ))}
              </AnimatePresence>
            </div>
            
            {statusTasks.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <ClockIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tasks</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <TaskDetailsModal
          task={tasks.find(t => t.id === selectedTask)!}
          agent={agentMap.get(tasks.find(t => t.id === selectedTask)?.agent_id)}
          onClose={() => onTaskSelect('')}
          onAction={onTaskAction}
        />
      )}
    </div>
  );
};

// Task Details Modal Component
const TaskDetailsModal: React.FC<{
  task: CrewTask;
  agent?: CrewAgent;
  onClose: () => void;
  onAction: (taskId: string, action: 'retry' | 'skip' | 'prioritize') => void;
}> = ({ task, agent, onClose, onAction }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="glass-card p-6 max-w-2xl w-full m-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white mb-2">{task.title}</h2>
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                task.priority === 'critical' ? 'bg-red-500 text-white' :
                task.priority === 'high' ? 'bg-orange-500 text-white' :
                task.priority === 'medium' ? 'bg-yellow-500 text-black' :
                'bg-green-500 text-white'
              }`}>
                {task.priority}
              </span>
              <span className={`px-2 py-1 rounded text-xs ${
                task.status === 'in_progress' ? 'bg-blue-500/20 text-blue-400' :
                task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                task.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {task.status.replace('_', ' ')}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">Description</h3>
            <p className="text-gray-300">{task.description}</p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-white mb-2">Expected Output</h3>
            <p className="text-gray-300 bg-black/20 rounded p-3">{task.expected_output}</p>
          </div>

          {task.actual_output && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Actual Output</h3>
              <div className="text-gray-300 bg-black/20 rounded p-3 whitespace-pre-wrap">
                {task.actual_output}
              </div>
            </div>
          )}

          {agent && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Assigned Agent</h3>
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <UserIcon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="font-medium text-white">{agent.name}</div>
                  <div className="text-sm text-gray-400">{agent.role}</div>
                </div>
              </div>
            </div>
          )}

          {task.tools_used && task.tools_used.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">Tools Used</h3>
              <div className="flex flex-wrap gap-2">
                {task.tools_used.map((tool, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Created:</span>
              <div className="text-white">{new Date(task.created_at).toLocaleString()}</div>
            </div>
            <div>
              <span className="text-gray-400">Updated:</span>
              <div className="text-white">{new Date(task.updated_at).toLocaleString()}</div>
            </div>
            {task.started_at && (
              <div>
                <span className="text-gray-400">Started:</span>
                <div className="text-white">{new Date(task.started_at).toLocaleString()}</div>
              </div>
            )}
            {task.completed_at && (
              <div>
                <span className="text-gray-400">Completed:</span>
                <div className="text-white">{new Date(task.completed_at).toLocaleString()}</div>
              </div>
            )}
          </div>

          <div className="flex space-x-3 pt-4 border-t border-gray-700">
            {task.status === 'failed' && (
              <button
                onClick={() => onAction(task.id, 'retry')}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
              >
                Retry Task
              </button>
            )}
            {task.status === 'pending' && (
              <button
                onClick={() => onAction(task.id, 'prioritize')}
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded transition-colors"
              >
                Prioritize
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default TaskBoard;
