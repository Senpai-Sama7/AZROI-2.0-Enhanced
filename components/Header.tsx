
// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/Header.tsx
// All development should use /frontend/src/components/Header.tsx version.

import React from 'react';
import Icon from './common/Icon';
import { ICON_LIGHT_BULB, ICON_QUESTION_MARK_CIRCLE } from '../constants'; 
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
    { view: ViewMode.HELP_SETTINGS, label: "Help & Settings", iconPath: ICON_QUESTION_MARK_CIRCLE },
  ];
  
  return (
    <header className="bg-gem-ebony/70 backdrop-blur-md shadow-xl sticky top-0 z-40 border-b border-gem-light-achromatic/10">
      <div className="container mx-auto flex justify-between items-center h-20 px-4 sm:px-6 lg:px-8">
        <div className="flex items-center space-x-3 cursor-pointer group" onClick={() => onNavigate(ViewMode.GOAL_INPUT)}>
          {/* Pulsing gem-like icon */}
          <div className="relative">
            <Icon path={ICON_LIGHT_BULB} className="w-9 h-9 text-gem-amethyst transition-colors duration-300 group-hover:text-gem-fuchsia" />
            <span className="absolute inset-0 rounded-full animate-pulse-subtle bg-gem-amethyst/30 group-hover:bg-gem-fuchsia/40 -z-10"></span>
          </div>
          <h1 className="text-2xl font-extrabold text-gem-light-achromatic uppercase tracking-wider text-stroke-varied group-hover:iridescent-text transition-all duration-300">
            AI Architect
          </h1>
        </div>
        <nav className="flex items-center space-x-0.5 sm:space-x-1">
          {navItems.map(item => (
            <button
              key={item.view}
              onClick={() => onNavigate(item.view)}
              className={`px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-all duration-300 ease-in-out flex items-center space-x-1.5 group relative overflow-hidden
                transform hover:scale-105 focus:outline-none focus:shadow-interactive-gem
                ${currentView === item.view 
                  ? 'text-gem-light-achromatic shadow-md iridescent-border' 
                  : 'text-gem-muted-grey hover:text-gem-light-achromatic bg-transparent hover:bg-gem-ebony-surface/50'
                }`}
                style={{
                    // Fix: Replace tailwind.theme.extend.colors direct access with placeholder hex color values.
                    // These should ideally be sourced from a centralized theme configuration aligned with tailwind.config.js.
                    '--gem-focus-color': currentView === item.view ? '#9b59b6' /* amethyst placeholder */ : '#95a5a6' /* muted_grey placeholder */,
                    '--angle': `${Math.random()*360}deg` // For iridescent border
                } as React.CSSProperties}
            >
              <span className={`relative z-10 flex items-center space-x-1.5 
                ${currentView === item.view ? 'mix-blend-screen font-semibold' : ''}
              `}>
                {item.iconPath && <Icon path={item.iconPath} className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${currentView === item.view ? 'text-gem-light-achromatic' : 'text-gem-muted-grey group-hover:text-gem-amethyst transition-colors'}`} />}
                <span>{item.label}</span>
              </span>
              {currentView === item.view && (
                <span className="absolute inset-0 -z-10 animate-iridescent-shift bg-iridescent-gradient bg-[size:300%_300%] opacity-60 group-hover:opacity-80 transition-opacity duration-500"></span>
              )}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Header;
