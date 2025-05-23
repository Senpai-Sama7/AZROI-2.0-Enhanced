import React, { useState } from 'react';
import Icon from './common/Icon';
import Button from './common/Button';
import { ICON_X, ICON_QUESTION_MARK_CIRCLE, ICON_KEY, ICON_INFORMATION_CIRCLE } from '../constants';

interface HelpSettingsModalProps {
  onClose: () => void;
}

const HelpSettingsModal: React.FC<HelpSettingsModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'help' | 'about'>('help');

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white flex items-center">
            <Icon path={ICON_QUESTION_MARK_CIRCLE} className="w-6 h-6 text-blue-400 mr-2" />
            Help & Settings
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            aria-label="Close modal"
          >
            <Icon path={ICON_X} className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveTab('help')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'help'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Help & Usage
          </button>
          <button
            onClick={() => setActiveTab('about')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'about'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            About
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-8rem)] custom-scrollbar">
          {activeTab === 'help' && <HelpContent />}
          {activeTab === 'about' && <AboutContent />}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 flex justify-end">
          <Button onClick={onClose} variant="primary">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

const HelpContent: React.FC = () => (
  <div className="space-y-6 text-sm text-gray-300">
    <section>
      <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
        <Icon path={ICON_INFORMATION_CIRCLE} className="w-5 h-5 text-blue-400 mr-2" />
        Getting Started
      </h3>
      <ol className="space-y-2 list-decimal list-inside">
        <li><strong>Define Your Goal:</strong> Describe your software project in detail on the "New Goal" tab.</li>
        <li><strong>Optional AI Analysis:</strong> Provide a Gemini API key to get intelligent goal analysis.</li>
        <li><strong>Submit & Monitor:</strong> Click "Begin Architectural Process" and switch to the Dashboard tab.</li>
        <li><strong>Track Progress:</strong> Watch real-time updates as AI agents work on your project.</li>
        <li><strong>Review Outputs:</strong> Check the outputs panel for generated code, plans, and deployment links.</li>
      </ol>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3 flex items-center">
        <Icon path={ICON_KEY} className="w-5 h-5 text-yellow-400 mr-2" />
        API Key Setup
      </h3>
      <div className="space-y-2">
        <p><strong>Gemini API Key:</strong></p>
        <ul className="space-y-1 list-disc list-inside ml-4">
          <li>Visit <a href="https://makersuite.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google AI Studio</a></li>
          <li>Create a new API key</li>
          <li>Enter it in the Goal Input panel when prompted</li>
          <li>The key is stored locally in your browser</li>
        </ul>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Understanding the Interface</h3>
      <div className="space-y-3">
        <div>
          <h4 className="font-medium text-gray-200">Dashboard Tab</h4>
          <p className="text-gray-400">Shows current goal status, active AI agents, and their tasks in real-time.</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">Monitoring Tab</h4>
          <p className="text-gray-400">Displays system health, hardware capabilities, and connection status.</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">Config Tab</h4>
          <p className="text-gray-400">Access backend configuration settings and system parameters.</p>
        </div>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Output Types</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-gray-800/50 p-3 rounded border border-gray-700">
          <h4 className="font-medium text-gray-200 mb-1">Log</h4>
          <p className="text-xs text-gray-400">Real-time processing logs and agent communications</p>
        </div>
        <div className="bg-gray-800/50 p-3 rounded border border-gray-700">
          <h4 className="font-medium text-gray-200 mb-1">Plan</h4>
          <p className="text-xs text-gray-400">High-level architectural plans and strategies</p>
        </div>
        <div className="bg-gray-800/50 p-3 rounded border border-gray-700">
          <h4 className="font-medium text-gray-200 mb-1">Code File</h4>
          <p className="text-xs text-gray-400">Generated source code files</p>
        </div>
        <div className="bg-gray-800/50 p-3 rounded border border-gray-700">
          <h4 className="font-medium text-gray-200 mb-1">Cloud Resources</h4>
          <p className="text-xs text-gray-400">GCS URIs, build logs, and deployment URLs</p>
        </div>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Troubleshooting</h3>
      <div className="space-y-2">
        <div>
          <h4 className="font-medium text-gray-200">Connection Issues</h4>
          <p className="text-gray-400">Check the footer status indicator. Red means backend disconnection.</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">No Agent Activity</h4>
          <p className="text-gray-400">Ensure the backend is running on port 8001 and WebSocket connection is active.</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">API Key Issues</h4>
          <p className="text-gray-400">Verify your Gemini API key is valid and has sufficient quota.</p>
        </div>
      </div>
    </section>
  </div>
);

