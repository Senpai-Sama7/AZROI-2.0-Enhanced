import React, { useState, useEffect } from 'react';
import Card from './common/Card';
import Icon from './common/Icon';
import { ICON_COG, ICON_CHECK_CIRCLE, ICON_EXCLAMATION_TRIANGLE, ICON_INFORMATION_CIRCLE } from '../constants';
import { MOCK_HW_REPORT } from '../constants';
import type { SystemStatus } from '../types';

interface MonitoringPanelProps {
  systemStatus: SystemStatus | null;
  wsConnection: WebSocket | null;
  lastHeartbeat: Date | null;
}

const MonitoringPanel: React.FC<MonitoringPanelProps> = ({ 
  systemStatus, 
  wsConnection, 
  lastHeartbeat 
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [connectionQuality, setConnectionQuality] = useState<'good' | 'poor' | 'disconnected'>('disconnected');

  // Monitor connection quality
  useEffect(() => {
    if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
      setConnectionQuality('disconnected');
      return;
    }

    if (!lastHeartbeat) {
      setConnectionQuality('poor');
      return;
    }

    const timeSinceHeartbeat = Date.now() - lastHeartbeat.getTime();
    if (timeSinceHeartbeat < 30000) { // 30 seconds
      setConnectionQuality('good');
    } else {
      setConnectionQuality('poor');
    }
  }, [wsConnection, lastHeartbeat]);

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'connected':
      case 'running':
        return 'text-green-400';
      case 'degraded':
      case 'poor':
        return 'text-yellow-400';
      case 'unhealthy':
      case 'disconnected':
      case 'error':
      case 'stopped':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'connected':
      case 'running':
        return ICON_CHECK_CIRCLE;
      case 'degraded':
      case 'poor':
        return ICON_EXCLAMATION_TRIANGLE;
      case 'unhealthy':
      case 'disconnected':
      case 'error':
      case 'stopped':
        return ICON_EXCLAMATION_TRIANGLE;
      default:
        return ICON_INFORMATION_CIRCLE;
    }
  };

  const formatPercentage = (value: number) => `${value.toFixed(1)}%`;
  const formatUptime = (lastUpdated: string) => {
    const updateTime = new Date(lastUpdated);
    const now = new Date();
    const diffMs = now.getTime() - updateTime.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ${diffMinutes % 60}m ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ${diffHours % 24}h ago`;
  };

  return (
    <div className="space-y-6 animate-slide-up">
      {/* System Overview */}
      <Card 
        title="System Status Overview" 
        titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-blue-400" />}
      >
        {systemStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatusItem
              label="Backend Health"
              value={systemStatus.backend_health}
              icon={getStatusIcon(systemStatus.backend_health)}
              colorClass={getStatusColor(systemStatus.backend_health)}
            />
            <StatusItem
              label="WebSocket"
              value={connectionQuality}
              icon={getStatusIcon(connectionQuality)}
              colorClass={getStatusColor(connectionQuality)}
              subtext={lastHeartbeat ? `Last: ${lastHeartbeat.toLocaleTimeString()}` : undefined}
            />
            <StatusItem
              label="Open Interpreter"
              value={systemStatus.open_interpreter_status}
              icon={getStatusIcon(systemStatus.open_interpreter_status)}
              colorClass={getStatusColor(systemStatus.open_interpreter_status)}
            />
            <StatusItem
              label="Memory Usage"
              value={formatPercentage(systemStatus.memory_usage_percent)}
              icon={ICON_INFORMATION_CIRCLE}
              colorClass={systemStatus.memory_usage_percent > 80 ? 'text-red-400' : 'text-green-400'}
            />
            <StatusItem
              label="CPU Usage"
              value={formatPercentage(systemStatus.cpu_usage_percent)}
              icon={ICON_INFORMATION_CIRCLE}
              colorClass={systemStatus.cpu_usage_percent > 80 ? 'text-red-400' : 'text-green-400'}
            />
            <StatusItem
              label="Active Agents"
              value={systemStatus.agent_count.toString()}
              icon={ICON_INFORMATION_CIRCLE}
              colorClass="text-blue-400"
            />
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <p>Loading system status...</p>
          </div>
        )}
        
        {systemStatus && (
          <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-400">
            Last updated: {formatUptime(systemStatus.last_updated)}
          </div>
        )}
      </Card>

      {/* Hardware Report */}
      <Card 
        title="Hardware Capabilities Report" 
        titleIcon={<Icon path={ICON_INFORMATION_CIRCLE} className="w-5 h-5 text-purple-400" />}
      >
        <div className="space-y-4">
          {/* Local Capabilities */}
          <ExpandableSection
            title="Local Hardware Analysis"
            isExpanded={expandedSection === 'local'}
            onToggle={() => toggleSection('local')}
          >
            <div className="space-y-3 text-sm">
              <InfoRow label="Server" value={MOCK_HW_REPORT.local_capabilities.server_details} />
              <InfoRow label="Laptop" value={MOCK_HW_REPORT.local_capabilities.laptop_details} />
              <InfoRow 
                label="GPU Acceleration" 
                value={MOCK_HW_REPORT.local_capabilities.gpu_acceleration_vllm_tgi_compatible ? 'Available' : 'Not Available'}
                colorClass={MOCK_HW_REPORT.local_capabilities.gpu_acceleration_vllm_tgi_compatible ? 'text-green-400' : 'text-red-400'}
              />
              <InfoRow label="Reason" value={MOCK_HW_REPORT.local_capabilities.reason_vllm_tgi_incompatibility} />
              <InfoRow label="Max Local LLM" value={MOCK_HW_REPORT.local_capabilities.max_local_llm_cpu_inference_ollama} />
              <InfoRow label="Estimated Performance" value={MOCK_HW_REPORT.local_capabilities.estimated_local_7b_q4_tokens_sec_cpu_ollama} />
              
              <div className="mt-3">
                <h5 className="font-semibold text-gray-300 mb-2">Limitations:</h5>
                <ul className="space-y-1 text-xs text-gray-400">
                  {MOCK_HW_REPORT.local_capabilities.limitations.map((limitation, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-red-400 mr-2">•</span>
                      <span>{limitation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </ExpandableSection>

          {/* Cloud Strategy */}
          <ExpandableSection
            title="Cloud Optimization Strategy"
            isExpanded={expandedSection === 'cloud'}
            onToggle={() => toggleSection('cloud')}
          >
            <div className="space-y-3 text-sm">
              <InfoRow 
                label="Primary LLM Hosting" 
                value={MOCK_HW_REPORT.cloud_requirements_and_strategy.primary_llm_hosting_optimized} 
              />
              
              <div className="bg-gray-800/30 p-3 rounded border border-gray-700">
                <h5 className="font-semibold text-gray-300 mb-2">Embedding Models:</h5>
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-green-400 font-medium">Primary:</span> {MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.primary.provider} - {MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.primary.model}
                    <div className="text-gray-400 ml-4">{MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.primary.cost_notes}</div>
                  </div>
                  <div>
                    <span className="text-blue-400 font-medium">Alternative:</span> {MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.alternative.provider} - {MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.alternative.model}
                    <div className="text-gray-400 ml-4">{MOCK_HW_REPORT.cloud_requirements_and_strategy.embedding_model_preference.alternative.cost_notes}</div>
                  </div>
                </div>
              </div>

              <InfoRow label="Balanced GPU Config" value={MOCK_HW_REPORT.cloud_requirements_and_strategy.vertex_ai_gpu_config_balanced} />
              <InfoRow label="High-Performance Config" value={MOCK_HW_REPORT.cloud_requirements_and_strategy.vertex_ai_gpu_config_powerful} />
              <InfoRow label="Estimated T4 Cost" value={MOCK_HW_REPORT.cloud_requirements_and_strategy.estimated_cost_t4_vm_vertex} />

              <div className="mt-3">
                <h5 className="font-semibold text-gray-300 mb-2">Cost Optimization Strategies:</h5>
                <ul className="space-y-1 text-xs text-gray-400">
                  {MOCK_HW_REPORT.cloud_requirements_and_strategy.credit_optimization_strategies.map((strategy, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-blue-400 mr-2">•</span>
                      <span>{strategy}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </ExpandableSection>
        </div>
      </Card>
    </div>
  );
};

// Helper Components
interface StatusItemProps {
  label: string;
  value: string;
  icon: string;
  colorClass: string;
  subtext?: string;
}

const StatusItem: React.FC<StatusItemProps> = ({ label, value, icon, colorClass, subtext }) => (
  <div className="bg-gray-800/30 p-3 rounded border border-gray-700">
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs text-gray-400 font-medium">{label}</span>
      <Icon path={icon} className={`w-4 h-4 ${colorClass}`} />
    </div>
    <div className={`text-sm font-semibold ${colorClass}`}>{value}</div>
    {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
  </div>
);

interface InfoRowProps {
  label: string;
  value: string;
  colorClass?: string;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value, colorClass = 'text-gray-300' }) => (
  <div className="flex justify-between items-start py-1">
    <span className="text-gray-400 text-xs font-medium min-w-0 mr-3">{label}:</span>
    <span className={`text-xs ${colorClass} text-right`}>{value}</span>
  </div>
);

interface ExpandableSectionProps {
  title: string;
  children: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
}

const ExpandableSection: React.FC<ExpandableSectionProps> = ({ title, children, isExpanded, onToggle }) => (
  <div className="bg-gray-800/20 rounded border border-gray-700">
    <button
      onClick={onToggle}
      className="w-full p-3 text-left flex justify-between items-center hover:bg-gray-700/20 transition-colors"
    >
      <span className="font-medium text-gray-200">{title}</span>
      <Icon 
        path="M19 9l-7 7-7-7" 
        className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
      />
    </button>
    {isExpanded && (
      <div className="px-3 pb-3 border-t border-gray-700">
        {children}
      </div>
    )}
  </div>
);

export default MonitoringPanel;
