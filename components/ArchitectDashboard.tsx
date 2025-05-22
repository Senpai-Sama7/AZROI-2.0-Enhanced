// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/ArchitectDashboard.tsx
// All development should use /frontend/src/components/ArchitectDashboard.tsx version.

import React, { useState } from 'react';
import Card from './common/Card';
import Icon from './common/Icon';
import { ICON_TERMINAL, ICON_DOCUMENT_TEXT, ICON_CHEVRON_DOWN, ICON_COG, ICON_LIGHT_BULB } from '../constants';
import type { ArchitectGoal, Agent, ArchitectOutput } from '../types';

interface ArchitectDashboardProps {
  currentGoal: ArchitectGoal | null;
  agents: Agent[];
  outputs: ArchitectOutput[];
}

const Pill: React.FC<{children: React.ReactNode, colorClass: string, className?: string}> = ({ children, colorClass, className ="" }) => (
  <span className={`px-3 py-1 text-xs font-bold rounded-full inline-block shadow-sm ${colorClass} ${className}`}>
    {children}
  </span>
);

const ArchitectDashboard: React.FC<ArchitectDashboardProps> = ({ currentGoal, agents, outputs }) => {
  const [activeOutputTab, setActiveOutputTab] = useState<'log' | 'plan' | 'code' | 'report'>('log');
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const toggleAgentExpansion = (agentId: string) => {
    setExpandedAgent(expandedAgent === agentId ? null : agentId);
  };

  if (!currentGoal || currentGoal.status === 'pending' || currentGoal.status === 'analyzing') {
    return (
      <Card 
        title="Architect Dashboard" 
        titleIcon={<Icon path={ICON_COG} className="w-7 h-7"/>}
        className="!border-gem-muted-grey/20"
        style={{'--gem-shadow-color': 'var(--color-gem-muted-grey)'} as React.CSSProperties}
        >
        <div className="text-center py-16">
          <Icon path={ICON_LIGHT_BULB} className="w-20 h-20 text-gem-muted-grey/50 mx-auto mb-6" />
          <p className="text-gem-light-achromatic text-xl mb-2">Awaiting a New Architectural Vision.</p>
          <p className="text-gem-muted-grey">Submit your grand design to initiate the AI Architect.</p>
        </div>
      </Card>
    );
  }
  
  const getStatusPillColor = (status: ArchitectGoal['status'] | Agent['status']) => {
    switch(status) {
      case 'pending':
      case 'idle':
        return 'bg-gem-citrine/20 text-gem-citrine border border-gem-citrine/40';
      case 'analyzing':
      case 'active':
        return 'bg-gem-sapphire/20 text-gem-sapphire border border-gem-sapphire/40 animate-pulse-subtle';
      case 'analyzed':
      case 'processing':
        return 'bg-gem-amethyst/20 text-gem-amethyst border border-gem-amethyst/40 animate-pulse-subtle';
      case 'completed':
        return 'bg-gem-fuchsia/20 text-gem-fuchsia border border-gem-fuchsia/40'; // Using fuchsia for success
      case 'error':
        return 'bg-gem-ruby/20 text-gem-ruby border border-gem-ruby/40';
      default:
        return 'bg-gem-ebony-surface text-gem-muted-grey border border-gem-muted-grey/30';
    }
  };

  const filteredOutputs = outputs.filter(output => output.type === activeOutputTab);

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 animate-slide-up">
      <div className="md:col-span-12 lg:col-span-7 xl:col-span-8 space-y-6">
        <Card 
            title="Current Vision & Status" 
            titleIcon={<Icon path={ICON_LIGHT_BULB} className="w-7 h-7"/>}
            className="!border-gem-sapphire/30"
            style={{'--gem-shadow-color': 'var(--color-gem-sapphire)'} as React.CSSProperties}
        >
          <h4 className="text-2xl font-semibold text-gem-light-achromatic mb-3">{currentGoal.text}</h4>
          <div className="flex items-center space-x-3">
            <span className="text-gem-muted-grey">Overall Status:</span>
            <Pill colorClass={getStatusPillColor(currentGoal.status)}>{currentGoal.status.toUpperCase()}</Pill>
          </div>
          {currentGoal.analysis && (
            <details className="mt-5 text-sm group">
              <summary className="cursor-pointer text-gem-citrine hover:underline list-none flex items-center font-medium">
                View AI-Powered Insights
                <Icon path={ICON_CHEVRON_DOWN} className="w-4 h-4 ml-1.5 group-open:rotate-180 transition-transform" />
              </summary>
              <div className="mt-2 p-3.5 bg-gem-ebony/60 rounded-md text-gem-light-achromatic/80 whitespace-pre-wrap leading-relaxed animate-fade-in custom-scrollbar max-h-40 overflow-y-auto">
                {currentGoal.analysis}
              </div>
            </details>
          )}
        </Card>

        <Card 
            title="AI Agent Activities" 
            titleIcon={<Icon path={ICON_COG} className="w-7 h-7" />}
            className="!border-gem-amethyst/30"
            style={{'--gem-shadow-color': 'var(--color-gem-amethyst)'} as React.CSSProperties}
        >
          {agents.length === 0 && <p className="text-gem-muted-grey">No active agents for this vision.</p>}
          <div className="space-y-4">
            {agents.map(agent => (
              <div key={agent.id} className="bg-gem-ebony-surface p-4 rounded-lg shadow-md border border-gem-muted-grey/25 transition-all hover:border-gem-amethyst/50">
                <div className="flex justify-between items-center cursor-pointer group" onClick={() => toggleAgentExpansion(agent.id)}>
                  <div>
                    <h5 className="font-semibold text-gem-light-achromatic text-lg">{agent.name}</h5>
                    <p className="text-xs text-gem-muted-grey">{agent.role}</p>
                  </div>
                  <div className="flex items-center space-x-3">
                    <Pill colorClass={getStatusPillColor(agent.status)} className="text-xs">{agent.status.toUpperCase()}</Pill>
                    <Icon path={ICON_CHEVRON_DOWN} className={`w-5 h-5 text-gem-muted-grey group-hover:text-gem-amethyst transition-transform duration-200 ${expandedAgent === agent.id ? 'rotate-180 text-gem-amethyst' : ''}`} />
                  </div>
                </div>
                {expandedAgent === agent.id && agent.currentTask && (
                  <div className="mt-3 pt-3 border-t border-gem-muted-grey/20 animate-fade-in">
                    <p className="text-sm text-gem-light-achromatic/90 pl-1">
                      <strong className="text-gem-light-achromatic">Current Task:</strong> {agent.currentTask}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="md:col-span-12 lg:col-span-5 xl:col-span-4">
        <Card 
            title="Architectural Outputs & Logs" 
            className="h-full flex flex-col !border-gem-fuchsia/30" 
            titleIcon={<Icon path={ICON_DOCUMENT_TEXT} className="w-7 h-7" />}
            style={{'--gem-shadow-color': 'var(--color-gem-fuchsia)'} as React.CSSProperties}
            >
          <div className="mb-4 border-b border-gem-muted-grey/25">
            <nav className="-mb-px flex space-x-1" aria-label="Tabs">
              {(['log', 'plan', 'code', 'report'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveOutputTab(tab)}
                  className={`whitespace-nowrap py-3.5 px-4 border-b-2 font-semibold text-sm capitalize transition-colors duration-200 focus:outline-none
                    ${activeOutputTab === tab
                      ? 'border-gem-fuchsia text-gem-fuchsia'
                      : 'border-transparent text-gem-muted-grey hover:text-gem-light-achromatic/80 hover:border-gem-muted-grey/50'
                    }`}
                >
                  {tab}s
                </button>
              ))}
            </nav>
          </div>
          
          <div className="flex-grow h-[30rem] overflow-y-auto bg-gem-ebony p-4 rounded-lg text-sm custom-scrollbar border border-gem-muted-grey/20">
            {filteredOutputs.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-gem-muted-grey">
                    <Icon path={ICON_TERMINAL} className="w-12 h-12 mb-3 text-gem-muted-grey/70" />
                    <p>No {activeOutputTab}s to display yet.</p>
                </div>
            )}
            {filteredOutputs.map((output, index) => (
              <div key={index} className="mb-4 pb-4 border-b border-gem-muted-grey/20 last:border-b-0 last:pb-0 animate-fade-in">
                <div className="flex justify-between items-start mb-1.5">
                  <h5 className="font-semibold text-gem-light-achromatic">{output.title}</h5>
                  <span className="text-xs text-gem-muted-grey flex-shrink-0 ml-2">{new Date(output.timestamp).toLocaleString()}</span>
                </div>
                <pre className="whitespace-pre-wrap text-gem-light-achromatic/80 bg-black/30 p-3 rounded-md overflow-x-auto text-xs leading-relaxed custom-scrollbar border border-gem-muted-grey/10">
                  <code>{output.content}</code>
                </pre>
              </div>
            ))}
            {activeOutputTab === 'log' && filteredOutputs.length === 0 && (
                <div className="animate-fade-in space-y-1 text-gem-light-achromatic/70">
                <div className="text-gem-sapphire/80">Architect initialized. Awaiting vision...</div>
                <div className="text-gem-sapphire/80">Vision received: <span className="text-gem-light-achromatic font-medium">"{currentGoal.text}"</span></div>
                {currentGoal.status === 'processing' && <div className="text-gem-amethyst/80">[PROCESS] Processing vision... Agent 'Project Manager' activated.</div>}
                </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ArchitectDashboard;