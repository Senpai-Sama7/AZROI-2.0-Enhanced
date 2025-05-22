import React, { useState, useEffect } from 'react';
import Card from './common/Card';
import Button from './common/Button';
import Icon from './common/Icon';
import { ICON_COG, ICON_SAVE, ICON_CHECK_CIRCLE, ICON_EXCLAMATION_TRIANGLE, ICON_CHEVRON_DOWN } from '../constants';
import LoadingSpinner from './common/LoadingSpinner';

// This interface reflects the structure of `backend/config.json`
// and what the backend API GET /api/config returns and POST /api/config expects.
interface BackendConfig {
  default_llm_model_backend?: string;
  log_level?: string;
  max_concurrent_agents?: number;
  planner_agent_prompt_template?: string;
  code_execution_timeout_seconds?: number;
  output_base_path_code_executions?: string; // Read-only from backend config
  default_generated_app_port?: number;
  cloud_build_timeout_seconds?: string;

  open_interpreter_config?: {
    model_string_fallback?: string;
    azure_api_key_env_var?: string; 
    azure_api_base_env_var?: string; 
    azure_api_version_env_var?: string; 
    azure_deployment_id_env_var?: string; 
    openai_api_key_env_var?: string; 
    auto_run?: boolean;
    safe_mode?: 'off' | 'ask' | 'auto';
    system_message?: string;
    max_retries?: number;
  };

  gcp_config_defaults?: { 
    project_id?: string; 
    region?: string; 
    gcs_bucket_name?: string; 
    artifact_registry_repository?: string; 
    artifact_registry_region_fallback?: string; 
    cloud_run_service_prefix?: string; 
    cloud_run_allow_unauthenticated?: boolean;
  };
  
  chroma_db_config?: { 
    path?: string;
    collection_name?: string;
  };
}


