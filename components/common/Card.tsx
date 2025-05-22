
// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/common/Card.tsx
// All development should use /frontend/src/components/common/Card.tsx version.

import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  children: React.ReactNode;
  className?: string;
  titleClassName?: string;
  bodyClassName?: string;
  footer?: React.ReactNode;
  titleIcon?: React.ReactNode;
  accentColor?: 'sapphire' | 'amethyst' | 'ruby' | 'citrine' | 'fuchsia' | 'muted-grey';
}

const Card: React.FC<CardProps> = ({ title, children, className = '', titleClassName = '', bodyClassName = '', footer, titleIcon, accentColor = 'amethyst', ...rest }) => {
  // Fix: Replace tailwind.theme.extend.colors direct access with placeholder hex color values.
  // These should ideally be sourced from a centralized theme configuration aligned with tailwind.config.js.
  const gemColorHexMap: Record<string, string> = {
    sapphire: '#3498db',
    amethyst: '#9b59b6',
    ruby: '#e74c3c',
    citrine: '#f1c40f',
    fuchsia: '#d33682',
    'muted-grey': '#95a5a6', 
  };
  const accentColorHex = gemColorHexMap[accentColor] || gemColorHexMap.amethyst;

  return (
    <div 
      className={`bg-gem-ebony-surface/80 backdrop-blur-sm rounded-xl overflow-hidden animate-fade-in transition-all duration-300 group relative shadow-xl hover:shadow-gem-radiant kaleidoscope-bg ${className} iridescent-border`}
      style={{
        '--gem-glow-color': accentColorHex,
        '--angle': `${Math.random() * 360}deg`, // Random start for border animation
         // @ts-ignore - For kaleidoscope-bg pseudo element
        // Fix: Use the gemColorHexMap for these values.
        '--kal-color1': gemColorHexMap.sapphire + '33',
        '--kal-color2': gemColorHexMap.amethyst + '3A',
        '--kal-color3': gemColorHexMap.fuchsia + '33',
        '--kal-color4': gemColorHexMap.citrine + '33',
        '--kal-color5': gemColorHexMap.ruby + '3A',
      } as React.CSSProperties}
      {...rest}
    >
      <div className="relative z-10"> {/* Content wrapper to sit above kaleidoscope pseudo-element */}
        {title && (
          <div className={`px-5 py-4 border-b border-gem-light-achromatic/10 flex items-center space-x-3 ${titleClassName}`}>
            {titleIcon && <span className={`text-gem-${accentColor} group-hover:text-gem-fuchsia transition-colors`}>{titleIcon}</span>}
            <h3 className="text-xl font-semibold text-gem-light-achromatic">{title}</h3>
          </div>
        )}
        <div className={`p-5 ${bodyClassName}`}>
          {children}
        </div>
        {footer && (
          <div className="px-5 py-4 bg-gem-ebony/50 border-t border-gem-light-achromatic/10">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Card;
