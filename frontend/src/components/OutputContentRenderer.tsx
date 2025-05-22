import React from 'react';
import { ArchitectOutput } from '../types';

export const renderOutputContent = (output: ArchitectOutput) => {
  const contentStyle = "text-gray-300 text-xs leading-relaxed";
  
  // Handle URLs with link components
  if (output.url) {
    return (
      <a 
        href={output.url} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="text-pink-400 hover:text-pink-300 hover:underline break-all"
        title={`Open ${output.title || output.type} in new tab`}
      >
        {output.content || output.url}
      </a>
    );
  }
  
  // Handle specific code-related output types
  if (output.type === 'code_file' || output.type === 'dockerfile' || output.type === 'plan') {
    return (
      <pre className={`${contentStyle} whitespace-pre-wrap bg-black/40 p-2 rounded-md overflow-x-auto custom-scrollbar border border-gray-700/50 shadow-inner`}>
        <code>{output.content}</code>
      </pre>
    );
  }
  
  // Handle log entries with appropriate coloring
  let logTextColor = "text-gray-300"; // Default for INFO or unspecified
  if (output.level === 'ERROR') logTextColor = "text-red-400";
  else if (output.level === 'WARNING') logTextColor = "text-yellow-400";
  else if (output.level === 'INFO' && output.sourceAgent && !['System', 'Frontend', 'WebSocket_Connection_Placeholder'].includes(output.sourceAgent)) logTextColor = "text-blue-300";

  // Default output rendering with proper text wrapping for all output types
  return <span className={`${contentStyle} ${logTextColor} whitespace-pre-wrap`}>{output.content}</span>;
};
