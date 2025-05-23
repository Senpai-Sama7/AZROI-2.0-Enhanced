import React from 'react';
import { ArchitectOutput } from '../types';
import Icon from './common/Icon';
import { ICON_LINK_EXTERNAL, ICON_CODE } from '../constants';

export const renderOutputContent = (output: ArchitectOutput) => {
  const contentStyle = "text-gray-300 text-xs leading-relaxed";
  
  // Handle URLs with link components
  if (output.url) {
    return (
      <a 
        href={output.url} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="text-pink-400 hover:text-pink-300 hover:underline break-all flex items-center"
        title={`Open ${output.title || output.type} in new tab`}
      >
        <span className="mr-1">{output.content || output.url}</span>
        <Icon path={ICON_LINK_EXTERNAL} className="w-3 h-3 inline-block flex-shrink-0" />
      </a>
    );
  }
  
  // Handle specific code-related output types
  if (output.type === 'code_file' || output.type === 'dockerfile' || output.type === 'plan') {
    return (
      <div className="relative">
        <div className="absolute right-1 top-1 z-10">
          <button 
            onClick={() => {
              navigator.clipboard.writeText(output.content || '');
            }}
            className="p-1 bg-gray-800/60 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
            title="Copy to clipboard"
            aria-label="Copy code to clipboard"
          >
            <Icon path={ICON_CODE} className="w-3 h-3" />
          </button>
        </div>
        <pre className={`${contentStyle} whitespace-pre-wrap bg-black/40 p-2 rounded-md overflow-x-auto custom-scrollbar border border-gray-700/50 shadow-inner`}>
          <code>{output.content}</code>
        </pre>
      </div>
    );
  }
  
  // Handle log entries with appropriate coloring
  let logTextColor = "text-gray-300"; // Default for INFO or unspecified
  if (output.level === 'ERROR') logTextColor = "text-red-400";
  else if (output.level === 'WARNING') logTextColor = "text-yellow-400";
  else if (output.level === 'INFO' && output.sourceAgent && !['System', 'Frontend', 'WebSocket_Connection_Placeholder'].includes(output.sourceAgent)) logTextColor = "text-blue-300";

  // Default output rendering with proper text wrapping for all output types
  return <span className={`${contentStyle} ${logTextColor} whitespace-pre-wrap break-words overflow-wrap-anywhere`}>{output.content}</span>;
};
