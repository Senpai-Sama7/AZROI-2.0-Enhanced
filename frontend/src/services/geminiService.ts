import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { GEMINI_MODEL_NAME, LOCAL_STORAGE_API_KEY } from '../constants';

let ai: GoogleGenAI | null = null;

const initializeAiClient = () => {
  let apiKeyToUse: string | undefined = undefined;

  // 1. Try to get API key from localStorage
  if (typeof window !== 'undefined' && window.localStorage) {
    const storedKey = localStorage.getItem(LOCAL_STORAGE_API_KEY);
    if (storedKey) {
      apiKeyToUse = storedKey;
      // console.log("Using API Key from localStorage for frontend analysis.");
    }
  }

  // 2. If not found in localStorage, try URL parameter "apiKey"
  if (!apiKeyToUse && typeof window !== 'undefined' && window.location && window.location.search) {
    const params = new URLSearchParams(window.location.search);
    const apiKeyFromUrl = params.get('apiKey');
    if (apiKeyFromUrl) {
      apiKeyToUse = apiKeyFromUrl;
      // console.log("Using API Key from URL parameter for frontend analysis.");
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(LOCAL_STORAGE_API_KEY, apiKeyFromUrl);
      }
    }
  }
  
  // 3. If not found, try to get from process.env (less likely in direct browser, but for completeness for bundlers)
  // This process.env.API_KEY refers to a potential client-side build-time variable, NOT the backend's process.env.API_KEY.
  if (!apiKeyToUse && typeof process !== 'undefined' && process.env && process.env.API_KEY) {
    apiKeyToUse = process.env.API_KEY; // This would be process.env.REACT_APP_GEMINI_API_KEY or similar if using CRA/Vite with .env files
    // console.log("Using API Key from process.env for frontend analysis.");
  }


  if (!apiKeyToUse) {
    console.warn(
      "Client-side Gemini API key not found. Please set it in Help & Settings (Client API Key tab), or provide it as a URL parameter 'apiKey', or ensure the API_KEY environment variable is available to the client bundle. Client-side Gemini analysis features will be disabled."
    );
    ai = null;
  } else {
    try {
        // This initializes the GenAI client for client-side use ONLY.
        ai = new GoogleGenAI({ apiKey: apiKeyToUse });
    } catch (e) {
        console.error("Failed to initialize GoogleGenAI for frontend analysis:", e);
        ai = null;
        if (typeof window !== 'undefined' && window.localStorage) {
            const storedKey = localStorage.getItem(LOCAL_STORAGE_API_KEY);
            if (storedKey === apiKeyToUse) { 
                 localStorage.removeItem(LOCAL_STORAGE_API_KEY);
                 console.warn("Potentially invalid client-side API key removed from localStorage due to frontend Gemini client initialization error.");
            }
        }
    }
  }
};

initializeAiClient(); // Initialize on load

// Call this function if the API key is updated in settings
export const reinitializeGeminiClient = () => {
    initializeAiClient();
};

export const analyzeGoalWithGemini = async (goal: string): Promise<string | null> => {
  if (!ai) {
    return "Client-side Gemini API is not configured. Analysis unavailable. Please set your client-side API key in Help & Settings (Client API Key tab).";
  }

  try {
    const model = GEMINI_MODEL_NAME; // Using the constant from constants.ts (now 'gemini-2.5-flash-preview-04-17')
    const systemInstruction = `You are an AI assistant specialized in analyzing and refining project goals for an Autonomous AI Architect system.
    Your role is to:
    1. Clarify the user's intent.
    2. Identify potential ambiguities or missing information.
    3. Suggest concrete, actionable sub-goals or key considerations.
    4. Frame your analysis in a helpful, constructive tone.
    Keep your response concise and focused, ideally in a few bullet points or short paragraphs.
    The goal is to help the user provide a clearer input to the AI Architect.`;

    const response: GenerateContentResponse = await ai.models.generateContent({
      model: model,
      contents: goal,
      config: {
        systemInstruction: systemInstruction,
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
      }
    });
    
    return response.text;
  } catch (error: any) {
    console.error("Error calling client-side Gemini API for analysis:", error);
    if (error && error.message) { // More robust error checking
        const errorMessage = error.message.toLowerCase();
        if (errorMessage.includes('api key not valid') || errorMessage.includes('permission denied') || errorMessage.includes('invalid api key')) {
            return "Error analyzing goal: The provided client-side Gemini API key is not valid or lacks permissions. Please check your API Key in Help & Settings.";
        }
        if (errorMessage.includes('quota')) {
            return "Error analyzing goal: Client-side Gemini API quota exceeded. Please check your usage or billing.";
        }
        // Specific check for 400 Bad Request which can often mean API key issues not caught by simpler string checks
        if (errorMessage.includes('bad request') || errorMessage.includes('400')) {
             return "Error analyzing goal: Bad request to Gemini API. This might be due to an invalid API key or malformed request. (Client-side)";
        }
        return `Error analyzing goal with client-side Gemini: ${error.message}`; // Return original error message if not specifically handled
    }
    return "An unknown error occurred while analyzing the goal with client-side Gemini.";
  }
};

export const checkApiKeyValidity = async (keyToCheck: string): Promise<{ valid: boolean; message: string }> => {
  if (!keyToCheck.trim()) {
    return { valid: false, message: "API Key cannot be empty." };
  }
  let tempAiClient;
  try {
    tempAiClient = new GoogleGenAI({ apiKey: keyToCheck });
  } catch (e: any) {
    console.error("API Key construction error during validation check:", e.message);
    return { valid: false, message: `Client-side API Key is malformed or invalid at initialization: ${e.message}` };
  }

  try {
    // Using the constant model name for validation.
    const response = await tempAiClient.models.generateContent({
        model: GEMINI_MODEL_NAME, // Ensure this is 'gemini-2.5-flash-preview-04-17'
        contents: "Hello", // Minimal content for validation
        config: { thinkingConfig: { thinkingBudget: 0 } } // Disable thinking for faster, cheaper check
    });

    if (response && response.text) { 
      return { valid: true, message: "Client-side API Key is valid and working." };
    } else {
      // This case might indicate an issue not caught by an error, e.g. empty response
      return { valid: false, message: "Client-side API Key seems valid but returned an empty response. Check model access or permissions."};
    }
  } catch (error: any) {
    console.error("Error during API key validation call:", error);
    if (error && error.message) { // More robust error checking
        const errorMessage = error.message.toLowerCase();
        if (errorMessage.includes('api key not valid') || errorMessage.includes('permission denied') || errorMessage.includes('invalid api key')) {
          return { valid: false, message: "Client-side API Key is not valid or lacks permissions." };
        }
        if (errorMessage.includes('quota')) {
          return { valid: false, message: "Client-side API Key is valid, but quota has been exceeded." };
        }
        // Specific check for 400 Bad Request
        if (errorMessage.includes('bad request') || errorMessage.includes('400')) {
             return { valid: false, message: "API Key validation failed: Bad request to Gemini API. This often indicates an invalid API key."};
        }
        return { valid: false, message: `Client-side API Key validation failed: ${error.message}` }; // Original error message
    }
     return { valid: false, message: "Client-side API Key validation failed with an unknown error." };
  }
};
