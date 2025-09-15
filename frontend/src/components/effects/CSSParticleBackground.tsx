import React, { useEffect, useRef, useState, useCallback } from 'react';

interface Particle {
  id: number;
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  rotation: number;
  rotationSpeed: number;
  scale: number;
  opacity: number;
  type: 'coin' | 'gem' | 'spark';
  color: string;
  life: number;
}

interface CSSParticleBackgroundProps {
  profitLevel?: number; // 0-1 scale based on current profits
  intensity?: number; // 0-1 scale for particle density
  className?: string;
}

export const CSSParticleBackground: React.FC<CSSParticleBackgroundProps> = ({
  profitLevel = 0.5,
  intensity = 0.6,
  className = ""
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const particlesRef = useRef<Particle[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();
  const lastFrameTimeRef = useRef<number>(0);
  const isVisibleRef = useRef<boolean>(true);

  useEffect(() => {
    const updateDimensions = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Scroll detection for performance optimization
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolling(true);
      
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      
      scrollTimeoutRef.current = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  // Intersection Observer for visibility detection
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisibleRef.current = entry.isIntersecting;
        });
      },
      { threshold: 0.1 }
    );

    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      // Throttle mouse updates during scrolling
      if (isScrolling) return;
      
      mouseRef.current = {
        x: (event.clientX / window.innerWidth) * 2 - 1,
        y: -(event.clientY / window.innerHeight) * 2 + 1
      };
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [isScrolling]);

  const createParticle = (index: number): Particle => {
    const type = Math.random() < 0.6 ? 'coin' : Math.random() < 0.8 ? 'gem' : 'spark';
    
    let color = '#fbbf24'; // Default gold
    if (type === 'gem') {
      const gemColors = ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981'];
      color = gemColors[Math.floor(Math.random() * gemColors.length)];
    } else if (type === 'spark') {
      color = profitLevel > 0.7 ? '#22c55e' : profitLevel > 0.4 ? '#f59e0b' : '#6b7280';
    }

    return {
      id: index,
      x: Math.random() * dimensions.width,
      y: Math.random() * dimensions.height,
      z: Math.random() * 1000,
      vx: (Math.random() - 0.5) * 0.5,
      vy: Math.random() * 0.5 + 0.1,
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: Math.random() * 0.02 + 0.01,
      scale: Math.random() * 0.8 + 0.4,
      opacity: Math.random() * 0.8 + 0.2,
      type,
      color,
      life: type === 'spark' ? Math.random() * 2 + 1 : Infinity
    };
  };

  const initializeParticles = useCallback(() => {
    // Reduce particle count during scrolling for better performance
    const baseCount = isScrolling ? 8 : 15;
    const particleCount = Math.floor(baseCount + (intensity * (isScrolling ? 10 : 25)));
    particlesRef.current = Array.from({ length: particleCount }, (_, i) => createParticle(i));
  }, [intensity, isScrolling]);

  const drawParticle = (ctx: CanvasRenderingContext2D, particle: Particle) => {
    ctx.save();
    
    // Calculate 3D perspective
    const perspective = 500;
    const scale3D = perspective / (perspective + particle.z);
    const x = particle.x * scale3D;
    const y = particle.y * scale3D;
    
    ctx.translate(x, y);
    ctx.rotate(particle.rotation);
    ctx.scale(particle.scale * scale3D, particle.scale * scale3D);
    ctx.globalAlpha = particle.opacity * Math.max(0.3, scale3D);
    
    if (particle.type === 'coin') {
      // Draw coin
      const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 8);
      gradient.addColorStop(0, particle.color + 'FF');
      gradient.addColorStop(0.7, particle.color + 'AA');
      gradient.addColorStop(1, particle.color + '44');
      
      ctx.fillStyle = gradient;
      ctx.shadowColor = particle.color;
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.ellipse(0, 0, 8, 2, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Add metallic shine
      ctx.fillStyle = '#ffffff44';
      ctx.beginPath();
      ctx.ellipse(-2, -1, 3, 1, 0, 0, Math.PI * 2);
      ctx.fill();
      
    } else if (particle.type === 'gem') {
      // Draw gem
      const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, 6);
      gradient.addColorStop(0, particle.color + 'FF');
      gradient.addColorStop(0.5, particle.color + 'CC');
      gradient.addColorStop(1, particle.color + '33');
      
      ctx.fillStyle = gradient;
      ctx.shadowColor = particle.color;
      ctx.shadowBlur = 8;
      
      // Diamond shape
      ctx.beginPath();
      ctx.moveTo(0, -6);
      ctx.lineTo(4, -2);
      ctx.lineTo(0, 6);
      ctx.lineTo(-4, -2);
      ctx.closePath();
      ctx.fill();
      
      // Add crystalline highlight
      ctx.fillStyle = '#ffffff66';
      ctx.beginPath();
      ctx.moveTo(0, -6);
      ctx.lineTo(2, -3);
      ctx.lineTo(0, 0);
      ctx.lineTo(-2, -3);
      ctx.closePath();
      ctx.fill();
      
    } else {
      // Draw spark
      ctx.fillStyle = particle.color + Math.floor(particle.opacity * 255).toString(16).padStart(2, '0');
      ctx.shadowColor = particle.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(0, 0, 3, 0, Math.PI * 2);
      ctx.fill();
      
      // Add spark trails
      ctx.strokeStyle = particle.color + '66';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(-6, 0);
      ctx.lineTo(6, 0);
      ctx.moveTo(0, -6);
      ctx.lineTo(0, 6);
      ctx.stroke();
    }
    
    ctx.restore();
  };

  const updateParticles = useCallback((deltaTime: number) => {
    // Skip expensive updates during scrolling
    if (isScrolling && deltaTime < 33) { // Skip updates if running faster than 30fps during scroll
      return;
    }

    particlesRef.current = particlesRef.current.map(particle => {
      // Basic position update
      particle.x += particle.vx * deltaTime * 0.8; // Slightly slower during scroll
      particle.y += particle.vy * deltaTime * 0.8;
      particle.rotation += particle.rotationSpeed * deltaTime;
      
      // Skip mouse interaction during scrolling for performance
      if (!isScrolling) {
        const mouseDistance = Math.sqrt(
          Math.pow(mouseRef.current.x * dimensions.width/2 + dimensions.width/2 - particle.x, 2) +
          Math.pow(mouseRef.current.y * dimensions.height/2 + dimensions.height/2 - particle.y, 2)
        );
        
        if (mouseDistance < 100) {
          const force = (100 - mouseDistance) * 0.0001;
          const angle = Math.atan2(
            mouseRef.current.y * dimensions.height/2 + dimensions.height/2 - particle.y,
            mouseRef.current.x * dimensions.width/2 + dimensions.width/2 - particle.x
          );
          particle.vx += Math.cos(angle) * force;
          particle.vy += Math.sin(angle) * force;
        }
      }
      
      // Simplified floating motion during scroll
      const floatIntensity = isScrolling ? 0.05 : 0.1;
      particle.x += Math.sin(Date.now() * 0.001 + particle.id) * floatIntensity;
      particle.y += Math.cos(Date.now() * 0.0007 + particle.id) * (floatIntensity * 0.5);
      
      // Wrap around screen
      if (particle.x > dimensions.width + 50) particle.x = -50;
      if (particle.x < -50) particle.x = dimensions.width + 50;
      if (particle.y > dimensions.height + 50) particle.y = -50;
      if (particle.y < -50) particle.y = dimensions.height + 50;
      
      // Update spark life (less frequent during scroll)
      if (particle.type === 'spark' && (!isScrolling || Math.random() > 0.7)) {
        particle.life -= deltaTime * 0.001;
        if (particle.life <= 0) {
          return createParticle(particle.id);
        }
        particle.opacity = Math.max(0, particle.life * 0.5);
      }
      
      return particle;
    });
  }, [isScrolling, dimensions.width, dimensions.height]);

  const animate = useCallback((currentTime: number) => {
    const canvas = canvasRef.current;
    if (!canvas || !isVisibleRef.current) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      animationRef.current = requestAnimationFrame(animate);
      return;
    }
    
    // Frame rate control - limit to 30fps during scrolling, 60fps when idle
    const targetFPS = isScrolling ? 30 : 60;
    const targetFrameTime = 1000 / targetFPS;
    const deltaTime = currentTime - lastFrameTimeRef.current;
    
    if (deltaTime >= targetFrameTime) {
      // Clear canvas with better performance
      ctx.clearRect(0, 0, dimensions.width, dimensions.height);
      
      // Update and draw particles
      updateParticles(deltaTime);
      
      // Reduce draw calls during scrolling
      const drawEveryNth = isScrolling ? 2 : 1;
      particlesRef.current.forEach((particle, index) => {
        if (!isScrolling || index % drawEveryNth === 0) {
          drawParticle(ctx, particle);
        }
      });
      
      lastFrameTimeRef.current = currentTime;
    }
    
    animationRef.current = requestAnimationFrame(animate);
  }, [isScrolling, dimensions, updateParticles]);

  useEffect(() => {
    if (dimensions.width && dimensions.height) {
      initializeParticles();
      animationRef.current = requestAnimationFrame(animate);
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [dimensions, profitLevel, intensity]);

  return (
    <canvas
      ref={canvasRef}
      width={dimensions.width}
      height={dimensions.height}
      className={`fixed inset-0 pointer-events-none z-0 ${className}`}
      style={{ 
        background: 'transparent',
        imageRendering: 'auto',
        willChange: 'transform',
        transform: 'translateZ(0)', // Force hardware acceleration
        backfaceVisibility: 'hidden'
      }}
    />
  );
};