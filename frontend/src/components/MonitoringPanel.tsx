import React, { useState, useEffect } from 'react';
import Card from './common/Card';
import Icon from './common/Icon';
import { ICON_CHART_BAR, ICON_COG, MOCK_HW_REPORT, ICON_LIGHT_BULB } from '../constants';
import type { HwReport } from '../types';
import LoadingSpinner from './common/LoadingSpinner';

const MonitoringPanel: React.FC = () => {
  const [hwReport, setHwReport] = useState<HwReport>(MOCK_HW_REPORT as HwReport);
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSystemData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Fetch hardware report
        const hwResponse = await fetch('http://localhost:8001/api/system/hardware');
        if (!hwResponse.ok) {
          throw new Error('Failed to fetch hardware data');
        }
        const hwData = await hwResponse.json();
        
        // Fetch metrics data
        const metricsResponse = await fetch('http://localhost:8001/api/system/metrics');
        if (!metricsResponse.ok) {
          throw new Error('Failed to fetch metrics data');
        }
        const metricsData = await metricsResponse.json();
        
        // Update state with real data
        setHwReport(hwData.hardware_report || MOCK_HW_REPORT);
        setMetrics(metricsData.metrics);
      } catch (error) {
        console.error("Error fetching system data:", error);
        setError("Failed to load system data. Using mock data instead.");
        // Fallback to mock data
        setHwReport(MOCK_HW_REPORT as HwReport);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSystemData();
    
    // Set up a refresh interval (every 30 seconds)
    const intervalId = setInterval(fetchSystemData, 30000);
    
    // Cleanup interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  // MetricCard styled for the new theme
  const MetricCard: React.FC<{label: string; value: string | number; unit?: string; iconPath?: string; accentClass?: string; trend?: 'up' | 'down' | 'neutral'}> = 
  ({label, value, unit, iconPath, accentClass = 'text-blue-400', trend}) => {
    const trendClasses = { 
        up: 'text-green-400', 
        down: 'text-red-400',
        neutral: 'text-gray-400'
    };
    const trendIcons = { 
        up: 'M4.5 15.75l7.5-7.5 7.5 7.5', 
        down: 'M19.5 8.25l-7.5 7.5-7.5-7.5', 
        neutral: 'M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z' 
    };

    return (
        <div 
            className="bg-gray-800/60 p-3 rounded-lg shadow border border-gray-700/60 transform hover:scale-[1.02] transition-transform duration-200 hover:shadow-md hover:border-gray-600/70"
        >
            <div className="flex items-center justify-between mb-0.5">
                <p className="text-xs font-medium text-gray-400">{label}</p>
                {iconPath && <Icon path={iconPath} className={`w-3.5 h-3.5 ${accentClass}`} />}
            </div>
            <p className="text-lg font-bold text-gray-100">{value}{unit && <span className="text-xs font-medium text-gray-400 ml-1">{unit}</span>}</p>
            {trend && (
                <div className={`mt-0.5 flex items-center text-xs ${trendClasses[trend]}`}>
                    <Icon path={trendIcons[trend]} className="w-2.5 h-2.5 mr-0.5" />
                    <span>{trend === 'up' ? '+5.2%' : trend === 'down' ? '-1.8%' : 'Stable'}</span>
                </div>
            )}
        </div>
    );
  };
  
  const DetailItem: React.FC<{label: string; children: React.ReactNode; highlight?: boolean}> = ({label, children, highlight=false}) => (
    <div className="py-1 border-b border-gray-700/50 last:border-b-0">
        <span className={`font-medium text-xs ${highlight ? 'text-yellow-300' : 'text-gray-200'}`}>{label}: </span>
        <span className="text-gray-300 text-xs">{children}</span>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {error && <p className="text-red-400 text-xs text-center">{error}</p>}
      <Card 
        title="System Performance Dashboard" 
        titleIcon={<Icon path={ICON_CHART_BAR} className="w-5 h-5 text-blue-400" />}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {metrics ? (
            <>
              <MetricCard label="LLM API Calls (1hr)" value={metrics.llm_api_calls} trend="up" iconPath="M10.5 6a7.5 7.5 0 100 15 7.5 7.5 0 000-15zM2.25 10.5a8.25 8.25 0 1114.59 5.28l4.69 4.69a.75.75 0 11-1.06 1.06l-4.69-4.69A8.25 8.25 0 012.25 10.5z" accentClass="text-blue-400"/>
              <MetricCard label="Avg. LLM Latency" value={metrics.avg_llm_latency} unit="s" trend="down" iconPath="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" accentClass="text-yellow-400" />
              <MetricCard label="Cache Hit Rate" value={metrics.cache_hit_rate} unit="%" trend="up" iconPath="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" accentClass="text-green-400" />
              <MetricCard label="Active AI Agents" value={metrics.active_ai_agents} trend="neutral" iconPath="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" accentClass="text-purple-400" />
              <MetricCard label="GCP Credit Burn (Today)" value={`$${metrics.gcp_credit_burn}`} trend="down" iconPath="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6A.75.75 0 012.25 5.25v-.75m0 0A2.25 2.25 0 014.5 2.25h15A2.25 2.25 0 0121.75 4.5m-18 0v.75A.75.75 0 003 6a.75.75 0 00.75-.75v-.75m0 0h15" accentClass="text-red-400"/>
              <MetricCard label="Critical Errors (24hr)" value={metrics.critical_errors} trend="down" iconPath="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" accentClass="text-red-400"/>
            </>
          ) : (
            <p className="text-xs text-center text-gray-500 p-1">
              No metrics data available.
            </p>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card 
            title="Local Hardware Insights" 
            titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-purple-400" />}
        >
          <div className="space-y-1.5 text-xs">
            <DetailItem label="Server">{hwReport.local_capabilities.server_details}</DetailItem>
            <DetailItem label="Laptop">{hwReport.local_capabilities.laptop_details}</DetailItem>
            <DetailItem label="VLLM/TGI Compatible" highlight={!hwReport.local_capabilities.gpu_acceleration_vllm_tgi_compatible}>
                <span className={hwReport.local_capabilities.gpu_acceleration_vllm_tgi_compatible ? 'text-green-400' : 'text-red-400'}>
                    {hwReport.local_capabilities.gpu_acceleration_vllm_tgi_compatible ? 'Yes' : 'No'}
                </span>
            </DetailItem>
            {!hwReport.local_capabilities.gpu_acceleration_vllm_tgi_compatible && <DetailItem label="Reason">{hwReport.local_capabilities.reason_vllm_tgi_incompatibility}</DetailItem>}
            <DetailItem label="Max Local CPU LLM (Ollama)">{hwReport.local_capabilities.max_local_llm_cpu_inference_ollama}</DetailItem>
            <DetailItem label="Est. Local CPU Tokens/sec (7B q4)">{hwReport.local_capabilities.estimated_local_7b_q4_tokens_sec_cpu_ollama}</DetailItem>
            <div>
              <h4 className="font-medium text-gray-200 mt-1.5 mb-0.5 text-xs">Key Limitations:</h4>
              <ul className="list-disc list-inside pl-2.5 text-gray-300 space-y-0.5 text-xs">
                {hwReport.local_capabilities.limitations.map((lim, i) => <li key={i}>{lim}</li>)}
              </ul>
            </div>
          </div>
        </Card>

        <Card 
            title="Cloud Strategy & Resource Plan" 
            titleIcon={<Icon path={ICON_LIGHT_BULB} className="w-5 h-5 text-yellow-400" />}
        >
          <div className="space-y-1.5 text-xs">
            <DetailItem label="Primary LLM Hosting" highlight>{hwReport.cloud_requirements_and_strategy.primary_llm_hosting_optimized}</DetailItem>
            <DetailItem label="Embedding (Primary)">{hwReport.cloud_requirements_and_strategy.embedding_model_preference.primary.provider} - {hwReport.cloud_requirements_and_strategy.embedding_model_preference.primary.model} ({hwReport.cloud_requirements_and_strategy.embedding_model_preference.primary.cost_notes})</DetailItem>
            {hwReport.cloud_requirements_and_strategy.embedding_model_preference.alternative && <DetailItem label="Embedding (Alt)">{hwReport.cloud_requirements_and_strategy.embedding_model_preference.alternative.provider} - {hwReport.cloud_requirements_and_strategy.embedding_model_preference.alternative.model} ({hwReport.cloud_requirements_and_strategy.embedding_model_preference.alternative.cost_notes})</DetailItem>}
            <DetailItem label="Vertex GPU (Balanced)">{hwReport.cloud_requirements_and_strategy.vertex_ai_gpu_config_balanced}</DetailItem>
            <DetailItem label="Vertex GPU (Powerful)">{hwReport.cloud_requirements_and_strategy.vertex_ai_gpu_config_powerful}</DetailItem>
            <DetailItem label="Est. T4 VM Cost (Vertex)">{hwReport.cloud_requirements_and_strategy.estimated_cost_t4_vm_vertex}</DetailItem>
            <div>
              <h4 className="font-medium text-gray-200 mt-1.5 mb-0.5 text-xs">Credit Optimization Focus:</h4>
              <ul className="list-disc list-inside pl-2.5 text-gray-300 space-y-0.5 text-xs">
                {(hwReport.cloud_requirements_and_strategy.credit_optimization_strategies || []).map((strat, i) => <li key={i}>{strat}</li>)}
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default MonitoringPanel;
