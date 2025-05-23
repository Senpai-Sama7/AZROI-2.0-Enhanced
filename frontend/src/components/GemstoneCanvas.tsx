import React, { useEffect, useRef, useState } from 'react';

interface Gemstone {
  x: number;
  y: number;
  size: number;
  rotation: number;
  rotationSpeed: number;
  opacity: number;
  color: string;
  pulsePhase: number;
}

interface GemstoneCanvasProps {
  className?: string;
  gemstoneCount?: number;
  animated?: boolean;
}

const GemstoneCanvas: React.FC<GemstoneCanvasProps> = ({
  className = '',
  gemstoneCount = 15,
  animated = true
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gemstonesRef = useRef<Gemstone[]>([]);
  const animationRef = useRef<number>();
  const [isVisible, setIsVisible] = useState(false);

  const gemstoneColors = [
    '#ec4899', // Pink
    '#8b5cf6', // Purple
    '#06b6d4', // Cyan
    '#10b981', // Emerald
    '#f59e0b', // Amber
    '#ef4444', // Red
    '#3b82f6', // Blue
  ];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      
      // Reinitialize gemstones when canvas resizes
      initializeGemstones();
    };

    const initializeGemstones = () => {
      const rect = canvas.getBoundingClientRect();
      gemstonesRef.current = [];

      for (let i = 0; i < gemstoneCount; i++) {
        gemstonesRef.current.push({
          x: Math.random() * rect.width,
          y: Math.random() * rect.height,
          size: Math.random() * 8 + 4,
          rotation: Math.random() * Math.PI * 2,
          rotationSpeed: (Math.random() - 0.5) * 0.02,
          opacity: Math.random() * 0.6 + 0.2,
          color: gemstoneColors[Math.floor(Math.random() * gemstoneColors.length)],
          pulsePhase: Math.random() * Math.PI * 2
        });
      }
    };

    const drawGemstone = (gem: Gemstone) => {
      ctx.save();
      ctx.translate(gem.x, gem.y);
      ctx.rotate(gem.rotation);

      // Calculate pulsing opacity
      const pulseOpacity = gem.opacity * (0.7 + 0.3 * Math.sin(gem.pulsePhase));
      
      // Draw gemstone as a diamond shape with gradient
      const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, gem.size);
      gradient.addColorStop(0, `${gem.color}${Math.floor(pulseOpacity * 255).toString(16).padStart(2, '0')}`);
      gradient.addColorStop(0.7, `${gem.color}${Math.floor(pulseOpacity * 127).toString(16).padStart(2, '0')}`);
      gradient.addColorStop(1, `${gem.color}00`);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      
      // Diamond shape
      ctx.moveTo(0, -gem.size);
      ctx.lineTo(gem.size * 0.7, 0);
      ctx.lineTo(0, gem.size);
      ctx.lineTo(-gem.size * 0.7, 0);
      ctx.closePath();
      ctx.fill();

      // Add inner highlight
      ctx.fillStyle = `rgba(255, 255, 255, ${pulseOpacity * 0.3})`;
      ctx.beginPath();
      ctx.moveTo(0, -gem.size * 0.6);
      ctx.lineTo(gem.size * 0.4, 0);
      ctx.lineTo(0, gem.size * 0.6);
      ctx.lineTo(-gem.size * 0.4, 0);
      ctx.closePath();
      ctx.fill();

      ctx.restore();
    };

    const animate = (timestamp: number) => {
      if (!animated) return;

      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);

      gemstonesRef.current.forEach((gem) => {
        // Update rotation
        gem.rotation += gem.rotationSpeed;
        
        // Update pulse phase
        gem.pulsePhase += 0.03;
        
        // Slow drift movement
        gem.y += gem.rotationSpeed * 10;
        if (gem.y > rect.height + gem.size) {
          gem.y = -gem.size;
          gem.x = Math.random() * rect.width;
        }

        drawGemstone(gem);
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    // Intersection Observer for performance
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(canvas);
    resizeCanvas();
    
    if (animated) {
      animationRef.current = requestAnimationFrame(animate);
    } else {
      // Static render
      gemstonesRef.current.forEach(drawGemstone);
    }

    window.addEventListener('resize', resizeCanvas);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      observer.disconnect();
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [gemstoneCount, animated]);

  // Pause animation when not visible for performance
  useEffect(() => {
    if (!animated) return;

    if (isVisible && !animationRef.current) {
      const animate = () => {
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext('2d');
        if (!canvas || !ctx) return;

        const rect = canvas.getBoundingClientRect();
        ctx.clearRect(0, 0, rect.width, rect.height);

        gemstonesRef.current.forEach((gem) => {
          gem.rotation += gem.rotationSpeed;
          gem.pulsePhase += 0.03;
          gem.y += gem.rotationSpeed * 10;
          
          if (gem.y > rect.height + gem.size) {
            gem.y = -gem.size;
            gem.x = Math.random() * rect.width;
          }

          const ctx = canvas.getContext('2d')!;
          ctx.save();
          ctx.translate(gem.x, gem.y);
          ctx.rotate(gem.rotation);

          const pulseOpacity = gem.opacity * (0.7 + 0.3 * Math.sin(gem.pulsePhase));
          const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, gem.size);
          gradient.addColorStop(0, `${gem.color}${Math.floor(pulseOpacity * 255).toString(16).padStart(2, '0')}`);
          gradient.addColorStop(1, `${gem.color}00`);

          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.moveTo(0, -gem.size);
          ctx.lineTo(gem.size * 0.7, 0);
          ctx.lineTo(0, gem.size);
          ctx.lineTo(-gem.size * 0.7, 0);
          ctx.closePath();
          ctx.fill();
          ctx.restore();
        });

        if (isVisible) {
          animationRef.current = requestAnimationFrame(animate);
        }
      };
      
      animationRef.current = requestAnimationFrame(animate);
    } else if (!isVisible && animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = undefined;
    }
  }, [isVisible, animated]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none ${className}`}
      style={{ 
        width: '100%', 
        height: '100%',
        opacity: animated ? 0.6 : 0.4 
      }}
      aria-hidden="true"
    />
  );
};

export default GemstoneCanvas;
