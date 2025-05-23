import React, { useState, useEffect, useCallback, memo, useMemo } from 'react';
import Card from './common/Card';
import Button from './common/Button';
import Icon from './common/Icon';
import LoadingSpinner from './common/LoadingSpinner';

// Icon constants
const ICON_LIGHT_BULB = "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z";
const ICON_EXCLAMATION_TRIANGLE = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z";

interface GoalInputPanelProps {
  onSubmit: (goalText: string, aiAnalysis?: string) => void;
  isSubmitting: boolean;
  processingError?: string | null;
}

// Memoized example goals to prevent re-creation
const EXAMPLE_GOALS = [
  "Create a full-stack e-commerce platform with user authentication, product catalog, shopping cart, and payment processing",
  "Build a real-time chat application with multiple rooms, file sharing, and user presence indicators",
  "Develop a task management system with team collaboration, deadlines, and progress tracking",
  "Create a personal finance tracker with expense categorization, budgeting, and reporting dashboards"
];

// Performance-optimized GoalInputPanel with virtual scrolling for large content
const GoalInputPanel: React.FC<GoalInputPanelProps> = memo(({ onSubmit, isSubmitting, processingError }) => {
  const [goalText, setGoalText] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState('');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);

  // Optimized API key loading
  useEffect(() => {
    const savedApiKey = localStorage.getItem('autonomousAIApiKey');
    if (savedApiKey) {
      setApiKey(savedApiKey);
    } else {
      setShowApiKeyInput(true);
    }
  }, []);

  // Memoized API key save effect
  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('autonomousAIApiKey', apiKey);
      setShowApiKeyInput(false);
    }
  }, [apiKey]);

  // Optimized analyze handler with proper error handling
  const handleAnalyze = useCallback(async () => {
    if (!goalText.trim()) {
      setAnalysisError('Please enter a goal description first.');
      return;
    }

    if (!apiKey.trim()) {
      setAnalysisError('Please provide a Gemini API key for AI analysis.');
      setShowApiKeyInput(true);
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setAiAnalysis('');

    try {
      // Dynamically import Google Generative AI to reduce initial bundle size
      const { GoogleGenerativeAI } = await import('@google/generative-ai');
      const genAI = new GoogleGenerativeAI(apiKey);
      const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash-preview-04-17' });

      const prompt = `As an expert software architect and project manager, analyze the following software development goal and provide a comprehensive analysis:

GOAL: "${goalText}"

Please provide:
1. Technical feasibility assessment
2. Key architectural considerations
3. Potential challenges and risks
4. Recommended technology stack
5. Estimated complexity level (1-10)
6. High-level implementation approach

Format your response in a clear, structured manner that would help guide an AI development team.`;

      const result = await model.generateContent(prompt);
      const response = result.response;
      const analysisText = response.text();

      setAiAnalysis(analysisText);
    } catch (error) {
      console.error('AI analysis error:', error);
      let errorMessage = 'Failed to analyze goal with AI.';
      
      if (error instanceof Error) {
        if (error.message.includes('API_KEY_INVALID')) {
          errorMessage = 'Invalid API key. Please check your Gemini API key.';
          setShowApiKeyInput(true);
        } else if (error.message.includes('QUOTA_EXCEEDED')) {
          errorMessage = 'API quota exceeded. Please check your Gemini API usage.';
        } else {
          errorMessage = `AI analysis failed: ${error.message}`;
        }
      }
      
      setAnalysisError(errorMessage);
    } finally {
      setIsAnalyzing(false);
    }
  }, [goalText, apiKey]);

  // Optimized submit handler
  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (goalText.trim() && !isSubmitting) {
      onSubmit(goalText.trim(), aiAnalysis || undefined);
    }
  }, [goalText, isSubmitting, aiAnalysis, onSubmit]);

  // Memoized clear API key handler
  const handleClearApiKey = useCallback(() => {
    setApiKey('');
    localStorage.removeItem('autonomousAIApiKey');
    setShowApiKeyInput(true);
  }, []);

  // Memoized example goal click handler
  const handleExampleClick = useCallback((example: string) => {
    setGoalText(example);
  }, []);

  // Memoized rendered example goals to prevent re-renders
  const renderedExampleGoals = useMemo(() => (
    EXAMPLE_GOALS.map((example, index) => (
      <button
        key={index}
        type="button"
        onClick={() => handleExampleClick(example)}
        className="text-left p-3 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700 rounded text-sm text-gray-300 hover:text-white transition-colors duration-150"
        disabled={isSubmitting}
      >
        {example}
      </button>
    ))
  ), [handleExampleClick, isSubmitting]);

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-slide-up">
      <Card 
        title="Define Your Architectural Vision" 
        titleIcon={<Icon path={ICON_LIGHT_BULB} className="w-5 h-5 text-yellow-400" />}
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* API Key Section */}
          {showApiKeyInput && (
            <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-300 mb-2">Gemini API Key Required</h3>
              <p className="text-xs text-gray-300 mb-3">
                To enable AI-powered goal analysis, please provide your Google Gemini API key. 
                This will be stored locally in your browser.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your Gemini API key..."
                  className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white text-sm focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                />
                <Button 
                  onClick={() => setShowApiKeyInput(false)}
                  variant="outline"
                  size="sm"
                  disabled={!apiKey.trim()}
                >
                  Save
                </Button>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Get your API key from{' '}
                <a 
                  href="https://makersuite.google.com/app/apikey" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:underline"
                >
                  Google AI Studio
                </a>
              </p>
            </div>
          )}

          {/* Goal Input */}
          <div>
            <label htmlFor="goalText" className="block text-sm font-medium text-gray-300 mb-2">
              Describe your software project goal
            </label>
            <textarea
              id="goalText"
              value={goalText}
              onChange={(e) => setGoalText(e.target.value)}
              placeholder="Enter a detailed description of what you want to build..."
              rows={4}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-pink-500 focus:border-transparent resize-y"
              disabled={isSubmitting}
            />
          </div>

          {/* Example Goals */}
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-2">Example Goals</h4>
            <div className="grid gap-2">
              {renderedExampleGoals}
            </div>
          </div>

          {/* AI Analysis Section */}
          {apiKey && !showApiKeyInput && (
            <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700">
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-sm font-medium text-gray-300">AI Analysis</h4>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={!goalText.trim() || isAnalyzing || isSubmitting}
                    size="sm"
                    variant="outline"
                  >
                    {isAnalyzing ? <LoadingSpinner size="xs" text="Analyzing..." /> : 'Analyze with AI'}
                  </Button>
                  <Button
                    type="button"
                    onClick={handleClearApiKey}
                    size="sm"
                    variant="outline"
                  >
                    Change API Key
                  </Button>
                </div>
              </div>

              {analysisError && (
                <div className="mb-3 p-3 bg-red-900/20 border border-red-700/50 rounded text-red-300 text-sm flex items-start gap-2">
                  <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{analysisError}</span>
                </div>
              )}

              {aiAnalysis && (
                <div className="bg-black/30 rounded p-3 border border-gray-600 max-h-64 overflow-y-auto">
                  <pre className="text-sm text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                    {aiAnalysis}
                  </pre>
                </div>
              )}

              {!aiAnalysis && !analysisError && !isAnalyzing && (
                <p className="text-xs text-gray-400 italic">
                  Click "Analyze with AI" to get intelligent insights about your goal.
                </p>
              )}
            </div>
          )}

          {/* Error Display */}
          {processingError && (
            <div className="p-3 bg-red-900/20 border border-red-700/50 rounded text-red-300 text-sm flex items-start gap-2">
              <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{processingError}</span>
            </div>
          )}

          {/* Submit Button */}
          <div className="flex justify-center">
            <Button
              type="submit"
              disabled={!goalText.trim() || isSubmitting}
              size="lg"
              className="min-w-[200px]"
            >
              {isSubmitting ? (
                <LoadingSpinner size="sm" text="Initiating..." />
              ) : (
                'Begin Architectural Process'
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
});

GoalInputPanel.displayName = 'GoalInputPanel';

export default GoalInputPanel;