import React from 'react';
// Icon component is not explicitly used here, but could be if nav items had icons.
// ICON_LIGHT_BULB, ICON_QUESTION_MARK_CIRCLE are removed as they are not used in the new header design
import { ViewMode } from '../types';

interface HeaderProps {
  currentView: ViewMode;
  onNavigate: (view: ViewMode) => void;
}

const Header: React.FC<HeaderProps> = ({ currentView, onNavigate }) => {
  const navItems = [
    { view: ViewMode.GOAL_INPUT, label: "Architect" },
    { view: ViewMode.DASHBOARD, label: "Dashboard" },
    { view: ViewMode.MONITORING, label: "Monitor" },
    { view: ViewMode.CONFIG, label: "Configure" },
    // Help & Settings is removed from header nav, handled by footer button in App.tsx
  ];
  
  return (
    <header className="fixed top-0 left-0 right-0 p-3 md:p-4 z-40 bg-black/50 backdrop-blur-md border-b border-gray-700/60 shadow-lg">
      <div className="container mx-auto flex justify-between items-center max-w-screen-xl px-2 sm:px-0">
        {/* Logo with Playfair Display font and simple SVG */}
        <div 
            className="flex items-center space-x-2 sm:space-x-2.5 cursor-pointer group" 
            onClick={() => onNavigate(ViewMode.GOAL_INPUT)}
            aria-label="Go to Architect Home"
            role="button"
            tabIndex={0}
            onKeyPress={(e) => e.key === 'Enter' && onNavigate(ViewMode.GOAL_INPUT)}
        >
            {/* Simple SVG icon as part of logo placeholder */}
            <div className="w-6 h-6 sm:w-7 sm:h-7 bg-gray-700/40 rounded-full flex items-center justify-center border border-gray-600/70 group-hover:border-pink-500/70 transition-colors duration-200">
                {/* Placeholder Gem/Diamond Icon Path (simplified) */}
                <svg className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-gray-300 group-hover:text-pink-400 transition-colors duration-200" fill="currentColor" viewBox="0 0 20 20"><path d="M10 3.5a1.5 1.5 0 011.371.848l6.858 11.232A1.5 1.5 0 0117.27 18H2.73a1.5 1.5 0 01-.959-2.42l6.858-11.232A1.5 1.5 0 0110 3.5zm0 2.125L4.43 16.5h11.14L10 5.625z"></path></svg>
            </div>
            <h1 className="text-lg sm:text-xl font-playfair font-bold text-gray-100 group-hover:text-pink-300 transition-colors duration-200 text-stroke-varied">
                AI Architect
            </h1>
        </div>

        {/* Navigation */}
        <nav className="flex items-center space-x-0.5 sm:space-x-1.5">
          {navItems.map(item => (
            <button
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`px-2.5 py-1.5 sm:px-3 sm:py-1.5 rounded-md text-xs sm:text-sm font-medium transition-colors duration-200
                focus:outline-none focus:ring-2 focus:ring-pink-500/70 focus:ring-offset-2 focus:ring-offset-black/60
                ${currentView === item.view 
                  ? 'text-white bg-gray-700/50 shadow-sm' // Active state
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-700/30' // Inactive state
                }`}
              aria-current={currentView === item.view ? 'page' : undefined}
            >
              {item.label}
            </button>
          ))}
          {/* The prominent pink "Help & Info" button is now in the footer (App.tsx) */}
        </nav>
      </div>
    </header>
  );
};

export default Header;
