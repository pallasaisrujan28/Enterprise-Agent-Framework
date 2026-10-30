'use client'

import React, { useRef, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Box, Text } from '@react-three/drei'
import * as THREE from 'three'

interface LoadingAnimationProps {
  message?: string
  progress?: number
  isVisible: boolean
}

function AnimatedSphere({ position, color, speed }: { position: [number, number, number], color: string, speed: number }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * speed
      meshRef.current.rotation.y = state.clock.elapsedTime * speed * 0.5
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.2
    }
  })

  return (
    <Sphere ref={meshRef} position={position} args={[0.3, 32, 32]}>
      <meshStandardMaterial color={color} transparent opacity={0.8} />
    </Sphere>
  )
}

function RotatingCube() {
  const meshRef = useRef<THREE.Mesh>(null!)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.5
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.3
      meshRef.current.rotation.z = state.clock.elapsedTime * 0.2
    }
  })

  return (
    <Box ref={meshRef} args={[0.8, 0.8, 0.8]}>
      <meshStandardMaterial 
        color="#3b82f6" 
        transparent 
        opacity={0.6}
        wireframe
      />
    </Box>
  )
}

function ProgressRing({ progress }: { progress: number }) {
  const ringRef = useRef<THREE.Mesh>(null!)
  
  useFrame(() => {
    if (ringRef.current) {
      const scale = 1 + Math.sin(Date.now() * 0.003) * 0.1
      ringRef.current.scale.setScalar(scale)
    }
  })

  return (
    <group>
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.5, 1.8, 32]} />
        <meshStandardMaterial color="#10b981" transparent opacity={0.7} />
      </mesh>
      <Text
        position={[0, 0, 0]}
        fontSize={0.3}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
      >
        {Math.round(progress)}%
      </Text>
    </group>
  )
}

function Scene({ message, progress }: { message: string, progress: number }) {
  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#3b82f6" />
      
      <RotatingCube />
      
      <AnimatedSphere position={[-2, 0, 0]} color="#ef4444" speed={1} />
      <AnimatedSphere position={[2, 0, 0]} color="#10b981" speed={-1} />
      <AnimatedSphere position={[0, 2, 0]} color="#f59e0b" speed={1.5} />
      <AnimatedSphere position={[0, -2, 0]} color="#8b5cf6" speed={-1.5} />
      
      <ProgressRing progress={progress} />
      
      <Text
        position={[0, -3, 0]}
        fontSize={0.4}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        maxWidth={8}
      >
        {message}
      </Text>
    </>
  )
}

export default function LoadingAnimation({ message = "Processing...", progress = 0, isVisible }: LoadingAnimationProps) {
  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
      <div className="w-96 h-96">
        <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
          <Scene message={message} progress={progress} />
        </Canvas>
      </div>
    </div>
  )
}