const ConfigPanel: React.FC = () => {
  const [config, setConfig] = useState<Partial<BackendConfig>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ message: string; type: 'success' | 'error'} | null>(null);

  const fetchConfig = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const response = await fetch('http://localhost:8001/api/config');
      if (!response.ok) {
          const errData = await response.json().catch(()=>({detail: "Failed to load configuration from backend."}));
          throw new Error(errData.detail || 'Failed to fetch config');
      }
      const data: BackendConfig = await response.json();
      setConfig(data);
    } catch (error) {
      console.error("Error fetching config:", error);
      setFeedback({ message: error instanceof Error ? error.message : "Could not load config from backend.", type: 'error'});
      setConfig({ // Sensible defaults on error
        default_llm_model_backend: "gemini-2.5-flash-preview-04-17", 
        log_level: "INFO", 
        max_concurrent_agents: 1,
        open_interpreter_config: { auto_run: true, safe_mode: "auto"},
        gcp_config_defaults: { cloud_run_allow_unauthenticated: true }
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);


  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>, section?: keyof BackendConfig) => {
    const { name, value, type } = e.target;
    let processedValue: string | number | boolean | undefined;

    if (type === 'checkbox') {
      processedValue = (e.target as HTMLInputElement).checked;
    } else if (type === 'number') {
      // Explicitly handle empty string as undefined, 0 as 0, and parse other values
      if (value === '') {
        processedValue = undefined;
      } else {
        const parsedValue = parseInt(value, 10);
        // If we got a proper number (including 0), use it. Otherwise keep the current value.
        if (!isNaN(parsedValue)) {
          processedValue = parsedValue;
        } else {
          const currentVal = section ? (config[section] as any)?.[name] : config[name as keyof BackendConfig];
          processedValue = typeof currentVal === 'number' ? currentVal : undefined;
        }
      }
    } else {
      processedValue = value;
    }

    if (section) {
        setConfig(prev => ({
            ...prev,
            [section]: {
                ...(prev[section] as object || {}),
                [name]: processedValue
            }
        }));
    } else {
        setConfig(prev => ({ ...prev, [name]: processedValue }));
    }
    setFeedback(null); 
  };

  const handleSave = async () => {
    setIsSaving(true);
    setFeedback(null);
    try {
        const response = await fetch('http://localhost:8001/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (!response.ok) {
            const errData = await response.json().catch(()=>({detail: "Failed to save configuration to backend."}));
            throw new Error(errData.detail || "Failed to save configuration.");
        }
        const result = await response.json();
        // Backend might return the full updated config (if it modifies/validates)
        setConfig(result.updated_config || config); 
        setFeedback({ message: result.message || 'Configuration saved successfully to backend!', type: 'success'});
    } catch (error) {
        setFeedback({ message: error instanceof Error ? error.message : "Could not save config to backend.", type: 'error'});
    } finally {
        setIsSaving(false);
    }
  };

  // Helper function to safely display numeric values including 0
  const safeNumericValue = (value: number | null | undefined, defaultValue: number): number => {
    // Explicitly check for null/undefined, preserving 0 as a valid value
    return value === null || value === undefined ? defaultValue : value;
  };

  // Fields that are typically set via .env on backend and should be read-only in UI
  const oiEnvVars: (keyof NonNullable<BackendConfig['open_interpreter_config']>)[] = ['azure_api_key_env_var', 'azure_api_base_env_var', 'azure_api_version_env_var', 'azure_deployment_id_env_var', 'openai_api_key_env_var'];
  const gcpReadOnlyVars: (keyof NonNullable<BackendConfig['gcp_config_defaults']>)[] = ['project_id', 'region', 'gcs_bucket_name', 'artifact_registry_repository', 'artifact_registry_region_fallback', 'cloud_run_service_prefix'];
  const chromaReadOnlyVars: (keyof NonNullable<BackendConfig['chroma_db_config']>)[] = ['path', 'collection_name'];


  if (isLoading) {
    return (
      <Card 
        title="System Configuration Blueprint (Backend Settings)" 
        className="w-full max-w-xl mx-auto" 
        titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-yellow-400" />}
      >
        <div className="flex justify-center items-center py-10">
          <LoadingSpinner text="Loading configuration..." />
        </div>
      </Card>
    );
  }

  return (
    <Card 
      title="System Configuration Blueprint (Backend Settings)" 
      className="w-full max-w-xl mx-auto animate-slide-up"
      titleIcon={<Icon path={ICON_COG} className="w-5 h-5 text-yellow-400" />}
      bodyClassName="!p-2"
    >
      <form onSubmit={e => { e.preventDefault(); handleSave(); }} className="space-y-4">
        {/* General Settings */}
        <ConfigSection title="General">
          <InputField
            id="default_llm_model_backend"
            name="default_llm_model_backend"
            label="Default LLM Model Backend"
            value={config.default_llm_model_backend || ''}
            onChange={handleChange}
            placeholder="e.g. gpt-4, gemini-pro"
          />
          <InputField
            id="log_level"
            name="log_level"
            label="Log Level"
            value={config.log_level || ''}
            onChange={handleChange}
            type="text"
            placeholder="e.g. INFO, DEBUG"
          />
          <InputField
            id="max_concurrent_agents"
            name="max_concurrent_agents"
            label="Max Concurrent Agents"
            value={safeNumericValue(config.max_concurrent_agents, 1)}
            onChange={handleChange}
            type="number"
            min={1}
          />
        </ConfigSection>

        {/* Planner Agent Prompt */}
        <ConfigSection title="Planner Agent">
          <InputField
            id="planner_agent_prompt_template"
            name="planner_agent_prompt_template"
            label="Planner Agent Prompt Template"
            value={config.planner_agent_prompt_template || ''}
            onChange={handleChange}
            type="textarea"
            rows={3}
            placeholder="Prompt template for planner agent"
          />
        </ConfigSection>

        {/* Code Execution Settings */}
        <ConfigSection title="Code Execution">
          <InputField
            id="code_execution_timeout_seconds"
            name="code_execution_timeout_seconds"
            label="Code Execution Timeout (seconds)"
            value={safeNumericValue(config.code_execution_timeout_seconds, 60)}
            onChange={handleChange}
            type="number"
            min={1}
          />
          <InputField
            id="output_base_path_code_executions"
            name="output_base_path_code_executions"
            label="Output Base Path (Read-only)"
            value={config.output_base_path_code_executions || ''}
            onChange={handleChange}
            disabled
          />
          <InputField
            id="default_generated_app_port"
            name="default_generated_app_port"
            label="Default Generated App Port"
            value={safeNumericValue(config.default_generated_app_port, 8080)}
            onChange={handleChange}
            type="number"
            min={1}
          />
          <InputField
            id="cloud_build_timeout_seconds"
            name="cloud_build_timeout_seconds"
            label="Cloud Build Timeout (seconds)"
            value={config.cloud_build_timeout_seconds || ''}
            onChange={handleChange}
            type="text"
            placeholder="e.g. 600"
          />
        </ConfigSection>

        {/* Open Interpreter Config */}
        <ConfigSection title="Open Interpreter Config">
          {oiEnvVars.map(varName => (
            <ReadOnlyField key={varName} label={varName} value={config.open_interpreter_config?.[varName]} />
          ))}
          <InputField
            id="oi_auto_run"
            name="auto_run"
            label="Auto Run"
            value={config.open_interpreter_config?.auto_run ? 'true' : 'false'}
            onChange={handleChange}
            type="checkbox"
            section="open_interpreter_config"
          />
          <InputField
            id="oi_safe_mode"
            name="safe_mode"
            label="Safe Mode"
            value={config.open_interpreter_config?.safe_mode || 'off'}
            onChange={handleChange}
            type="text"
            section="open_interpreter_config"
            placeholder="off | ask | auto"
          />
          <InputField
            id="oi_system_message"
            name="system_message"
            label="System Message"
            value={config.open_interpreter_config?.system_message || ''}
            onChange={handleChange}
            type="textarea"
            section="open_interpreter_config"
            rows={2}
          />
          <InputField
            id="oi_max_retries"
            name="max_retries"
            label="Max Retries"
            value={safeNumericValue(config.open_interpreter_config?.max_retries, 0)}
            onChange={handleChange}
            type="number"
            section="open_interpreter_config"
            min={0}
          />
        </ConfigSection>

        {/* GCP Config Defaults */}
        <ConfigSection title="GCP Config Defaults">
          {gcpReadOnlyVars.map(varName => (
            <ReadOnlyField key={varName} label={varName} value={config.gcp_config_defaults?.[varName]} />
          ))}
          <InputField
            id="gcp_cloud_run_allow_unauthenticated"
            name="cloud_run_allow_unauthenticated"
            label="Cloud Run Allow Unauthenticated"
            value={config.gcp_config_defaults?.cloud_run_allow_unauthenticated ? 'true' : 'false'}
            onChange={handleChange}
            type="checkbox"
            section="gcp_config_defaults"
          />
        </ConfigSection>

        {/* Chroma DB Config */}
        <ConfigSection title="Chroma DB Config">
          {chromaReadOnlyVars.map(varName => (
            <ReadOnlyField key={varName} label={varName} value={config.chroma_db_config?.[varName]} />
          ))}
        </ConfigSection>

        {/* Feedback and Save Button */}
        {feedback && (
          <div className={`p-2 rounded text-xs border shadow-sm ${feedback.type === 'success' ? 'bg-green-800/20 text-green-300 border-green-600/40' : 'bg-red-800/20 text-red-300 border-red-600/40'}`}>
            {feedback.message}
          </div>
        )}
        <div className="flex justify-end">
          <button
            type="submit"
            className="px-4 py-1.5 rounded bg-pink-600 hover:bg-pink-700 text-white font-semibold text-xs shadow disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </Card>
  );
};


