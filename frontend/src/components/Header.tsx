import React from 'react';
import Icon from './common/Icon';
import { ICON_LIGHT_BULB, ICON_QUESTION_MARK_CIRCLE } from '../constants';

interface HeaderProps {
  onHelpClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onHelpClick }) => {
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
        onClick={onHelpClick}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800/50 hover:bg-gray-700/60 rounded text-sm text-gray-300 hover:text-white border border-gray-700/60 transition"
        aria-label="Help and settings"
      >
        <Icon path={ICON_QUESTION_MARK_CIRCLE} className="w-4 h-4" />
        <span>Help & Settings</span>
      </button>
    </header>
  );
};

export default Header;
