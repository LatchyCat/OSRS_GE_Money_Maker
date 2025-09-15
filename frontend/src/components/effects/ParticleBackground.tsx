import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Sphere, Text } from '@react-three/drei';
import * as THREE from 'three';

interface Particle {
  id: number;
  position: [number, number, number];
  velocity: [number, number, number];
  rotation: number;
  rotationSpeed: number;
  scale: number;
  opacity: number;
  targetOpacity: number;
  color: string;
  type: 'coin' | 'gem' | 'spark';
}

interface ParticleProps {
  particle: Particle;
  mousePosition: { x: number; y: number };
}

const ParticleComponent: React.FC<ParticleProps> = ({ particle, mousePosition }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  useFrame((state, delta) => {
    if (!meshRef.current) return;
    
    // Update rotation
    meshRef.current.rotation.y += particle.rotationSpeed * delta;
    meshRef.current.rotation.x += particle.rotationSpeed * 0.5 * delta;
    
    // Mouse interaction - particles are attracted to mouse
    const mouseDistance = Math.sqrt(
      Math.pow(mousePosition.x - particle.position[0], 2) + 
      Math.pow(mousePosition.y - particle.position[1], 2)
    );
    
    if (mouseDistance < 2) {
      const attractionForce = (2 - mouseDistance) * 0.001;
      const angle = Math.atan2(
        mousePosition.y - particle.position[1], 
        mousePosition.x - particle.position[0]
      );
      
      // Apply gentle attraction force
      meshRef.current.position.x += Math.cos(angle) * attractionForce;
      meshRef.current.position.y += Math.sin(angle) * attractionForce;
    }
    
    // Gentle floating motion
    meshRef.current.position.y += Math.sin(state.clock.elapsedTime + particle.id) * 0.0005;
    meshRef.current.position.x += Math.cos(state.clock.elapsedTime * 0.5 + particle.id) * 0.0002;
    
    // Opacity animation
    if (particle.type === 'spark') {
      particle.opacity = Math.max(0, particle.opacity - delta * 0.5);
    }
  });
  
  const geometry = useMemo(() => {
    if (particle.type === 'coin') {
      return new THREE.CylinderGeometry(0.05, 0.05, 0.01, 8);
    } else if (particle.type === 'gem') {
      return new THREE.OctahedronGeometry(0.03);
    } else {
      return new THREE.SphereGeometry(0.02);
    }
  }, [particle.type]);
  
  const material = useMemo(() => {
    const baseColor = new THREE.Color(particle.color);
    
    if (particle.type === 'coin') {
      return new THREE.MeshPhysicalMaterial({
        color: baseColor,
        metalness: 0.9,
        roughness: 0.1,
        transparent: true,
        opacity: particle.opacity,
        emissive: baseColor,
        emissiveIntensity: 0.2,
      });
    } else if (particle.type === 'gem') {
      return new THREE.MeshPhysicalMaterial({
        color: baseColor,
        metalness: 0.3,
        roughness: 0.0,
        transparent: true,
        opacity: particle.opacity * 0.8,
        transmission: 0.9,
        ior: 2.4,
        emissive: baseColor,
        emissiveIntensity: 0.3,
      });
    } else {
      return new THREE.MeshBasicMaterial({
        color: baseColor,
        transparent: true,
        opacity: particle.opacity,
      });
    }
  }, [particle.color, particle.opacity, particle.type]);
  
  return (
    <mesh
      ref={meshRef}
      position={particle.position}
      scale={particle.scale}
      geometry={geometry}
      material={material}
    />
  );
};

interface ParticleBackgroundProps {
  profitLevel: number; // 0-1 scale based on current profits
  intensity: number; // 0-1 scale for particle density
  mousePosition: { x: number; y: number };
}

const ParticleSystem: React.FC<ParticleBackgroundProps> = ({ 
  profitLevel, 
  intensity, 
  mousePosition 
}) => {
  const [particles, setParticles] = useState<Particle[]>([]);
  const { size } = useThree();
  
  useEffect(() => {
    const particleCount = Math.floor(20 + (intensity * 30));
    const newParticles: Particle[] = [];
    
    for (let i = 0; i < particleCount; i++) {
      const type = Math.random() < 0.6 ? 'coin' : Math.random() < 0.8 ? 'gem' : 'spark';
      
      let color = '#fbbf24'; // Default gold
      if (type === 'gem') {
        const gemColors = ['#3b82f6', '#8b5cf6', '#ec4899', '#10b981'];
        color = gemColors[Math.floor(Math.random() * gemColors.length)];
      } else if (type === 'spark') {
        color = profitLevel > 0.7 ? '#22c55e' : profitLevel > 0.4 ? '#f59e0b' : '#6b7280';
      }
      
      newParticles.push({
        id: i,
        position: [
          (Math.random() - 0.5) * (size.width / 100),
          (Math.random() - 0.5) * (size.height / 100),
          (Math.random() - 0.5) * 2
        ],
        velocity: [
          (Math.random() - 0.5) * 0.01,
          Math.random() * 0.005 + 0.002,
          (Math.random() - 0.5) * 0.005
        ],
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: Math.random() * 0.5 + 0.2,
        scale: Math.random() * 0.5 + 0.5,
        opacity: Math.random() * 0.8 + 0.2,
        targetOpacity: Math.random() * 0.8 + 0.2,
        color,
        type: type as 'coin' | 'gem' | 'spark'
      });
    }
    
    setParticles(newParticles);
  }, [intensity, profitLevel, size]);
  
  useFrame((state, delta) => {
    setParticles(prev => prev.map(particle => {
      // Update position based on velocity
      const newPosition: [number, number, number] = [
        particle.position[0] + particle.velocity[0] * delta * 60,
        particle.position[1] + particle.velocity[1] * delta * 60,
        particle.position[2] + particle.velocity[2] * delta * 60
      ];
      
      // Wrap particles around screen edges
      if (newPosition[0] > size.width / 100) newPosition[0] = -size.width / 100;
      if (newPosition[0] < -size.width / 100) newPosition[0] = size.width / 100;
      if (newPosition[1] > size.height / 100) newPosition[1] = -size.height / 100;
      if (newPosition[1] < -size.height / 100) newPosition[1] = size.height / 100;
      
      return {
        ...particle,
        position: newPosition,
        opacity: Math.max(0, Math.min(1, particle.opacity + (particle.targetOpacity - particle.opacity) * delta))
      };
    }).filter(particle => particle.opacity > 0.01));
  });
  
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.6} color="#fbbf24" />
      <pointLight position={[-10, -10, 10]} intensity={0.3} color="#3b82f6" />
      
      {particles.map(particle => (
        <ParticleComponent 
          key={particle.id} 
          particle={particle} 
          mousePosition={mousePosition}
        />
      ))}
    </>
  );
};

export const ParticleBackground: React.FC<{
  profitLevel?: number;
  intensity?: number;
  className?: string;
}> = ({ 
  profitLevel = 0.5, 
  intensity = 0.6,
  className = ""
}) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      const x = (event.clientX / window.innerWidth) * 2 - 1;
      const y = -(event.clientY / window.innerHeight) * 2 + 1;
      setMousePosition({ x: x * 5, y: y * 3 });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);
  
  return (
    <div className={`fixed inset-0 pointer-events-none z-0 ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 75 }}
        gl={{ 
          alpha: true, 
          antialias: true,
          powerPreference: "high-performance"
        }}
      >
        <ParticleSystem 
          profitLevel={profitLevel}
          intensity={intensity}
          mousePosition={mousePosition}
        />
      </Canvas>
    </div>
  );
};