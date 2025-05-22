import React, { useEffect, useState, useMemo } from 'react';
import './styles/starry-background.css';

// Modern version of the space background that uses the starry background CSS class
const StarryBackground: React.FC = () => {
  const [shootingStarKey, setShootingStarKey] = useState(0); // For re-triggering shooting star animation

  useEffect(() => {
    // Show a new shooting star every 8-20 seconds
    const interval = setInterval(() => {
      setShootingStarKey((prevKey: number) => prevKey + 1);
    }, Math.random() * 12000 + 8000);
    
    return () => clearInterval(interval);
  }, []);
  
  const ShootingStar = useMemo(() => {
    const topStart = `${Math.random() * 50}%`;
    const leftStart = `${Math.random() * 100}%`;
    const angle = Math.random() * 45 + 15; // 15-60 degrees
    const duration = `${Math.random() * 1.5 + 1}s`;

    return (
      <div
        key={shootingStarKey}
        className="absolute w-16 h-px bg-gradient-to-r from-white to-transparent opacity-0 animate-shooting-star-fall"
        style={{
          top: topStart,
          left: leftStart,
          '--shooting-star-duration': duration,
          '--shooting-star-delay': `${Math.random() * 0.5}s`,
          '--shooting-star-angle': `${angle}deg`,
        } as React.CSSProperties}
      />
    );
  }, [shootingStarKey]);

  return (
    <div className="fixed inset-0 -z-50 overflow-hidden starry-background" aria-hidden="true">
      {/* The starry background with stars and nebulae is defined in the CSS class */}
      
      {/* Additional animated elements */}
      <div 
        className="absolute inset-0 opacity-10 animate-subtle-drift" 
        style={{
          backgroundImage: `
            radial-gradient(ellipse at 20% 30%, rgba(219, 39, 119, 0.15) 0%, transparent 70%), /* Pink */
            radial-gradient(ellipse at 70% 65%, rgba(167, 139, 250, 0.12) 0%, transparent 70%) /* Purple */
          `,
          filter: 'blur(60px)',
        }}
      />
      
      {ShootingStar}
    </div>
  );
};

export default StarryBackground;
