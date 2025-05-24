// CrewAI-specific type definitions
export interface CrewAgent {
  id: string;
  name: string;
  role: string;
  goal: string;
  backstory: string;
  status: 'idle' | 'thinking' | 'executing' | 'collaborating' | 'completed' | 'error';
  current_task?: string;
  capabilities: string[];
  tools: string[];
  memory_context?: string;
  performance_metrics?: {
    tasks_completed: number;
    success_rate: number;
    avg_execution_time: number;
    collaboration_score: number;
  };
  created_at: string;
  updated_at: string;
}

export interface CrewTask {
  id: string;
  title: string;
  description: string;
  agent_id: string;
  status: 'pending' | 'in_progress' | 'review' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  dependencies: string[]; // Task IDs that must be completed first
  expected_output: string;
  actual_output?: string;
  tools_used?: string[];
  execution_time?: number;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CrewSession {
  id: string;
  name: string;
  goal: string;
  status: 'planning' | 'executing' | 'reviewing' | 'completed' | 'failed' | 'paused';
  agents: CrewAgent[];
  tasks: CrewTask[];
  workflow: 'sequential' | 'hierarchical' | 'consensus';
  max_iterations: number;
  current_iteration: number;
  collaboration_score: number;
  progress_percentage: number;
  estimated_completion?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  metadata?: {
    total_tokens_used?: number;
    total_cost?: number;
    user_id?: string;
    project_id?: string;
  };
}

export interface TaskExecution {
  id: string;
  task_id: string;
  agent_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  input_data: any;
  output_data?: any;
  error_message?: string;
  execution_time: number;
  tokens_used?: number;
  tool_calls?: ToolCall[];
  thoughts?: string;
  started_at: string;
  completed_at?: string;
}

export interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, any>;
  result?: any;
  error?: string;
  execution_time: number;
  timestamp: string;
}

export interface AgentCollaboration {
  id: string;
  from_agent_id: string;
  to_agent_id: string;
  message: string;
  message_type: 'request' | 'response' | 'delegation' | 'feedback';
  context: any;
  timestamp: string;
}

export interface CrewMetrics {
  session_id: string;
  total_agents: number;
  active_agents: number;
  completed_tasks: number;
  failed_tasks: number;
  avg_task_time: number;
  collaboration_events: number;
  efficiency_score: number;
  quality_score: number;
  cost_metrics: {
    total_tokens: number;
    estimated_cost: number;
    cost_per_task: number;
  };
  performance_trends: {
    timestamp: string;
    tasks_per_hour: number;
    error_rate: number;
    collaboration_rate: number;
  }[];
}

export interface CrewWebSocketMessage {
  event: 
    | 'session_created'
    | 'session_updated' 
    | 'session_completed'
    | 'agent_status_changed'
    | 'task_started'
    | 'task_completed'
    | 'task_failed'
    | 'collaboration_event'
    | 'metrics_update'
    | 'error';
  data: {
    session_id?: string;
    session?: CrewSession;
    agent?: CrewAgent;
    task?: CrewTask;
    execution?: TaskExecution;
    collaboration?: AgentCollaboration;
    metrics?: CrewMetrics;
    error?: string;
    timestamp: string;
  };
}
