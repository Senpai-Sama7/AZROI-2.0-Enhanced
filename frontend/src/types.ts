export interface ArchitectGoal {
  id: string; // Unique ID for the goal, can be initially frontend-generated, then updated by backend
  text: string;
  analysis?: string; // From Frontend Gemini call for initial refinement
  status: 
    | 'pending'         // Frontend: awaiting submission or initial backend ack
    | 'analyzing'       // Frontend: client-side Gemini analysis in progress
    | 'processing'      // Backend: General term, specific stage below, or if specific stage not yet known
    | 'PLANNING'
    | 'CODE_GENERATION'
    | 'GCS_UPLOAD'
    | 'ARTIFACT_REGISTRY_REPO_CREATE' // Added to match backend task types
    | 'CLOUD_BUILD'
    | 'CLOUD_RUN_DEPLOYMENT'
    | 'completed'
    | 'error';
  processingError?: string | null; // Stores error messages from backend processing
}

export interface Agent {
  id: string; // Agent name or unique ID from backend
  name: string;
  role: string;
  status: 
    | 'idle' 
    | 'active' 
    | 'processing' // Generic processing state
    | 'completed' 
    | 'error' 
    // Specific states mirroring ArchitectGoal states if an agent is responsible for that phase
    | 'PLANNING' 
    | 'CODE_GENERATION' 
    | 'GCS_UPLOAD'
    | 'ARTIFACT_REGISTRY_REPO_CREATE'
    | 'CLOUD_BUILD'
    | 'CLOUD_RUN_DEPLOYMENT';
  currentTask?: string;
}

export interface ArchitectOutput {
  type: 
    | 'plan' 
    | 'code_file' // Represents information about a generated code file/directory
    | 'dockerfile' // Represents information about a generated Dockerfile
    | 'gcs_uri' // URI for uploaded source archive in GCS
    | 'cloud_build_log_url' // URL to the Cloud Build logs
    | 'artifact_registry_image_uri' // URI for the built image in Artifact Registry
    | 'cloud_run_url' // URL for the deployed Cloud Run service
    | 'report' // General reports or summaries
    | 'log'; // For logs from agents or system
  title: string; 
  content: string; // Main textual content (log message, plan snippet, file path if not in metadata, etc.)
  timestamp: Date; // Should be a Date object on frontend
  sourceAgent?: string; // Name of the agent or system component that generated this output
  url?: string; // For clickable links (GCS, Cloud Run, Build Logs, etc.)
  category?: 'initial_plan' | 'generated_code' | 'dockerization_artifact' | 'gcs_artifact' | 'cloud_build_artifact' | 'cloud_run_service' | 'general_log' | 'system_status' | 'error_log';
  metadata?: Record<string, any>; // e.g. {filePath: 'main.py', entrypoint: 'main.py', dependencies: 'requirements.txt'} for code_file
  level?: 'INFO' | 'ERROR' | 'DEBUG' | 'WARNING'; // For logs
}

// Hardware and Cloud Info types remain as they are for MonitoringPanel (mocked data)
export interface HardwareInfo {
  server_details: string;
  laptop_details: string;
  gpu_acceleration_vllm_tgi_compatible: boolean;
  reason_vllm_tgi_incompatibility: string;
  max_local_llm_cpu_inference_ollama: string;
  estimated_local_7b_q4_tokens_sec_cpu_ollama: string;
  limitations: string[];
}

export interface CloudInfo {
  primary_llm_hosting_optimized: string;
  embedding_model_preference: {
    primary: { provider: string; model: string; dimensions: number; cost_notes: string };
    alternative?: { provider:string; model: string; dimensions: number; cost_notes: string };
  };
  vertex_ai_gpu_config_balanced: string;
  vertex_ai_gpu_config_powerful: string;
  estimated_cost_t4_vm_vertex: string;
  credit_optimization_strategies: string[];
}

export interface HwReport {
  local_capabilities: HardwareInfo;
  cloud_requirements_and_strategy: CloudInfo;
}

export enum ViewMode {
  GOAL_INPUT = 'GOAL_INPUT',
  DASHBOARD = 'DASHBOARD',
  MONITORING = 'MONITORING',
  CONFIG = 'CONFIG',
  HELP_SETTINGS = 'HELP_SETTINGS',
}


// WebSocket Message Types aligned with backend implementation
// (Based on README.md and typical agent interactions)

export type WebSocketLogMessage = {
  type: 'log';
  goal_id: string;
  source: string; // Agent name, "System", "Frontend", "OpenInterpreter"
  content: string;
  timestamp: string; // ISO string from backend
  level?: 'INFO' | 'ERROR' | 'DEBUG' | 'WARNING'; // Matches ArchitectOutput['level']
};

export type WebSocketAgentUpdateMessage = {
  type: 'agent_update';
  goal_id: string;
  agent: Agent; // Full agent object or partial update. Backend should send full for simplicity.
};

export type WebSocketOutputArtifactMessage = {
  type: 'output_artifact';
  goal_id: string;
  // Backend sends ArchitectOutput with timestamp as string, and other fields matching ArchitectOutput
  output: Omit<ArchitectOutput, 'timestamp'> & { timestamp: string };
};

export type WebSocketGoalStatusUpdateMessage = {
  type: 'goal_status_update';
  goal_id: string;
  status: ArchitectGoal['status'];
  message?: string; // Optional accompanying message for the status update
  error_message?: string; // Specific error message if status is 'error'
};

export type WebSocketErrorMessage = { // For general backend errors not tied to a specific other message type
  type: 'error'; // General, non-specific error from backend
  goal_id?: string; // Optional, if the error is specific to a goal processing context
  message: string;
  timestamp: string; // ISO string
};

export type WebSocketMessage = 
  | WebSocketLogMessage
  | WebSocketAgentUpdateMessage
  | WebSocketOutputArtifactMessage
  | WebSocketGoalStatusUpdateMessage
  | WebSocketErrorMessage;
