import React, { useState, useCallback } from 'react';
import Button from './common/Button';
import Card from './common/Card';
import LoadingSpinner from './common/LoadingSpinner';
import Icon from './common/Icon';
import { ICON_ARROW_PATH, ICON_INFORMATION_CIRCLE, ICON_EXCLAMATION_TRIANGLE, ICON_LIGHT_BULB } from '../constants';
import { analyzeGoalWithGemini } from '../services/geminiService';
import type { ArchitectGoal } from '../types';

interface GoalInputPanelProps {
  onGoalSubmit: (goalText: string, analysis?: string) => void;
  currentGoal?: ArchitectGoal | null;
}

const GoalInputPanel: React.FC<GoalInputPanelProps> = ({ onGoalSubmit, currentGoal }) => {
  const [goalText, setGoalText] = useState<string>(currentGoal?.text || '');
  const [analysis, setAnalysis] = useState<string | null>(currentGoal?.analysis || null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  
  // Check if backend is actively processing (not just pending, error, or completed frontend states)
  const isProcessingBackend = currentGoal?.status &&
                              currentGoal.status !== 'pending' &&
                              currentGoal.status !== 'analyzing' && // client-side analysis in progress
                              currentGoal.status !== 'completed' &&
                              currentGoal.status !== 'error';

  const handleAnalyzeGoal = useCallback(async () => {
    if (!goalText.trim()) {
      setAnalysisError("Please articulate your vision before analysis.");
      return;
    }
    setIsLoadingAnalysis(true);
    setAnalysisError(null);
    setAnalysis(null);
    try {
      const result = await analyzeGoalWithGemini(goalText);
      // The service now returns error messages as strings, so check for that.
      if (result && (result.toLowerCase().includes("error analyzing goal:") || result.toLowerCase().includes("gemini api is not configured") || result.toLowerCase().includes("api key"))) {
        setAnalysisError(result);
        setAnalysis(null);
      } else {
        setAnalysis(result);
      }
    } catch (error) { // Fallback for unexpected errors from the service
      console.error("Client-side Gemini analysis error:", error);
      const message = error instanceof Error ? error.message : "Failed to analyze goal with AI (client-side).";
      setAnalysisError(message);
      setAnalysis(null);
    } finally {
      setIsLoadingAnalysis(false);
    }
  }, [goalText]);

  const handleSubmitGoalToBackend = () => {
    if (!goalText.trim()) {
      setAnalysisError("A clearly defined goal is the first step to architectural brilliance. Please enter your vision."); 
      return;
    }
    if (analysisError && analysisError.includes("A clearly defined goal")) setAnalysisError(null);
    
    onGoalSubmit(goalText, analysis || undefined);
  };
  
  // A goal "session" is active if it's being processed by the backend.
  const isGoalSessionActive = isProcessingBackend || (currentGoal && (currentGoal.status === 'completed' || currentGoal.status === 'error'));


  return (
    <Card 
      title="Architectural Vision Input" 
      className="w-full animate-slide-up glass-panel" 
      titleIcon={<Icon path={ICON_LIGHT_BULB} className="w-5 h-5 text-pink-500" />}
    >
      <div className="space-y-4">
        <textarea
          value={goalText}
          onChange={(e) => setGoalText(e.target.value)}
          placeholder="Describe the high-level objective for the Autonomous AI Architect... (e.g., 'Create a Python FastAPI application with a /hello endpoint that returns 'world'. Dockerize it and deploy to Google Cloud Run.')"
          className="w-full h-32 p-3 form-input-themed resize-y text-sm custom-scrollbar bg-gray-900/60 border border-gray-700 rounded-md" 
          disabled={isLoadingAnalysis || isProcessingBackend}
          aria-label="Architectural Goal Input"
          aria-describedby="goal-feedback"
          rows={5}
        />
        <div className="flex flex-col sm:flex-row sm:justify-end sm:items-center space-y-2 sm:space-y-0 sm:space-x-3">
          <Button 
            onClick={handleAnalyzeGoal} 
            isLoading={isLoadingAnalysis} 
            disabled={!goalText.trim() || isProcessingBackend}
            variant="outline" 
            size="md"
            leftIcon={<Icon path={ICON_ARROW_PATH} />}
          >
            Analyze (Client-Side)
          </Button>
          <Button 
            onClick={handleSubmitGoalToBackend} 
            isLoading={isProcessingBackend && (!currentGoal?.processingError)}
            disabled={!goalText.trim() || isLoadingAnalysis || isProcessingBackend}
            variant="primary" 
            size="md"
            className="pink-glow"
          >
            {isProcessingBackend ? "Processing Vision..." : "Set Vision"}
          </Button>
        </div>

        <div id="goal-feedback" className="space-y-3 text-xs">
          {analysisError && (
            <div className="p-2.5 bg-red-700/20 border border-red-600/40 rounded-md text-red-300 flex items-start space-x-1.5 animate-fade-in shadow-sm">
              <Icon path={ICON_EXCLAMATION_TRIANGLE} className="w-3.5 h-3.5 flex-shrink-0 text-red-400 mt-px" />
              <div>
                  <h5 className="font-semibold">Analysis Note</h5>
                  <p>{analysisError}</p>
              </div>
            </div>
          )}

          {isLoadingAnalysis && <LoadingSpinner text="Gemini analyzing (client-side)..." className="mt-2" variant="pink" size="sm"/>}
          
          {analysis && !isLoadingAnalysis && !analysisError && (
            <Card 
              title="Client-Side AI Insights" 
              className="mt-2"
              titleIcon={<Icon path={ICON_INFORMATION_CIRCLE} className="w-4 h-4 text-blue-400" />}
              bodyClassName="!p-0" // Remove default body padding
            >
              <div className="text-gray-300 whitespace-pre-wrap leading-relaxed custom-scrollbar max-h-24 overflow-y-auto text-xs p-2.5 bg-black/20 rounded-b-md">
                {analysis}
              </div>
            </Card>
          )}
          {isGoalSessionActive && !isProcessingBackend && ( // If goal had an error or completed
            <div className={`p-2.5 rounded-md flex items-start space-x-1.5 animate-fade-in shadow-sm
              ${currentGoal?.status === 'error' ? 'bg-red-700/20 border border-red-600/40 text-red-300' : 'bg-green-700/20 border border-green-600/40 text-green-300'}
            `}>
              <Icon path={currentGoal?.status === 'error' ? ICON_EXCLAMATION_TRIANGLE : ICON_INFORMATION_CIRCLE} className={`w-3.5 h-3.5 flex-shrink-0 mt-px ${currentGoal?.status === 'error' ? 'text-red-400' : 'text-green-400'}`} />
              <div>
                  <h5 className="font-semibold">Vision Concluded</h5>
                  <p>The Architect has processed the vision. Status: <span className="font-bold">{currentGoal?.status.toUpperCase()}</span>.</p>
                  {currentGoal?.processingError && <p className="mt-0.5">Details: {currentGoal.processingError}</p>}
                   <p className="mt-1">You can now submit a new vision.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export default GoalInputPanel;