const AboutContent: React.FC = () => (
  <div className="space-y-6 text-sm text-gray-300">
    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Autonomous AI Architect</h3>
      <p className="mb-4">
        A sophisticated AI-powered system that transforms high-level software requirements into 
        complete, deployable applications using advanced multi-agent orchestration.
      </p>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Key Features</h3>
      <ul className="space-y-2 list-disc list-inside">
        <li>Multi-agent AI orchestration using CrewAI framework</li>
        <li>Dynamic LLM routing with caching and circuit breakers</li>
        <li>Secure code execution in gVisor sandboxes</li>
        <li>Real-time WebSocket communication</li>
        <li>Automated GCP deployment pipeline</li>
        <li>Comprehensive monitoring and observability</li>
        <li>Vector-based knowledge management</li>
      </ul>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Architecture</h3>
      <div className="space-y-3">
        <div>
          <h4 className="font-medium text-gray-200">Frontend</h4>
          <p className="text-gray-400">React with TypeScript, real-time updates via WebSockets</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">Backend</h4>
          <p className="text-gray-400">FastAPI with async processing, agent orchestration</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">AI Agents</h4>
          <p className="text-gray-400">Specialized roles: Architect, Builder, QA, Security, DevOps</p>
        </div>
        <div>
          <h4 className="font-medium text-gray-200">Infrastructure</h4>
          <p className="text-gray-400">Docker containers, Terraform IaC, GCP services</p>
        </div>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Technology Stack</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="font-medium text-gray-200 mb-2">Core Technologies</h4>
          <ul className="text-xs text-gray-400 space-y-1">
            <li>• Python 3.11</li>
            <li>• React 18</li>
            <li>• FastAPI</li>
            <li>• CrewAI</li>
            <li>• LangChain</li>
          </ul>
        </div>
        <div>
          <h4 className="font-medium text-gray-200 mb-2">Infrastructure</h4>
          <ul className="text-xs text-gray-400 space-y-1">
            <li>• Docker & gVisor</li>
            <li>• Qdrant Vector DB</li>
            <li>• Redis Caching</li>
            <li>• Prometheus</li>
            <li>• Google Cloud Platform</li>
          </ul>
        </div>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">Version Information</h3>
      <div className="bg-gray-800/50 p-3 rounded border border-gray-700">
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-gray-400">Version:</span> <span className="text-white">1.0.0</span>
          </div>
          <div>
            <span className="text-gray-400">Build:</span> <span className="text-white">Production</span>
          </div>
          <div>
            <span className="text-gray-400">API:</span> <span className="text-white">v1</span>
          </div>
          <div>
            <span className="text-gray-400">Protocol:</span> <span className="text-white">WebSocket + REST</span>
          </div>
        </div>
      </div>
    </section>

    <section>
      <h3 className="text-lg font-semibold text-white mb-3">License & Credits</h3>
      <p className="text-gray-400 mb-2">
        This software is built with open-source technologies and follows industry best practices 
        for security, scalability, and maintainability.
      </p>
      <p className="text-xs text-gray-500">
        © 2024 Autonomous AI Architect. All rights reserved.
      </p>
    </section>
  </div>
);

export default HelpSettingsModal;
