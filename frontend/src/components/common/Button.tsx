import React from 'react';
import Icon from './Icon'; // Assuming Icon component is in the same directory or path is correct
import { ICON_ARROW_PATH } from '../../constants'; 

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline' | 'subtle';
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isLoading?: boolean;
  // Glow and iridescent props are removed as they are tied to the old theme
  className?: string; // Allow additional classes to be passed
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  leftIcon,
  rightIcon,
  isLoading = false,
  className = '',
  ...props
}) => {
  const baseStyles = "font-semibold rounded-md focus:outline-none inline-flex items-center justify-center transition-all duration-200 ease-in-out transform active:scale-[0.98] focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800/50";
  
  // New theme styles using Tailwind colors
  const variantStyles = {
    primary: `bg-pink-600 text-white hover:bg-pink-700 shadow-md focus:ring-pink-500`,
    secondary: `bg-gray-300 text-gray-800 hover:bg-gray-400 shadow focus:ring-gray-500`, // Light gray for secondary
    danger: "bg-red-600 text-white hover:bg-red-700 shadow-md focus:ring-red-500",
    ghost: "bg-transparent text-gray-300 hover:text-pink-400 hover:bg-gray-700/40 focus:ring-pink-500", // Ghost for dark backgrounds
    outline: `bg-transparent text-pink-500 border-2 border-pink-500 hover:bg-pink-500 hover:text-white focus:ring-pink-500`,
    subtle: "bg-gray-700/50 text-gray-300 hover:text-white hover:bg-gray-600/60 focus:ring-gray-500", // Subtle dark button
  };

  // Modernized sizes
  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs", // Adjusted for more common small button size
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-2.5 text-base", // Slightly smaller lg
  };

  const disabledStyles = "disabled:opacity-60 disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100 disabled:bg-gray-600/50 disabled:text-gray-400 disabled:border-transparent";
  const loadingIconPath = ICON_ARROW_PATH; 

  // Standard icon size for buttons, adjustable per button size if needed later
  let iconSizeClass = "w-4 h-4"; 
  if (size === 'sm') iconSizeClass = "w-3.5 h-3.5";
  if (size === 'lg') iconSizeClass = "w-5 h-5";


  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${disabledStyles} ${className}`}
      disabled={isLoading || props.disabled}
      {...props}
    >
      <span className="relative z-10 flex items-center justify-center">
        {isLoading && (
          <Icon path={loadingIconPath} className={`animate-spin -ml-0.5 mr-2 ${iconSizeClass}`} />
        )}
        {/* Ensure leftIcon and rightIcon are cloned with the correct className if they are React elements */}
        {leftIcon && !isLoading && <span className="mr-1.5 flex items-center">{React.isValidElement(leftIcon) ? React.cloneElement(leftIcon as React.ReactElement<any>, { className: iconSizeClass}) : leftIcon}</span>}
        {children}
        {rightIcon && !isLoading && <span className="ml-1.5 flex items-center">{React.isValidElement(rightIcon) ? React.cloneElement(rightIcon as React.ReactElement<any>, { className: iconSizeClass}) : rightIcon}</span>}
      </span>
    </button>
  );
};

export default Button;
