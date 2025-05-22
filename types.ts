
export interface ArchitectGoal {
  id: string;
  text: string;
  analysis?: string; // From Gemini
  status: 'pending' | 'analyzing' | 'analyzed' | 'processing' | 'completed' | 'error';
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'active' | 'completed' | 'error';
  currentTask?: string;
}

export interface ArchitectOutput {
  type: 'plan' | 'code' | 'report' | 'log';
  title: string;
  content: string;
  timestamp: Date;
}

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

// Enums should be standard enums
export enum ViewMode {
  GOAL_INPUT = 'GOAL_INPUT',
  DASHBOARD = 'DASHBOARD',
  MONITORING = 'MONITORING',
  CONFIG = 'CONFIG',
  HELP_SETTINGS = 'HELP_SETTINGS', // Added Help & Settings view
}
