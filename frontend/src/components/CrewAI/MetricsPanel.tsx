import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ClockIcon,
  CurrencyDollarIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  UserGroupIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowUpIcon,
  ArrowDownIcon
} from '@heroicons/react/24/outline';
import type { CrewMetrics, CrewSession } from '../../types/crewai';

interface MetricsPanelProps {
  metrics: CrewMetrics;
  session: CrewSession;
  className?: string;
}

const MetricsPanel: React.FC<MetricsPanelProps> = ({
  metrics,
  session,
  className = ''
}) => {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [selectedMetric, setSelectedMetric] = useState<string>('overview');

  // Calculate trend data
  const trendData = useMemo(() => {
    const trends = metrics.performance_trends || [];
    const recent = trends.slice(-10); // Last 10 data points
    
    if (recent.length < 2) return { tasksPerHour: 0, errorRate: 0, collaboration: 0 };

    const current = recent[recent.length - 1];
    const previous = recent[recent.length - 2];

    return {
      tasksPerHour: ((current.tasks_per_hour - previous.tasks_per_hour) / previous.tasks_per_hour) * 100,
      errorRate: ((current.error_rate - previous.error_rate) / previous.error_rate) * 100,
      collaboration: ((current.collaboration_rate - previous.collaboration_rate) / previous.collaboration_rate) * 100
    };
  }, [metrics.performance_trends]);

  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    subtitle?: string;
    trend?: number;
    icon: React.ComponentType<any>;
    color: string;
    onClick?: () => void;
  }> = ({ title, value, subtitle, trend, icon: Icon, color, onClick }) => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className={`glass-card p-6 cursor-pointer transition-all ${color}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <Icon className="w-5 h-5" />
            <span className="text-sm font-medium text-gray-300">{title}</span>
          </div>
          <div className="text-2xl font-bold text-white mb-1">{value}</div>
          {subtitle && (
            <div className="text-xs text-gray-400">{subtitle}</div>
          )}
        </div>
        {trend !== undefined && (
          <div className={`flex items-center space-x-1 ${
            trend > 0 ? 'text-green-400' : trend < 0 ? 'text-red-400' : 'text-gray-400'
          }`}>
            {trend > 0 ? (
              <ArrowUpIcon className="w-4 h-4" />
            ) : trend < 0 ? (
              <ArrowDownIcon className="w-4 h-4" />
            ) : null}
            <span className="text-sm font-medium">{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Agents"
          value={metrics.total_agents}
          subtitle={`${metrics.active_agents} active`}
          icon={UserGroupIcon}
          color="bg-blue-500/20"
        />
        
        <MetricCard
          title="Completed Tasks"
          value={metrics.completed_tasks}
          subtitle={`${metrics.failed_tasks} failed`}
          trend={trendData.tasksPerHour}
          icon={CheckCircleIcon}
          color="bg-green-500/20"
        />
        
        <MetricCard
          title="Avg Task Time"
          value={`${Math.round(metrics.avg_task_time)}s`}
          subtitle="Per task completion"
          icon={ClockIcon}
          color="bg-purple-500/20"
        />
        
        <MetricCard
          title="Efficiency Score"
          value={`${Math.round(metrics.efficiency_score * 100)}%`}
          subtitle={`Quality: ${Math.round(metrics.quality_score * 100)}%`}
          icon={TrendingUpIcon}
          color="bg-orange-500/20"
        />
      </div>

      {/* Cost and Collaboration Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <CurrencyDollarIcon className="w-5 h-5" />
            <span>Cost Analysis</span>
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Total Tokens</span>
              <span className="text-white font-medium">
                {metrics.cost_metrics.total_tokens.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Estimated Cost</span>
              <span className="text-white font-medium">
                ${metrics.cost_metrics.estimated_cost.toFixed(4)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Cost per Task</span>
              <span className="text-white font-medium">
                ${metrics.cost_metrics.cost_per_task.toFixed(6)}
              </span>
            </div>
            <div className="pt-3 border-t border-gray-700">
              <div className="text-xs text-gray-400">
                Cost efficiency: {metrics.completed_tasks > 0 ? 
                  (metrics.cost_metrics.estimated_cost / metrics.completed_tasks * 1000).toFixed(2) : '0'
                }¢ per completed task
              </div>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
            <UserGroupIcon className="w-5 h-5" />
            <span>Collaboration Stats</span>
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Collaboration Events</span>
              <span className="text-white font-medium">{metrics.collaboration_events}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Events per Agent</span>
              <span className="text-white font-medium">
                {(metrics.collaboration_events / metrics.total_agents).toFixed(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Collaboration Rate</span>
              <div className="flex items-center space-x-2">
                <span className="text-white font-medium">
                  {metrics.performance_trends.length > 0 ? 
                    (metrics.performance_trends[metrics.performance_trends.length - 1].collaboration_rate * 100).toFixed(1) : '0'
                  }%
                </span>
                {trendData.collaboration !== 0 && (
                  <span className={`text-xs flex items-center ${
                    trendData.collaboration > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {trendData.collaboration > 0 ? <ArrowUpIcon className="w-3 h-3" /> : <ArrowDownIcon className="w-3 h-3" />}
                    {Math.abs(trendData.collaboration).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
          <ChartBarIcon className="w-5 h-5" />
          <span>Performance Trends</span>
        </h3>
        <PerformanceChart trends={metrics.performance_trends} />
      </div>
    </div>
  );

  return (
    <div className={`metrics-panel ${className}`}>
      {/* Time Range Selector */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Performance Metrics</h2>
        <div className="flex space-x-1 bg-black/20 rounded-lg p-1">
          {[
            { id: '1h', label: '1H' },
            { id: '6h', label: '6H' },
            { id: '24h', label: '24H' },
            { id: '7d', label: '7D' }
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTimeRange(id as any)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${
                timeRange === id
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Session Summary */}
      <div className="mb-6 glass-card p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">{session.name}</h3>
            <p className="text-gray-400">{session.goal}</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Session Progress</div>
            <div className="text-xl font-bold text-white">{session.progress_percentage}%</div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      {renderOverview()}
    </div>
  );
};

// Performance Chart Component
const PerformanceChart: React.FC<{ trends: any[] }> = ({ trends }) => {
  if (!trends || trends.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <ChartBarIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No performance data available</p>
        </div>
      </div>
    );
  }

  // Simple chart visualization - in a real app, you'd use a charting library
  const maxTasksPerHour = Math.max(...trends.map(t => t.tasks_per_hour));
  const maxErrorRate = Math.max(...trends.map(t => t.error_rate));

  return (
    <div className="h-64 relative">
      <div className="absolute inset-0 flex items-end space-x-1">
        {trends.slice(-20).map((trend, index) => (
          <div key={index} className="flex-1 flex flex-col space-y-1">
            {/* Tasks per hour bar */}
            <div
              className="bg-blue-500 w-full rounded-t"
              style={{
                height: `${(trend.tasks_per_hour / maxTasksPerHour) * 80}px`,
                minHeight: '2px'
              }}
              title={`Tasks/hour: ${trend.tasks_per_hour.toFixed(1)}`}
            />
            {/* Error rate bar */}
            <div
              className="bg-red-500 w-full"
              style={{
                height: `${(trend.error_rate / maxErrorRate) * 40}px`,
                minHeight: '1px'
              }}
              title={`Error rate: ${(trend.error_rate * 100).toFixed(1)}%`}
            />
          </div>
        ))}
      </div>
      
      {/* Y-axis labels */}
      <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-400">
        <span>{maxTasksPerHour.toFixed(1)}</span>
        <span>{(maxTasksPerHour / 2).toFixed(1)}</span>
        <span>0</span>
      </div>
      
      {/* Legend */}
      <div className="absolute top-2 right-2 flex space-x-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-blue-500 rounded" />
          <span className="text-gray-400">Tasks/Hour</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-500 rounded" />
          <span className="text-gray-400">Error Rate</span>
        </div>
      </div>
    </div>
  );
};

export default MetricsPanel;
