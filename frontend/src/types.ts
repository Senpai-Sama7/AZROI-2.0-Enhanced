export interface ArchitectGoal {
  id?: string;
  text: string;
  status: 'pending' | 'analyzing' | 'processing' | 'planning' | 'code_generation' | 'gcs_upload' | 'artifact_registry_repo_create' | 'cloud_build' | 'cloud_run_deployment' | 'completed' | 'error';
  analysis?: string;
  submitTime?: string; // ISO datetime string
  completionTime?: string; // ISO datetime string
  processingError?: string | null;
}

export interface Agent {
  id?: string;
  name: string;
  role: string;
  status: 'idle' | 'active' | 'completed' | 'error';
  currentTask?: string;
}

export interface ArchitectOutput {
  id?: string;
  goalId?: string;
  type: 'log' | 'plan' | 'code_file' | 'dockerfile' | 'gcs_uri' | 'cloud_build_log_url' | 'artifact_registry_image_uri' | 'cloud_run_url' | 'report';
  title: string;
  content: string;
  url?: string; // For outputs that have an external link (e.g., Cloud Run URL)
  timestamp: string; // ISO datetime string
  level?: 'INFO' | 'WARNING' | 'ERROR'; // For log entries
  sourceAgent?: string; // Which agent produced this output
  metadata?: Record<string, any>; // Additional metadata
}

export interface SystemStatus {
  backend_health: 'healthy' | 'degraded' | 'unhealthy';
  websocket_status: 'connected' | 'disconnected' | 'error';
  open_interpreter_status: 'running' | 'stopped' | 'error';
  memory_usage_percent: number;
  cpu_usage_percent: number;
  disk_usage_percent: number;
  agent_count: number;
  message_count: number;
  last_updated: string;
}

export interface WebSocketMessage {
  event: 'agent_update' | 'output_update' | 'goal_update' | 'error' | 'heartbeat';
  data: {
    goal_id?: string;
    agent?: Agent;
    output?: ArchitectOutput;
    goal_status?: string;
    error?: string;
    timestamp?: string;
  };
}
