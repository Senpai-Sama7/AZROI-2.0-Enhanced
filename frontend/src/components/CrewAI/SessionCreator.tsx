import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  PlusIcon,
  UserGroupIcon,
  Cog6ToothIcon,
  PlayIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import type { CrewAgent } from '../../types/crewai';
import crewAPIService from '../../services/crewapi';

interface SessionCreatorProps {
  onSessionCreated: (sessionId: string) => void;
  onClose: () => void;
  className?: string;
}

const SessionCreator: React.FC<SessionCreatorProps> = ({
  onSessionCreated,
  onClose,
  className = ''
}) => {
  const [sessionData, setSessionData] = useState({
    name: '',
    goal: '',
    workflow: 'sequential' as 'sequential' | 'hierarchical' | 'consensus',
    max_iterations: 5
  });

  const [agents, setAgents] = useState<Partial<CrewAgent>[]>([
    {
      name: 'Senior Architect',
      role: 'Lead Developer',
      goal: 'Design and oversee the overall system architecture',
      backstory: 'Experienced software architect with expertise in scalable systems',
      capabilities: ['System Design', 'Code Review', 'Architecture Planning'],
      tools: ['code_analyzer', 'documentation_generator', 'design_patterns']
    },
    {
      name: 'DevOps Engineer',
      role: 'Infrastructure Specialist',
      goal: 'Handle deployment, monitoring, and infrastructure management',
      backstory: 'DevOps expert focused on automation and reliable deployments',
      capabilities: ['CI/CD', 'Monitoring', 'Infrastructure as Code'],
      tools: ['docker_manager', 'kubernetes_deployer', 'monitoring_setup']
    }
  ]);

  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddAgent = () => {
    setAgents([...agents, {
      name: '',
      role: '',
      goal: '',
      backstory: '',
      capabilities: [],
      tools: []
    }]);
  };

  const handleRemoveAgent = (index: number) => {
    setAgents(agents.filter((_, i) => i !== index));
  };

  const handleAgentChange = (index: number, field: keyof CrewAgent, value: any) => {
    const updatedAgents = [...agents];
    updatedAgents[index] = { ...updatedAgents[index], [field]: value };
    setAgents(updatedAgents);
  };

  const handleCapabilityChange = (agentIndex: number, capabilities: string) => {
    const caps = capabilities.split(',').map(c => c.trim()).filter(c => c);
    handleAgentChange(agentIndex, 'capabilities', caps);
  };

  const handleToolsChange = (agentIndex: number, tools: string) => {
    const toolList = tools.split(',').map(t => t.trim()).filter(t => t);
    handleAgentChange(agentIndex, 'tools', toolList);
  };

  const validateForm = (): boolean => {
    if (!sessionData.name.trim()) {
      setError('Session name is required');
      return false;
    }
    if (!sessionData.goal.trim()) {
      setError('Session goal is required');
      return false;
    }
    if (agents.length === 0) {
      setError('At least one agent is required');
      return false;
    }
    
    for (let i = 0; i < agents.length; i++) {
      const agent = agents[i];
      if (!agent.name?.trim() || !agent.role?.trim() || !agent.goal?.trim()) {
        setError(`Agent ${i + 1} is missing required fields`);
        return false;
      }
    }
    
    setError(null);
    return true;
  };

  const handleCreate = async () => {
    if (!validateForm()) return;

    setIsCreating(true);
    try {
      const session = await crewAPIService.createSession({
        ...sessionData,
        agents: agents.map(agent => ({
          ...agent,
          status: 'idle' as const,
          id: undefined,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }))
      });

      onSessionCreated(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
    } finally {
      setIsCreating(false);
    }
  };

  const AgentForm: React.FC<{ agent: Partial<CrewAgent>; index: number }> = ({ agent, index }) => (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-lg font-semibold text-white">Agent {index + 1}</h4>
        {agents.length > 1 && (
          <button
            onClick={() => handleRemoveAgent(index)}
            className="text-red-400 hover:text-red-300"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Name *
          </label>
          <input
            type="text"
            value={agent.name || ''}
            onChange={(e) => handleAgentChange(index, 'name', e.target.value)}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="Agent name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Role *
          </label>
          <input
            type="text"
            value={agent.role || ''}
            onChange={(e) => handleAgentChange(index, 'role', e.target.value)}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="Agent role"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Goal *
        </label>
        <textarea
          value={agent.goal || ''}
          onChange={(e) => handleAgentChange(index, 'goal', e.target.value)}
          className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white h-20"
          placeholder="What should this agent accomplish?"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Backstory
        </label>
        <textarea
          value={agent.backstory || ''}
          onChange={(e) => handleAgentChange(index, 'backstory', e.target.value)}
          className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white h-20"
          placeholder="Agent's background and expertise"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Capabilities (comma-separated)
          </label>
          <input
            type="text"
            value={agent.capabilities?.join(', ') || ''}
            onChange={(e) => handleCapabilityChange(index, e.target.value)}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="System Design, Code Review"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Tools (comma-separated)
          </label>
          <input
            type="text"
            value={agent.tools?.join(', ') || ''}
            onChange={(e) => handleToolsChange(index, e.target.value)}
            className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="code_analyzer, docker_manager"
          />
        </div>
      </div>
    </div>
  );

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
        className={`glass-card p-6 max-w-4xl w-full m-4 max-h-[90vh] overflow-y-auto ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <UserGroupIcon className="w-8 h-8 text-blue-400" />
            <h2 className="text-2xl font-bold text-white">Create Crew Session</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Session Configuration */}
        <div className="space-y-6">
          <div className="glass-card p-4 space-y-4">
            <h3 className="text-lg font-semibold text-white">Session Configuration</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Session Name *
                </label>
                <input
                  type="text"
                  value={sessionData.name}
                  onChange={(e) => setSessionData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
                  placeholder="My AI Architecture Project"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Workflow Type
                </label>
                <select
                  value={sessionData.workflow}
                  onChange={(e) => setSessionData(prev => ({ ...prev, workflow: e.target.value as any }))}
                  className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  <option value="sequential">Sequential</option>
                  <option value="hierarchical">Hierarchical</option>
                  <option value="consensus">Consensus</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Session Goal *
              </label>
              <textarea
                value={sessionData.goal}
                onChange={(e) => setSessionData(prev => ({ ...prev, goal: e.target.value }))}
                className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white h-24"
                placeholder="Describe what you want the AI crew to accomplish..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Max Iterations
              </label>
              <input
                type="number"
                value={sessionData.max_iterations}
                onChange={(e) => setSessionData(prev => ({ ...prev, max_iterations: parseInt(e.target.value) }))}
                className="w-full bg-black/30 border border-gray-600 rounded px-3 py-2 text-white"
                min="1"
                max="20"
              />
            </div>
          </div>

          {/* Agents Configuration */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Agents Configuration</h3>
              <button
                onClick={handleAddAgent}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                <PlusIcon className="w-4 h-4" />
                <span>Add Agent</span>
              </button>
            </div>

            <div className="space-y-4">
              {agents.map((agent, index) => (
                <AgentForm key={index} agent={agent} index={index} />
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-4 pt-6 border-t border-gray-700">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={isCreating}
              className="flex items-center space-x-2 px-6 py-2 bg-green-500 hover:bg-green-600 disabled:bg-gray-500 text-white rounded-lg transition-colors"
            >
              {isCreating ? (
                <Cog6ToothIcon className="w-4 h-4 animate-spin" />
              ) : (
                <PlayIcon className="w-4 h-4" />
              )}
              <span>{isCreating ? 'Creating...' : 'Create & Start Session'}</span>
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default SessionCreator;
