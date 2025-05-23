import React from 'react';

interface CardProps {
  title?: string;
  titleIcon?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  headerClassName?: string;
  onClick?: () => void;
  hoverable?: boolean;
}

const Card: React.FC<CardProps> = ({
  title,
  titleIcon,
  children,
  className = '',
  bodyClassName = '',
  headerClassName = '',
  onClick,
  hoverable = false
}) => {
  const baseClasses = 'bg-gray-800/60 backdrop-blur-sm border border-gray-700/60 rounded-lg shadow-lg';
  const hoverClasses = hoverable ? 'hover:border-gray-600/70 hover:shadow-xl transition-all duration-200' : '';
  const clickableClasses = onClick ? 'cursor-pointer' : '';

  return (
    <div 
      className={`${baseClasses} ${hoverClasses} ${clickableClasses} ${className}`}
      onClick={onClick}
    >
      {title && (
        <div className={`px-4 py-3 border-b border-gray-700/50 ${headerClassName}`}>
          <h3 className="text-lg font-semibold text-white flex items-center">
            {titleIcon && <span className="mr-2">{titleIcon}</span>}
            {title}
          </h3>
        </div>
      )}
      <div className={`p-4 ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
};

export default Card;
