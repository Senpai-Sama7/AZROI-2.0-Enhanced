import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
  variant?: 'pink' | 'blue' | 'gray'; // New theme variants using Tailwind compatible names
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'md', text, className, variant = 'pink' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2', // Slightly smaller sm
    md: 'w-6 h-6 border-[3px]', // Slightly smaller md
    lg: 'w-10 h-10 border-4', // Slightly smaller lg
  };

  // New theme color classes using Tailwind
  const colorClasses = {
    pink: 'border-pink-500',
    blue: 'border-blue-500',
    gray: 'border-gray-400',
  };

  const textColorClasses = {
    pink: 'text-pink-400',
    blue: 'text-blue-400',
    gray: 'text-gray-300',
  };

  return (
    <div className={`flex flex-col items-center justify-center ${className || ''}`}>
      <div
        className={`animate-spin rounded-full ${colorClasses[variant]} border-t-transparent ${sizeClasses[size]}`}
        role="status"
        aria-live="polite"
        aria-label={text ? undefined : "Loading"} // Only label if no text
      ></div>
      {text && <p className={`mt-2 text-xs ${textColorClasses[variant]} font-medium`}>{text}</p>}
    </div>
  );
};

export default LoadingSpinner;