// Helper sub-components
interface FieldPropsBase { id: string; name: string; label: string; disabled?: boolean; section?: keyof BackendConfig; }
interface InputFieldProps extends FieldPropsBase {
  value: string | number; onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>, section?: keyof BackendConfig) => void;
  type?: string; options?: (string | {value: string; label: string})[]; min?: string | number; max?: string | number; rows?: number; placeholder?: string;
}

const InputField: React.FC<InputFieldProps> = function InputField(props: InputFieldProps) {
  const { id, name, label, value, onChange, type = "text", section, disabled, options, min, max, rows, placeholder } = props;
  const commonProps = { id, name, value: value ?? '', onChange: (e: React.ChangeEvent<any>) => onChange(e, section), disabled, className: `w-full form-input-themed text-xs ${disabled ? 'cursor-not-allowed opacity-70' : ''}` };
  const labelBaseClass = "block text-xs font-medium text-gray-300 mb-0.5";

  return (
    React.createElement('div', null,
      React.createElement('label', { htmlFor: id, className: labelBaseClass }, label),
      type === "select" ? (
        React.createElement('select', { ...commonProps, className: `${commonProps.className} select-arrow-themed pr-7` },
          options?.map(opt => typeof opt === 'string' ? React.createElement('option', { key: opt, value: opt, className: "bg-gray-700 text-gray-200" }, opt) : React.createElement('option', { key: opt.value, value: opt.value, className: "bg-gray-700 text-gray-200" }, opt.label))
        )
      ) : type === "textarea" ? (
        React.createElement('textarea', { ...commonProps, rows, placeholder, className: `${commonProps.className} h-auto resize-y custom-scrollbar` })
      ) : type === "checkbox" ? (
        React.createElement('input', { ...commonProps, type: 'checkbox', checked: value === true || value === 'true' ? true : false })
      ) : (
        React.createElement('input', { ...commonProps, type, min, max, placeholder })
      )
    )
  );
};

interface ReadOnlyFieldProps { label: string; value?: string | number | boolean; }
const ReadOnlyField: React.FC<ReadOnlyFieldProps> = function ReadOnlyField({ label, value }: ReadOnlyFieldProps) {
  return React.createElement('div', null,
    React.createElement('label', { className: "block text-xs font-medium text-gray-400 mb-0.5" }, label),
    React.createElement('input', { type: 'text', value: value === undefined || value === null ? 'Not set/from env' : String(value), className: "w-full form-input-themed text-xs !bg-gray-800/30 !border-gray-700/40 !text-gray-400 cursor-not-allowed", disabled: true })
  );
};

interface ConfigSectionProps { title: string; children: React.ReactNode; }
const ConfigSection: React.FC<ConfigSectionProps> = function ConfigSection({ title, children }: ConfigSectionProps) {
  return React.createElement('details', { className: "space-y-2.5 bg-gray-800/40 p-2.5 rounded-md border border-gray-700/50 shadow-sm", open: true },
    React.createElement('summary', { className: "text-sm font-semibold text-gray-100 cursor-pointer hover:text-pink-400 list-none flex justify-between items-center" },
      title,
      React.createElement(Icon, { path: ICON_CHEVRON_DOWN, className: "w-3.5 h-3.5 transition-transform transform details-summary-marker" })
    ),
    React.createElement('div', { className: "pt-2 space-y-2.5 border-t border-gray-700/40" }, children)
  );
};

export default ConfigPanel;
