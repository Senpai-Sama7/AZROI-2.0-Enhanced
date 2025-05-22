// WebSocket message batching utility to improve performance with high message volumes
import React, { useState, useEffect, useRef } from 'react';
import { ArchitectOutput, Agent } from '../types';

// Helper to debounce state updates for massive message volumes
export function useBatchedUpdates<T>(
  initialState: T[],
  batchTimeMs: number = 100 // Default batch window (adjust based on expected message frequency)
): [T[], React.Dispatch<React.SetStateAction<T[]>>, (items: T[]) => void] {
  const [state, setState] = useState<T[]>(initialState);
  const batchQueueRef = useRef<T[]>([]);
  const timeoutRef = useRef<number | null>(null);

  // Function to add items to batch queue
  const addToBatch = (items: T[]) => {
    batchQueueRef.current = [...batchQueueRef.current, ...items];
    
    if (timeoutRef.current === null) {
      timeoutRef.current = window.setTimeout(() => {
        setState(prev => [...prev, ...batchQueueRef.current]);
        batchQueueRef.current = [];
        timeoutRef.current = null;
      }, batchTimeMs);
    }
  };

  // Clean up any pending timeouts
  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [state, setState, addToBatch];
}

// Helper for optimized agent updates that avoids redundant re-renders
export function useOptimizedAgentUpdates(
  initialAgents: Agent[] = []
): [Agent[], (agent: Agent) => void, React.Dispatch<React.SetStateAction<Agent[]>>] {
  const [agents, setAgents] = useState<Agent[]>(initialAgents);
  
  // Update a single agent efficiently
  const updateAgent = (updatedAgent: Agent) => {
    setAgents(prevAgents => {
      const existingAgentIndex = prevAgents.findIndex(
        a => a.id === updatedAgent.id || a.name === updatedAgent.name
      );
      
      if (existingAgentIndex !== -1) {
        // Only update if something actually changed
        const currentAgent = prevAgents[existingAgentIndex];
        const hasChanges = Object.keys(updatedAgent).some(
          key => updatedAgent[key as keyof Agent] !== currentAgent[key as keyof Agent]
        );
        
        if (!hasChanges) return prevAgents; // Skip update if nothing changed
        
        const updatedAgents = [...prevAgents];
        updatedAgents[existingAgentIndex] = { ...currentAgent, ...updatedAgent };
        return updatedAgents;
      }
      
      return [...prevAgents, updatedAgent];
    });
  };
  
  return [agents, updateAgent, setAgents];
}
