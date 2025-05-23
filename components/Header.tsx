import React, { memo, useCallback } from 'react';
import Icon from './common/Icon';

// Icon constants for performance (avoid re-creating objects)
const ICON_LIGHT_BULB = "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z";
const ICON_QUESTION_MARK_CIRCLE = "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z";

interface HeaderProps {
  onHelpClick: () => void;
}

// Performance-optimized Header component
const Header: React.FC<HeaderProps> = memo(({ onHelpClick }) => {
  // Memoize click handler to prevent child re-renders
  const handleHelpClick = useCallback(() => {
    onHelpClick();
  }, [onHelpClick]);

  return (
    <header className="flex justify-between items-center">
      <div className="flex items-center">
        <Icon path={ICON_LIGHT_BULB} className="w-7 h-7 text-yellow-400 mr-3" />
        <div>
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600">
            Autonomous AI Architect
          </h1>
          <p className="text-gray-400 text-sm">Architect, generate, and deploy complex software from high-level goals</p>
        </div>
      </div>
      
      <button 
        onClick={handleHelpClick}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800/50 hover:bg-gray-700/60 rounded text-sm text-gray-300 hover:text-white border border-gray-700/60 transition-colors duration-150"
        aria-label="Help and settings"
      >
        <Icon path={ICON_QUESTION_MARK_CIRCLE} className="w-4 h-4" />
        <span>Help & Settings</span>
      </button>
    </header>
  );
});

Header.displayName = 'Header';

export default Header;
