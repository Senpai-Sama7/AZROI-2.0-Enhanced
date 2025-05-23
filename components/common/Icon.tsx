// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/common/Icon.tsx
// All development should use /frontend/src/components/common/Icon.tsx version.

import React, { memo } from 'react';

interface IconProps {
  path: string;
  className?: string;
  viewBox?: string;
  size?: number;
  title?: string;
  onClick?: () => void;
}

// Optimized Icon component with minimal re-renders
const Icon: React.FC<IconProps> = memo(({
  path,
  className = '',
  viewBox = '0 0 24 24',
  size,
  title,
  onClick
}) => {
  const sizeStyle = size ? { width: `${size}px`, height: `${size}px` } : {};
  const clickProps = onClick ? { 
    onClick, 
    role: 'button', 
    tabIndex: 0,
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    }
  } : {};
  
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={viewBox}
      className={className}
      style={sizeStyle}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={!title}
      {...clickProps}
    >
      {title && <title>{title}</title>}
      <path d={path} />
    </svg>
  );
});

Icon.displayName = 'Icon';

export default Icon;
