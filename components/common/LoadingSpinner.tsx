import React, { memo, useMemo } from 'react';

interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  color?: string;
  text?: string;
  className?: string;
  reduceMotion?: boolean; // Option to respect prefers-reduced-motion
}

// Power-efficient loading spinner with reduced motion support
const LoadingSpinner: React.FC<LoadingSpinnerProps> = memo(({
  size = 'md',
  color = 'text-white',
  text,
  className = '',
  reduceMotion = false
}) => {
  const { sizeClass, textSizeClass } = useMemo(() => {
    const sizeMap = {
      xs: 'w-3 h-3',
      sm: 'w-4 h-4',
      md: 'w-6 h-6',
      lg: 'w-8 h-8'
    };

    const textSizeMap = {
      xs: 'text-xs',
      sm: 'text-sm',
      md: 'text-sm',
      lg: 'text-base'
    };

    return {
      sizeClass: sizeMap[size],
      textSizeClass: textSizeMap[size]
    };
  }, [size]);

  // Use CSS animation class that respects prefers-reduced-motion
  const animationClass = reduceMotion ? '' : 'animate-spin';

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <svg
        className={`${animationClass} ${sizeClass} ${color} ${text ? 'mr-2' : ''}`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      {text && <span className={`${textSizeClass} font-medium`}>{text}</span>}
    </div>
  );
});

LoadingSpinner.displayName = 'LoadingSpinner';

export default LoadingSpinner;