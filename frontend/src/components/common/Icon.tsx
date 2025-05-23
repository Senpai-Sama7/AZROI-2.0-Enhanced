import React from 'react';

interface IconProps {
  path: string;
  className?: string;
  viewBox?: string;
  size?: number;
  title?: string;
  onClick?: () => void;
}

const Icon: React.FC<IconProps> = ({
  path,
  className = '',
  viewBox = '0 0 24 24',
  size,
  title,
  onClick
}) => {
  const sizeStyle = size ? { width: `${size}px`, height: `${size}px` } : {};
  const clickProps = onClick ? { onClick, role: 'button', tabIndex: 0 } : {};
  
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
};

export default Icon;