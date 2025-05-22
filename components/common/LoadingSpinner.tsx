// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/common/LoadingSpinner.tsx
// All development should use /frontend/src/components/common/LoadingSpinner.tsx version.

import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
  variant?: 'amethyst' | 'sapphire' | 'citrine'; // Updated variants to gem names
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', text, className, variant = 'amethyst' }) => {
  const sizeClasses = {
    sm: 'w-5 h-5 border-2',
    md: 'w-8 h-8 border-[3px]',
    lg: 'w-12 h-12 border-4',
  };

  const colorClasses = {
    amethyst: 'border-gem-amethyst',
    sapphire: 'border-gem-sapphire',
    citrine: 'border-gem-citrine',
  }

  const textColorClasses = {
    amethyst: 'text-gem-amethyst',
    sapphire: 'text-gem-sapphire',
    citrine: 'text-gem-citrine',
  }

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div
        className={`animate-spin rounded-full ${colorClasses[variant]} border-t-transparent ${sizeClasses[size]}`}
      ></div>
      {text && <p className={`mt-3 text-sm ${textColorClasses[variant]} font-medium`}>{text}</p>}
    </div>
  );
};

export default LoadingSpinner;