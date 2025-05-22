
// DEPRECATED FILE - DO NOT USE
// This file is deprecated. Please use the new version in /frontend/src/components/AnimatedSpaceBackground.tsx
// All development should use /frontend/src/components/AnimatedSpaceBackground.tsx version.

import React, { useEffect, useState, useMemo } from 'react';

const AnimatedSpaceBackground: React.FC = () => {
  const [stars, setStars] = useState<Array<{ top: string; left: string; size: string; delay: string; duration: string }>>([]);
  const [shootingStarKey, setShootingStarKey] = useState(0); // To re-trigger animation

  useEffect(() => {
    const numStars = Math.floor(window.innerWidth / 20); // Adjust density based on width
    const newStars = Array.from({ length: numStars }).map(() => ({
      top: `${Math.random() * 100}%`,
      left: `${Math.random() * 100}%`,
      size: `${Math.random() * 2 + 0.5}px`, // 0.5px to 2.5px
      delay: `${Math.random() * 5}s`,
      duration: `${Math.random() * 3 + 3}s`, // 3s to 6s twinkle
    }));
    setStars(newStars);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setShootingStarKey(prevKey => prevKey + 1);
    }, Math.random() * 10000 + 8000); // Randomly between 8-18 seconds
    return () => clearInterval(interval);
  }, []);
  
  const ShootingStar = useMemo(() => {
    const topStart = `${Math.random() * 40 - 10}%`; // Start higher up
    const leftStart = `${Math.random() * 100 + 50}%`; // Start more to the right, off-screen
    const angle = Math.random() * 20 + 200; // Angle between 200-220 degrees (falling left-down)
    const duration = `${Math.random() * 2 + 1.5}s`; // 1.5s to 3.5s duration

    return (
        <div
            key={shootingStarKey}
            className="absolute w-20 h-px bg-gradient-to-r from-gem-light-achromatic/80 to-transparent opacity-0"
            style={{
                top: topStart,
                left: leftStart,
                transform: `rotate(${angle}deg)`,
                animation: `shootingStarFall ${duration} ease-in-out forwards`,
                animationDelay: `${Math.random() * 2}s`, // Random start delay
            }}
        >
            <style>{`
                @keyframes shootingStarFall {
                    0% { opacity: 0; transform: translateX(0) translateY(0) scaleX(0.3) rotate(${angle}deg); }
                    20% { opacity: 1; transform: translateX(-40vw) translateY(25vh) scaleX(1) rotate(${angle}deg); }
                    100% { opacity: 0; transform: translateX(-100vw) translateY(60vh) scaleX(0.1) rotate(${angle}deg); }
                }
            `}</style>
        </div>
    );
  }, [shootingStarKey]);


  return (
    <div className="fixed inset-0 -z-50 overflow-hidden bg-gem-ebony">
      {/* Stars */}
      {stars.map((star, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-gem-light-achromatic/70 animate-star-twinkle"
          style={{
            top: star.top,
            left: star.left,
            width: star.size,
            height: star.size,
            animationDelay: star.delay,
            animationDuration: star.duration,
          }}
        />
      ))}

      {/* Nebulae (subtle) */}
      {/* Fix: Replace tailwind.theme.extend.colors direct access with placeholder hex color values (including alpha).
          These should ideally be sourced from a centralized theme configuration aligned with tailwind.config.js.
          Placeholder colors used: sapphire (#3498db), amethyst (#9b59b6), fuchsia (#d33682) */}
      <div 
        className="absolute inset-0 opacity-15" // Very subtle
        style={{
          backgroundImage: `
            radial-gradient(ellipse at 20% 30%, #3498db20 0%, transparent 70%),
            radial-gradient(ellipse at 80% 70%, #9b59b625 0%, transparent 70%),
            radial-gradient(ellipse at 50% 50%, #d3368215 0%, transparent 60%)
          `,
          filter: 'blur(60px)', // Increased blur
          animation: 'subtleDrift 60s linear infinite alternate',
        }}
      >
        <style>{`
          @keyframes subtleDrift {
            0% { transform: translate(0,0) rotate(0deg); }
            100% { transform: translate(20px, 10px) rotate(5deg); }
          }
        `}</style>
      </div>
      
      {ShootingStar}
    </div>
  );
};

export default AnimatedSpaceBackground;
