'use client'

import React, { useRef, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Box, Text, Torus, Cylinder } from '@react-three/drei'
import * as THREE from 'three'

interface ProgressVisualizationProps {
  progress: number
  stage: 'analyzing' | 'extracting' | 'processing' | 'validating' | 'finalizing'
  isVisible: boolean
  operationType?: string
}

function ProgressOrb({ progress, position, color }: { progress: number, position: [number, number, number], color: string }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const glowRef = useRef<THREE.Mesh>(null!)
  
  useFrame((state) => {
    if (meshRef.current && glowRef.current) {
      const time = state.clock.elapsedTime
      meshRef.current.rotation.y = time * 0.5
      
      // Pulsing effect based on progress
      const pulse = 1 + Math.sin(time * 3) * 0.1 * (progress / 100)
      meshRef.current.scale.setScalar(pulse)
      
      // Glow intensity based on progress
      const material = glowRef.current.material as THREE.MeshBasicMaterial
      material.opacity = 0.3 + (progress / 100) * 0.4
    }
  })

  return (
    <group position={position}>
      <Sphere ref={meshRef} args={[0.5, 32, 32]}>
        <meshStandardMaterial 
          color={color} 
          transparent 
          opacity={0.8}
          emissive={color}
          emissiveIntensity={progress / 200}
        />
      </Sphere>
      <Sphere ref={glowRef} args={[0.7, 16, 16]}>
        <meshBasicMaterial 
          color={color} 
          transparent 
          opacity={0.2}
        />
      </Sphere>
    </group>
  )
}

function ProgressRing({ progress, radius, color }: { progress: number, radius: number, color: string }) {
  const ringRef = useRef<THREE.Mesh>(null!)
  
  useFrame(() => {
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.01
    }
  })

  const circumference = 2 * Math.PI * radius
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (progress / 100) * circumference

  return (
    <Torus 
      ref={ringRef}
      args={[radius, 0.05, 8, 32, (progress / 100) * Math.PI * 2]}
      rotation={[Math.PI / 2, 0, 0]}
    >
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
    </Torus>
  )
}

function DataFlow({ stage, progress }: { stage: string, progress: number }) {
  const particlesRef = useRef<THREE.Group>(null!)
  
  useFrame((state) => {
    if (particlesRef.current) {
      const time = state.clock.elapsedTime
      particlesRef.current.children.forEach((child, index) => {
        const mesh = child as THREE.Mesh
        const speed = 0.02 + (progress / 100) * 0.03
        mesh.position.x = Math.sin(time * speed + index) * 2
        mesh.position.y = Math.cos(time * speed + index * 0.5) * 1.5
        mesh.position.z = Math.sin(time * speed + index * 0.3) * 1
      })
    }
  })

  const particleCount = Math.floor(5 + (progress / 100) * 10)
  
  return (
    <group ref={particlesRef}>
      {Array.from({ length: particleCount }).map((_, i) => (
        <Box key={i} args={[0.05, 0.05, 0.05]} position={[0, 0, 0]}>
          <meshStandardMaterial 
            color={stage === 'analyzing' ? '#3b82f6' : 
                   stage === 'extracting' ? '#10b981' : 
                   stage === 'processing' ? '#f59e0b' : 
                   stage === 'validating' ? '#8b5cf6' : '#ef4444'} 
            transparent 
            opacity={0.7}
          />
        </Box>
      ))}
    </group>
  )
}

function CentralCore({ progress, stage }: { progress: number, stage: string }) {
  const coreRef = useRef<THREE.Mesh>(null!)
  
  useFrame((state) => {
    if (coreRef.current) {
      const time = state.clock.elapsedTime
      coreRef.current.rotation.x = time * 0.3
      coreRef.current.rotation.y = time * 0.2
      
      // Scale based on progress
      const scale = 0.8 + (progress / 100) * 0.4
      coreRef.current.scale.setScalar(scale)
    }
  })

  const coreColor = 
    stage === 'analyzing' ? '#3b82f6' :
    stage === 'extracting' ? '#10b981' :
    stage === 'processing' ? '#f59e0b' :
    stage === 'validating' ? '#8b5cf6' : '#ef4444'

  return (
    <Box ref={coreRef} args={[1, 1, 1]}>
      <meshStandardMaterial 
        color={coreColor}
        transparent 
        opacity={0.6}
        wireframe
        emissive={coreColor}
        emissiveIntensity={progress / 300}
      />
    </Box>
  )
}

function Scene({ progress, stage, operationType }: { progress: number, stage: string, operationType?: string }) {
  const stageMessages = {
    analyzing: 'Analyzing Input Data',
    extracting: 'Extracting Persona Attributes',
    processing: operationType ? `Performing ${operationType} Operation` : 'Processing Data',
    validating: 'Validating Results',
    finalizing: 'Finalizing Output'
  }

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#ffffff" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#3b82f6" />
      <pointLight position={[0, 10, -10]} intensity={0.3} color="#10b981" />
      
      <CentralCore progress={progress} stage={stage} />
      
      <ProgressRing progress={progress} radius={2} color="#3b82f6" />
      <ProgressRing progress={progress * 0.8} radius={2.5} color="#10b981" />
      <ProgressRing progress={progress * 0.6} radius={3} color="#f59e0b" />
      
      <ProgressOrb progress={progress} position={[-3, 2, 0]} color="#ef4444" />
      <ProgressOrb progress={progress} position={[3, 2, 0]} color="#10b981" />
      <ProgressOrb progress={progress} position={[0, 3, 2]} color="#f59e0b" />
      <ProgressOrb progress={progress} position={[0, -3, -2]} color="#8b5cf6" />
      
      <DataFlow stage={stage} progress={progress} />
      
      <Text
        position={[0, -4, 0]}
        fontSize={0.4}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        maxWidth={10}
      >
        {stageMessages[stage as keyof typeof stageMessages]}
      </Text>
      
      <Text
        position={[0, -4.8, 0]}
        fontSize={0.3}
        color="#94a3b8"
        anchorX="center"
        anchorY="middle"
      >
        {Math.round(progress)}% Complete
      </Text>
    </>
  )
}

export default function ProgressVisualization({ 
  progress, 
  stage, 
  isVisible, 
  operationType 
}: ProgressVisualizationProps) {
  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
      <div className="w-[600px] h-[600px]">
        <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
          <Scene progress={progress} stage={stage} operationType={operationType} />
        </Canvas>
      </div>
    </div>
  )
}