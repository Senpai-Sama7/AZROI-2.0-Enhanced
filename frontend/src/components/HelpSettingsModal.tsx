import React, { useState, useEffect, useCallback } from 'react';
import Card from './common/Card';
import Button from './common/Button';
import Icon from './common/Icon';
import { 
    ICON_KEY, ICON_SAVE, ICON_TRASH, ICON_CHECK_CIRCLE, ICON_EXCLAMATION_TRIANGLE, 
    ICON_QUESTION_MARK_CIRCLE, LOCAL_STORAGE_API_KEY 
} from '../constants';
import { checkApiKeyValidity, reinitializeGeminiClient } from '../services/geminiService';
import LoadingSpinner from './common/LoadingSpinner'; 

interface HelpSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const HelpSettingsModal: React.FC<HelpSettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'help' | 'settings'>('help');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [storedApiKey, setStoredApiKey] = useState<string | null>(null);
  const [validationStatus, setValidationStatus] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isCheckingKey, setIsCheckingKey] = useState<boolean>(false);
  const [hasKeyChanged, setHasKeyChanged] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      const key = localStorage.getItem(LOCAL_STORAGE_API_KEY);
      setStoredApiKey(key);
      setApiKeyInput(key || '');
      setHasKeyChanged(false);
      setValidationStatus(null); 
    }
  }, [isOpen]);

  // Handler for API key input changes
  const handleApiKeyInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setApiKeyInput(newValue);
    // Check if the current input is different from the stored key
    setHasKeyChanged(newValue.trim() !== storedApiKey);
  }, [storedApiKey]);

  const handleSaveKey = useCallback(() => {
    if (apiKeyInput.trim()) {
      localStorage.setItem(LOCAL_STORAGE_API_KEY, apiKeyInput.trim());
      setStoredApiKey(apiKeyInput.trim());
      setValidationStatus({ message: 'Client-side API Key secured and ready for use!', type: 'success' });
      reinitializeGeminiClient(); 
    } else {
      setValidationStatus({ message: 'API Key field cannot be empty for saving.', type: 'error' });
    }
  }, [apiKeyInput]);

  const handleDeleteKey = useCallback(() => {
    localStorage.removeItem(LOCAL_STORAGE_API_KEY);
    setStoredApiKey(null);
    setApiKeyInput('');
    setValidationStatus({ message: 'Client-side API Key has been cleared from local storage.', type: 'info' });
    reinitializeGeminiClient();
  }, []);

  const handleCheckKey = useCallback(async () => {
    const keyToTest = apiKeyInput.trim() || storedApiKey;
    if (!keyToTest) {
      setValidationStatus({ message: 'No API Key to validate. Please enter or save one for client-side analysis.', type: 'error' });
      return;
    }
    setIsCheckingKey(true);
    setValidationStatus(null);
    const result = await checkApiKeyValidity(keyToTest);
    setValidationStatus({ message: result.message, type: result.valid ? 'success' : 'error' });
    setIsCheckingKey(false);
  }, [apiKeyInput, storedApiKey]);

  if (!isOpen) return null;

  const labelBaseClass = "block text-xs font-medium text-gray-300 mb-1";

  const renderHelpContent = () => (
    <div className="prose prose-sm prose-invert max-w-none text-gray-300 leading-relaxed space-y-3 custom-scrollbar text-xs">
      <h2 className="text-lg font-semibold text-gray-100 border-b border-gray-700/60 pb-1.5 mb-2.5">Navigating the AI Architect UI</h2>
      <p>Welcome! This interface allows you to define project goals and oversee an AI system that architects and implements them, leveraging a functional backend for processing.</p>
      
      <section>
        <h3 className="text-md font-medium text-pink-400 mb-1.5">Core Workflow:</h3>
        <ol className="list-decimal list-outside space-y-1 pl-4">
          <li><strong>Client-Side API Key (Optional):</strong> In the "Client API Key" tab, enter your Google Gemini API Key. This is ONLY for the "Analyze (Client-Side)" button in the "Architect" view. It's stored in your browser.</li>
          <li><strong>Backend Configuration:</strong> Critical backend API keys (for Gemini, GCP, Open Interpreter model providers like Azure OpenAI) MUST be configured in the `backend/.env` file as per `README.md`. The "Configure" view allows tweaking some backend settings via an API.</li>
          <li><strong>Define Your Vision:</strong> In the "Architect" view, describe your project objective.</li>
          <li><strong>Submit to Backend:</strong> Click "Set Vision". This sends your goal to the backend, which triggers the full AI pipeline: planning, code generation, and cloud deployment.</li>
          <li><strong>Monitor Progress:</strong> The "Dashboard" view shows real-time logs, agent statuses, and artifact links (GCS URLs, Cloud Run URLs etc.) streamed from the backend.</li>
          <li><strong>System Vitals (Mocked):</strong> The "Monitor" view provides (currently mocked) performance metrics.</li>
        </ol>
      </section>

      <section>
        <h3 className="text-md font-medium text-pink-400 mb-1.5">Understanding the Views:</h3>
        <ul className="list-disc list-outside space-y-1 pl-4">
            <li><strong>Architect:</strong> Your starting point for defining project goals.</li>
            <li><strong>Dashboard:</strong> Central hub for tracking real-time progress from the backend.</li>
            <li><strong>Monitor:</strong> (Mocked Data) System performance insights.</li>
            <li><strong>Configure:</strong> Adjust backend operational parameters via API.</li>
        </ul>
      </section>
      
      <section className="mt-4 p-2.5 bg-gray-800/50 border border-red-600/50 rounded-md shadow-sm">
        <h4 className="text-sm font-semibold text-red-400 flex items-center mb-1">
            <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-3.5 h-3.5 mr-1.5" />
            Important Note on API Keys
        </h4>
        <p className="text-xs text-gray-400">The API key managed here is for client-side analysis only. The main AI processing and cloud interactions use API keys and service accounts configured securely in the backend (`backend/.env`, `secrets/`).</p>
      </section>
    </div>
  );

  const renderSettingsContent = () => (
    <div className="space-y-4 text-xs">
      <h3 className="text-md font-semibold text-gray-100">Client-Side Gemini API Key</h3>
      <p className="text-gray-400">
        This API Key is ONLY for the optional "Analyze (Client-Side)" feature. It's stored in your browser.
      </p>
      <div>
        <label htmlFor="apiKeyInput" className={labelBaseClass}>
          Enter Client-Side Gemini API Key:
        </label>
        <div className="flex items-center space-x-2">
          <input
            type="password"
            id="apiKeyInput"
            value={apiKeyInput}
            onChange={(e) => handleApiKeyInputChange(e)}
            placeholder="AIzaSy..."
            className="w-full form-input-themed text-xs flex-grow"
            aria-label="Client-Side Gemini API Key Input"
          />
        </div>
        {storedApiKey && <p className="text-xs text-gray-500 mt-1">An API key is currently stored for client-side analysis.</p>}
        {!storedApiKey && <p className="text-xs text-red-400/80 mt-1">No client-side API key stored. Client-side analysis is disabled.</p>}
      </div>

      <div className="flex flex-wrap gap-2 items-center pt-1">
        <Button 
          onClick={handleSaveKey} 
          variant="primary" 
          size="md" 
          leftIcon={<Icon path={ICON_SAVE} />}
          disabled={!hasKeyChanged || !apiKeyInput.trim()}
        >
          Save Key
        </Button>
        <Button onClick={handleCheckKey} variant="outline" size="md" leftIcon={<Icon path={ICON_CHECK_CIRCLE} />} isLoading={isCheckingKey} disabled={!apiKeyInput.trim() && !storedApiKey}>
          Check Validity
        </Button>
        {storedApiKey && (
          <Button onClick={handleDeleteKey} variant="danger" size="sm" leftIcon={<Icon path={ICON_TRASH} />}>
            Delete Key
          </Button>
        )}
      </div>

      {isCheckingKey && <LoadingSpinner text="Validating API key..." className="mt-2" variant="pink" size="sm" />}

      {validationStatus && (
        <div className={`mt-2.5 p-2 text-xs rounded-md border flex items-start space-x-1.5 shadow-sm ${
          validationStatus.type === 'success' ? 'bg-green-700/20 text-green-300 border-green-600/40' : 
          validationStatus.type === 'error' ? 'bg-red-800/20 text-red-300 border-red-600/40' : 
          'bg-blue-700/20 text-blue-300 border-blue-600/40'
        }`}>
          <Icon path={validationStatus.type === 'success' ? ICON_CHECK_CIRCLE : ICON_EXCLAMATION_TRIANGLE} className="w-3.5 h-3.5 mt-px flex-shrink-0" />
          <span className="font-medium">{validationStatus.message}</span>
        </div>
      )}
    </div>
  );

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 z-50 animate-fade-in" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="help-settings-title"
    >
      <Card 
        className="w-full max-w-md max-h-[90vh] flex flex-col shadow-2xl !p-0" // Modal card styling
        onClick={e => e.stopPropagation()}
      >
        <div className="px-4 py-2.5 border-b border-gray-700/60 flex justify-between items-center">
            <h2 id="help-settings-title" className="text-md font-semibold text-gray-100 flex items-center">
                <Icon path={ICON_QUESTION_MARK_CIRCLE} className="w-4 h-4 mr-1.5 text-pink-400" />
                Help & Client API Key
            </h2>
        </div>
        <div className="border-b border-gray-700/60">
          <nav className="flex space-x-0.5 px-3" aria-label="Tabs">
            {(['help', 'settings'] as const).map(tabName => (
              <button
                key={tabName}
                onClick={() => setActiveTab(tabName)}
                role="tab"
                aria-selected={activeTab === tabName}
                className={`whitespace-nowrap py-2 px-2.5 border-b-2 font-medium text-xs capitalize transition-colors duration-200 focus:outline-none hover:bg-gray-700/30 rounded-t-sm
                  ${activeTab === tabName
                    ? 'border-pink-500 text-pink-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-600/40'
                  }`}
              >
                {tabName === 'help' ? 'How to Use' : 'Client API Key'}
              </button>
            ))}
          </nav>
        </div>
        
        <div className="p-3 overflow-y-auto flex-grow custom-scrollbar min-h-[200px] bg-gray-800/30">
          {activeTab === 'help' ? renderHelpContent() : renderSettingsContent()}
        </div>

        <div className="px-4 py-2 bg-gray-800/60 border-t border-gray-700/60 text-right">
          <Button onClick={onClose} variant="subtle" size="md">Close</Button>
        </div>
      </Card>
    </div>
  );
};

export default HelpSettingsModal;
