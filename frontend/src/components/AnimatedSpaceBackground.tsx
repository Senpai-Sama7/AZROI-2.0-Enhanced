import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
  color: string;
  type: 'star' | 'dust' | 'nebula';
}

interface AnimatedSpaceBackgroundProps {
  className?: string;
  particleCount?: number;
  speed?: number;
}

const AnimatedSpaceBackground: React.FC<AnimatedSpaceBackgroundProps> = ({
  className = '',
  particleCount = 150,
  speed = 1
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animationRef = useRef<number>();
  const mouseRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    // Initialize particles
    const initParticles = () => {
      particlesRef.current = [];
      
      for (let i = 0; i < particleCount; i++) {
        const type = Math.random() < 0.7 ? 'star' : Math.random() < 0.9 ? 'dust' : 'nebula';
        
        particlesRef.current.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: type === 'star' ? Math.random() * 2 + 0.5 : 
                type === 'dust' ? Math.random() * 1 + 0.2 :
                Math.random() * 50 + 20,
          speedX: (Math.random() - 0.5) * speed * 0.5,
          speedY: (Math.random() - 0.5) * speed * 0.5,
          opacity: type === 'star' ? Math.random() * 0.8 + 0.2 :
                   type === 'dust' ? Math.random() * 0.4 + 0.1 :
                   Math.random() * 0.1 + 0.05,
          color: type === 'star' ? '#ffffff' :
                 type === 'dust' ? '#c084fc' :
                 ['#8b5cf6', '#ec4899', '#06b6d4'][Math.floor(Math.random() * 3)],
          type
        });
      }
    };

    // Mouse movement effect
    const handleMouseMove = (event: MouseEvent) => {
      mouseRef.current.x = event.clientX;
      mouseRef.current.y = event.clientY;
    };

    // Animation loop
    const animate = () => {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      particlesRef.current.forEach((particle) => {
        // Update position
        particle.x += particle.speedX;
        particle.y += particle.speedY;

        // Mouse interaction for stars
        if (particle.type === 'star') {
          const dx = mouseRef.current.x - particle.x;
          const dy = mouseRef.current.y - particle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance < 100) {
            const force = (100 - distance) / 100;
            particle.x -= (dx / distance) * force * 0.5;
            particle.y -= (dy / distance) * force * 0.5;
          }
        }

        // Wrap around screen
        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = canvas.height;
        if (particle.y > canvas.height) particle.y = 0;

        // Draw particle
        ctx.save();
        ctx.globalAlpha = particle.opacity;

        if (particle.type === 'star') {
          // Draw twinkling star
          const twinkle = Math.sin(Date.now() * 0.003 + particle.x) * 0.3 + 0.7;
          ctx.globalAlpha *= twinkle;
          
          ctx.fillStyle = particle.color;
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          ctx.fill();
          
          // Add glow
          const gradient = ctx.createRadialGradient(
            particle.x, particle.y, 0,
            particle.x, particle.y, particle.size * 3
          );
          gradient.addColorStop(0, `rgba(255, 255, 255, ${twinkle * 0.3})`);
          gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
          
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size * 3, 0, Math.PI * 2);
          ctx.fill();
          
        } else if (particle.type === 'dust') {
          // Draw cosmic dust
          ctx.fillStyle = particle.color;
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          ctx.fill();
          
        } else if (particle.type === 'nebula') {
          // Draw nebula clouds
          const gradient = ctx.createRadialGradient(
            particle.x, particle.y, 0,
            particle.x, particle.y, particle.size
          );
          gradient.addColorStop(0, `${particle.color}40`);
          gradient.addColorStop(0.5, `${particle.color}20`);
          gradient.addColorStop(1, `${particle.color}00`);
          
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.restore();
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    resizeCanvas();
    initParticles();
    animate();

    window.addEventListener('resize', () => {
      resizeCanvas();
      initParticles();
    });
    
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [particleCount, speed]);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 pointer-events-none ${className}`}
      style={{ zIndex: -1 }}
      aria-hidden="true"
    />
  );
};

export default AnimatedSpaceBackground;
