// Core icon paths used throughout the application
export const ICON_TERMINAL = "M6 9a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V11a2 2 0 00-2-2h-2a2 2 0 01-2-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v2a2 2 0 012 2z";
export const ICON_DOCUMENT_TEXT = "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z";
export const ICON_CHEVRON_DOWN = "M19 9l-7 7-7-7";
export const ICON_COG = "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z";
export const ICON_LIGHT_BULB = "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z";
export const ICON_EXCLAMATION_TRIANGLE = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z";
export const ICON_SAVE = "M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4";
export const ICON_CHECK_CIRCLE = "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z";
export const ICON_LINK_EXTERNAL = "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14";
export const ICON_CODE = "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4";
export const ICON_X = "M6 18L18 6M6 6l12 12";
export const ICON_QUESTION_MARK_CIRCLE = "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z";
export const ICON_KEY = "M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z";
export const ICON_SWITCH_HORIZONTAL = "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4";
export const ICON_INFORMATION_CIRCLE = "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z";

export const MOCK_HW_REPORT = { // This data is for the MonitoringPanel and remains as is.
  local_capabilities: {
    server_details: "Intel Core i5-7300U, 15GB RAM, Intel HD Graphics 620",
    laptop_details: "HP EliteBook 840 G4, i5-6300U, 20GB RAM, Intel HD Graphics 520",
    gpu_acceleration_vllm_tgi_compatible: false,
    reason_vllm_tgi_incompatibility: "No compatible NVIDIA GPU with sufficient VRAM. Intel iGPUs not supported for performant VLLM/TGI.",
    max_local_llm_cpu_inference_ollama: "Llama-2-7B (4-bit quantized, e.g., GGUF q4_K_M), Mistral-7B (Q4)",
    estimated_local_7b_q4_tokens_sec_cpu_ollama: "0.5-3 tokens/sec (highly dependent on exact setup, model, and CPU load)",
    limitations: [
      "No dedicated local NVIDIA GPU for VLLM/TGI acceleration, severely limiting local LLM performance.",
      "CPU-bound local LLM inference will be too slow for most interactive or complex agent tasks.",
      "Shared system memory for iGPUs means insufficient dedicated VRAM for any meaningful LLM acceleration, even if experimental runners existed."
    ]
  },
  cloud_requirements_and_strategy: {
    primary_llm_hosting_optimized: "Self-hosted vLLM/TGI on GCP Vertex AI (NVIDIA T4/A100 VMs) managed by Terraform for cost-control and model flexibility, OR OpenAI/Anthropic APIs for ease of use with powerful models.",
    embedding_model_preference: {
      primary: { provider: "OpenAI", model: "text-embedding-3-small", dimensions: 1536, cost_notes: "Highly cost-effective, good performance." },
      alternative: { provider: "SentenceTransformers", model: "Supabase/gte-small", dimensions: 384, cost_notes: "Free, open-source, good for budget constraints or offline needs." }
    },
    vertex_ai_gpu_config_balanced: "Vertex AI Prediction Endpoint with n1-standard-4 machine type and NVIDIA T4 GPU (for serving models via vLLM/TGI).",
    vertex_ai_gpu_config_powerful: "Vertex AI Prediction Endpoint with a2-highgpu-1g machine type and NVIDIA A100 GPU (for larger models or higher throughput via vLLM/TGI).",
    estimated_cost_t4_vm_vertex: "Approx. $0.35-$0.70/hr for GPU, plus VM cost. Check current GCP pricing for Prediction endpoints.",
    credit_optimization_strategies: [
      "Utilize Dialogflow CX and GenAI App Builder credits for their specific services first.",
      "Deploy stateless application components to Cloud Run (managed by Terraform) using custom containers.",
      "For VLLM/TGI on Vertex AI, use model scaling settings (min/max replicas) to manage costs based on demand; consider spot VMs for non-critical batch inference if applicable.",
      "Implement aggressive caching (Redis) for LLM responses and embeddings.",
      "Dynamically route LLM tasks to the most cost-effective model/provider based on real-time performance metrics and task requirements."
    ]
  }
};

export const GEMINI_MODEL_NAME = 'gemini-2.5-flash-preview-04-17'; // Updated for client-side analysis & key validatione analysis & key validation
export const LOCAL_STORAGE_API_KEY = 'autonomousAIApiKey'; // For client-side Gemini API Key
export const LOCAL_STORAGE_CONFIG_KEY = 'autonomousAIConfig'; // For ConfigPanel if it ever needs local storage (currently API-driven)export const LOCAL_STORAGE_CONFIG_KEY = 'autonomousAIConfig'; // For ConfigPanel if it ever needs local storage (currently API-driven)

