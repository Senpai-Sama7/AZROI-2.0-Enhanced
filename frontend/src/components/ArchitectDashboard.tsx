import React, { useState, useEffect, useRef } from 'react';
import Card from './common/Card';
import Icon from './common/Icon';
import { ICON_TERMINAL, ICON_DOCUMENT_TEXT, ICON_CHEVRON_DOWN, ICON_COG, ICON_LIGHT_BULB, ICON_EXCLAMATION_TRIANGLE } from '../constants';
import type { ArchitectGoal, Agent, ArchitectOutput } from '../types';

interface ArchitectDashboardProps {
  currentGoal: ArchitectGoal | null;
  agents: Agent[];
  outputs: ArchitectOutput[];
  processingError?: string | null; // For general submission/websocket errors not tied to currentGoal state
}

const Pill: React.FC<{children: React.ReactNode, colorClass: string, className?: string}> = ({ children, colorClass, className ="" }) => (
  <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full inline-block shadow-sm ${colorClass} ${className}`}>
    {children}
  </span>
);

const ArchitectDashboard: React.FC<ArchitectDashboardProps> = ({ currentGoal, agents, outputs, processingError }) => {
  const [activeOutputTab, setActiveOutputTab] = useState<ArchitectOutput['type']>('log');
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const logsEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (activeOutputTab === 'log') {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }

  useEffect(scrollToBottom, [outputs, activeOutputTab]);

  const toggleAgentExpansion = (agentId: string) => {
    setExpandedAgent(expandedAgent === agentId ? null : agentId);
  };

  // Initial state if no goal or goal in pre-processing client states
  if (!currentGoal || currentGoal.status === 'pending' || currentGoal.status === 'analyzing') {
    return (
      <Card 
        title="Architect Dashboard" 
        titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-gray-400" />}
      >
        <div className="text-center py-10">
          <Icon path={ICON_LIGHT_BULB} className="w-14 h-14 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-200 text-md mb-1">Awaiting a New Architectural Vision.</p>
          <p className="text-gray-400 text-xs">Submit your grand design to initiate the AI Architect.</p>
        </div>
      </Card>
    );
  }
  
  const getStatusPillColor = (status: ArchitectGoal['status'] | Agent['status']) => {
    switch(status?.toLowerCase()) {
      case 'pending':
      case 'idle':
        return 'bg-yellow-600/30 text-yellow-300 border border-yellow-500/50';
      case 'analyzing': 
      case 'active':    
      case 'processing':
      case 'planning':
      case 'code_generation':
      case 'gcs_upload':
      case 'artifact_registry_repo_create':
      case 'cloud_build':
      case 'cloud_run_deployment':
        return 'bg-blue-600/30 text-blue-300 border border-blue-500/50 animate-pulse';
      case 'completed':
        return 'bg-green-600/30 text-green-300 border border-green-500/50';
      case 'error':
        return 'bg-red-700/30 text-red-300 border border-red-600/50';
      default:
        return 'bg-gray-700/40 text-gray-400 border border-gray-600/60'; // Fallback
    }
  };
  
  // Define the order of tabs and filter by available output types
  const orderedTabs: Array<ArchitectOutput['type']> = ['log', 'plan', 'code_file', 'dockerfile', 'gcs_uri', 'cloud_build_log_url', 'artifact_registry_image_uri', 'cloud_run_url', 'report'];
  const availableOutputTypesFromData = Array.from(new Set(outputs.map(o => o.type))) as Array<ArchitectOutput['type']>;
  const displayTabs = orderedTabs.filter(tab => availableOutputTypesFromData.includes(tab) || tab === 'log');
  
  useEffect(() => {
    // If current active tab isn't available anymore, default to log or first available
    if (!displayTabs.includes(activeOutputTab)) {
      if (displayTabs.includes('log')) {
        setActiveOutputTab('log');
      } else if (displayTabs.length > 0) {
        setActiveOutputTab(displayTabs[0]);
      }
    }
  }, [outputs, activeOutputTab, displayTabs]);


  const filteredOutputs = outputs.filter(output => output.type === activeOutputTab);

  const renderOutputContent = (output: ArchitectOutput) => {
    const contentStyle = "text-gray-300 text-xs leading-relaxed";
    if (output.url) {
      return (
        <a 
          href={output.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-pink-400 hover:text-pink-300 hover:underline break-all"
          title={`Open ${output.title || output.type} in new tab`}
        >
          {output.content || output.url}
        </a>
      );
    }
    
    // Handle known specific output types
    if (output.type === 'code_file' || output.type === 'dockerfile' || output.type === 'plan') {
      return (
        <pre className={`${contentStyle} whitespace-pre-wrap bg-black/40 p-2 rounded-md overflow-x-auto custom-scrollbar border border-gray-700/50 shadow-inner`}>
          <code className="break-words overflow-wrap-anywhere">{output.content}</code>
        </pre>
      );
    }
    
    let logTextColor = "text-gray-300"; // Default for INFO or unspecified
    if (output.level === 'ERROR') logTextColor = "text-red-400";
    else if (output.level === 'WARNING') logTextColor = "text-yellow-400";
    else if (output.level === 'INFO' && output.sourceAgent && !['System', 'Frontend', 'WebSocket_Connection_Placeholder'].includes(output.sourceAgent)) logTextColor = "text-blue-300";


    return <span className={`${contentStyle} ${logTextColor} whitespace-pre-wrap`}>{output.content}</span>;
  };


  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 animate-slide-up">
      {/* Left Column: Goal & Agents */}
      <div className="md:col-span-12 lg:col-span-7 xl:col-span-8 space-y-4">
        <Card 
            title="Current Vision & Status" 
            titleIcon={<Icon path={ICON_LIGHT_BULB} className="w-5 h-5 text-pink-400" />}
        >
          <h4 className="text-md font-semibold text-gray-100 mb-1.5">{currentGoal.text}</h4>
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-gray-400 text-xs">Overall Status:</span>
            <Pill colorClass={getStatusPillColor(currentGoal.status)}>{currentGoal.status.toUpperCase()}</Pill>
          </div>
          {currentGoal.analysis && (
            <details className="mt-2 text-xs group">
              <summary className="cursor-pointer text-yellow-400 hover:underline list-none flex items-center font-medium">
                View Client-Side AI Analysis
                <Icon path={ICON_CHEVRON_DOWN} className="w-3 h-3 ml-1 group-open:rotate-180 transition-transform" />
              </summary>
              <div className="mt-1 p-1.5 bg-black/30 rounded text-gray-300 whitespace-pre-wrap leading-relaxed animate-fade-in custom-scrollbar max-h-20 overflow-y-auto text-xs">
                {currentGoal.analysis}
              </div>
            </details>
          )}
           {(processingError || currentGoal.processingError) && (
             <div className="mt-2 p-2 bg-red-700/20 border border-red-600/50 rounded text-red-300 flex items-start space-x-1 animate-fade-in shadow-sm text-xs">
                <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-3.5 h-3.5 flex-shrink-0 text-red-400 mt-px" />
                <div>
                    <h5 className="font-semibold">Processing Error</h5>
                    <p>{processingError || currentGoal.processingError}</p>
                </div>
            </div>
          )}
        </Card>

        <Card 
            title="AI Agent Activities" 
            titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-purple-400" />}
        >
          {(agents.length === 0 && (currentGoal.status !== 'completed' && currentGoal.status !== 'error')) && <p className="text-gray-400 italic text-xs">Initializing agents or awaiting backend updates...</p>}
          {(agents.length === 0 && (currentGoal.status === 'completed' || currentGoal.status === 'error')) && <p className="text-gray-400 text-xs">No active agents. Processing has {currentGoal.status}.</p>}
          
          <div className="space-y-2 max-h-80 overflow-y-auto custom-scrollbar pr-1">
            {agents.map(agent => (
              <div key={agent.id || agent.name} className="bg-gray-800/50 p-2 rounded shadow border border-gray-700/60 transition-all hover:border-purple-500/50">
                <div className="flex justify-between items-center cursor-pointer group" onClick={() => toggleAgentExpansion(agent.id || agent.name)}>
                  <div>
                    <h5 className="font-semibold text-gray-100 text-sm">{agent.name}</h5>
                    <p className="text-xs text-gray-400">{agent.role}</p>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Pill colorClass={getStatusPillColor(agent.status)} className="text-xs">{agent.status.toUpperCase()}</Pill>
                    <Icon path={ICON_CHEVRON_DOWN} className={`w-3.5 h-3.5 text-gray-400 group-hover:text-purple-400 transition-transform duration-200 ${expandedAgent === (agent.id || agent.name) ? 'rotate-180 text-purple-400' : ''}`} />
                  </div>
                </div>
                {expandedAgent === (agent.id || agent.name) && agent.currentTask && (
                  <div className="mt-1.5 pt-1.5 border-t border-gray-700/50 animate-fade-in">
                    <p className="text-xs text-gray-300">
                      <strong className="text-gray-200">Task:</strong> {agent.currentTask}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Right Column: Outputs & Logs */}
      <div className="md:col-span-12 lg:col-span-5 xl:col-span-4">
        <Card 
            title="Architectural Outputs & Logs" 
            className="h-full flex flex-col" 
            titleIcon={<Icon path={ICON_DOCUMENT_TEXT} className="w-5 h-5 text-green-400" />}
            bodyClassName="flex flex-col flex-grow !p-2" // Override Card's default body padding
        >
          <div className="mb-2 border-b border-gray-700/60">
            <nav className="-mb-px flex space-x-0.5 overflow-x-auto custom-scrollbar pb-px" aria-label="Tabs">
              {displayTabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveOutputTab(tab)}
                  className={`whitespace-nowrap py-2 px-2.5 border-b-2 font-medium text-xs capitalize transition-colors duration-200 focus:outline-none hover:bg-gray-700/40 rounded-t
                    ${activeOutputTab === tab
                      ? 'border-pink-500 text-pink-400' 
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600/40'
                    }`}
                  aria-current={activeOutputTab === tab ? 'page' : undefined}
                >
                  {tab.replace(/_/g, ' ')}
                </button>
              ))}
            </nav>
          </div>
          
          <div className="flex-grow h-[24rem] sm:h-[28rem] overflow-y-auto bg-black/30 p-2 rounded text-xs custom-scrollbar border border-gray-700/50 shadow-inner">
            {filteredOutputs.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <Icon path={ICON_TERMINAL} className="w-8 h-8 mb-1.5 text-gray-600" />
                    <p>No {activeOutputTab.replace(/_/g, ' ')} to display yet.</p>
                     {activeOutputTab === 'log' && <p className="text-xs mt-0.5">Waiting for real-time updates...</p>}
                </div>
            )}
            {filteredOutputs.map((output, index) => (
              <div key={index} className={`mb-1.5 pb-1.5 border-b border-gray-700/50 last:border-b-0 last:pb-0 animate-fade-in ${output.level === 'ERROR' ? 'bg-red-900/30 p-1 rounded-sm' : output.level === 'WARNING' ? 'bg-yellow-800/20 p-1 rounded-sm': ''}`}>
                <div className="flex justify-between items-start mb-0.5">
                  <h5 className="font-semibold text-gray-200 text-xs flex items-center">
                    {output.level === 'ERROR' && <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-3 h-3 mr-1 text-red-400" />}
                    {output.title} 
                    {output.sourceAgent && <span className="text-xs text-gray-500 ml-1">({output.sourceAgent})</span>}
                  </h5>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-1.5">{new Date(output.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="pl-0.5"> {/* No extra padding for content itself, let renderOutputContent handle it */}
                    {renderOutputContent(output)}
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </Card>
      </div>
    </div>
  );
};

export default ArchitectDashboard;
