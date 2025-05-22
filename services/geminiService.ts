
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
      // console.log("Using API Key from localStorage.");
    }
  }

  // 2. If not found in localStorage, try URL parameter "apiKey"
  if (!apiKeyToUse && typeof window !== 'undefined' && window.location && window.location.search) {
    const params = new URLSearchParams(window.location.search);
    const apiKeyFromUrl = params.get('apiKey');
    if (apiKeyFromUrl) {
      apiKeyToUse = apiKeyFromUrl;
      // console.log("Using API Key from URL parameter.");
      // Optionally store it in localStorage for future use
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(LOCAL_STORAGE_API_KEY, apiKeyFromUrl);
      }
    }
  }
  
  // 3. If not found, try to get from process.env (less likely in direct browser, but for completeness)
  if (!apiKeyToUse && typeof process !== 'undefined' && process.env && process.env.API_KEY) {
    apiKeyToUse = process.env.API_KEY;
    // console.log("Using API Key from process.env.");
  }


  if (!apiKeyToUse) {
    console.warn(
      "Gemini API key not found. Please set it in Help & Settings, or provide it as a URL parameter 'apiKey', or set the API_KEY environment variable. Gemini features will be disabled."
    );
    ai = null;
  } else {
    try {
        ai = new GoogleGenAI({ apiKey: apiKeyToUse });
    } catch (e) {
        console.error("Failed to initialize GoogleGenAI:", e);
        ai = null;
        // If initialization itself fails (e.g. due to malformed key at constructor level, though rare)
        // we might want to clear a potentially bad key from local storage
        if (typeof window !== 'undefined' && window.localStorage) {
            const storedKey = localStorage.getItem(LOCAL_STORAGE_API_KEY);
            if (storedKey === apiKeyToUse) { // only clear if it's the one we just tried
                 localStorage.removeItem(LOCAL_STORAGE_API_KEY);
                 console.warn("Potentially invalid API key removed from localStorage due to initialization error.");
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
    return "Gemini API is not configured. Analysis unavailable. Please set your API key in Help & Settings.";
  }

  try {
    const model = GEMINI_MODEL_NAME;
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
  } catch (error) {
    console.error("Error calling Gemini API:", error);
    if (error instanceof Error) {
        if (error.message.includes('API key not valid') || error.message.includes('permission denied') || error.message.includes('invalid')) {
            return "Error analyzing goal: The provided Gemini API key is not valid or lacks permissions. Please check your API_KEY in Help & Settings.";
        }
        if (error.message.includes('quota')) {
            return "Error analyzing goal: Gemini API quota exceeded. Please check your usage or billing.";
        }
        return `Error analyzing goal with Gemini: ${error.message}`;
    }
    return "An unknown error occurred while analyzing the goal with Gemini.";
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
    console.error("API Key construction error:", e.message);
    return { valid: false, message: `API Key is malformed or invalid at initialization: ${e.message}` };
  }

  try {
    // A lightweight call, like generating a very short, simple text.
    // The specific model 'gemini-2.5-flash-preview-04-17' should be used for checks.
    const response = await tempAiClient.models.generateContent({
        model: GEMINI_MODEL_NAME, 
        contents: "Hello",
        config: { thinkingConfig: { thinkingBudget: 0 } } // Disable thinking for faster, cheaper check
    });

    if (response && response.text) { // Check if response and response.text are not null/undefined
      return { valid: true, message: "API Key is valid and working." };
    } else {
      // This case might indicate an issue not caught by an error, e.g. empty response
      return { valid: false, message: "API Key seems valid but returned an empty response. Check model access."};
    }
  } catch (error: any) {
    console.error("Error during API key validation call:", error);
    if (error.message.includes('API key not valid') || error.message.includes('permission denied') || error.message.includes('invalid')) {
      return { valid: false, message: "API Key is not valid or lacks permissions." };
    }
    if (error.message.includes('quota')) {
      return { valid: false, message: "API Key is valid, but quota has been exceeded." };
    }
    return { valid: false, message: `API Key validation failed: ${error.message}` };
  }
};
