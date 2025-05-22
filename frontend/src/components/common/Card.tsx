import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  children: React.ReactNode;
  className?: string;
  titleClassName?: string;
  bodyClassName?: string;
  footer?: React.ReactNode;
  titleIcon?: React.ReactNode;
  // accentColor and other complex styling props like kaleidoscope, iridescent-border are removed for the new theme
}

const Card: React.FC<CardProps> = ({ 
    title, 
    children, 
    className = '', 
    titleClassName = '', 
    bodyClassName = '', 
    footer, 
    titleIcon, 
    ...rest 
}) => {
  // New theme card styling: glassy background effect with blur
  const cardBaseClasses = "bg-gray-900/60 backdrop-blur-md rounded-lg overflow-hidden shadow-xl border border-gray-800/50";
  
  // Standard icon size for card titles - use a sensible default like w-5 h-5 or text-lg if it's a font icon
  // If titleIcon is an <Icon> component, it should ideally take its own size prop or inherit.
  // For now, let's assume Icon component handles its own default size or respects text size.
  const iconWrapperClass = "text-gray-300 mr-2"; // For the span wrapping the icon

  return (
    <div 
      className={`${cardBaseClasses} animate-fade-in transition-all duration-300 ${className}`}
      {...rest}
    >
      <div className="relative z-10"> {/* Content wrapper */}
        {title && (
          <div className={`px-4 py-3 border-b border-gray-700/60 flex items-center ${titleClassName}`}>
            {titleIcon && <span className={iconWrapperClass}>{titleIcon}</span>}
            <h3 className="text-base font-semibold text-gray-100">{title}</h3> {/* text-base or text-md */}
          </div>
        )}
        <div className={`p-4 ${bodyClassName}`}> {/* Standardized padding */}
          {children}
        </div>
        {footer && (
          <div className="px-4 py-3 bg-black/20 border-t border-gray-700/60"> {/* Slightly darker footer bg */}
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Card;
