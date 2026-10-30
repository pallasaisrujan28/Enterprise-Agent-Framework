'use client'

import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { MeshStandardMaterial, Vector3 } from 'three'
import * as THREE from 'three'

interface RobotCharacterProps {
  animationState: 'idle' | 'walking' | 'running' | 'celebrating' | 'thinking'
  lookAt?: { x: number; y: number; z: number }
}

const RobotCharacter = ({ animationState = 'idle', lookAt }: RobotCharacterProps) => {
  const groupRef = useRef<THREE.Group>(null!)

  // Body parts refs
  const leftLegRef = useRef<THREE.Mesh>(null!)
  const rightLegRef = useRef<THREE.Mesh>(null!)
  const leftArmRef = useRef<THREE.Mesh>(null!)
  const rightArmRef = useRef<THREE.Mesh>(null!)
  const headRef = useRef<THREE.Mesh>(null!)
  const leftHandRef = useRef<THREE.Mesh>(null!)
  const rightHandRef = useRef<THREE.Mesh>(null!)

  // Animation state
  const animationRef = useRef({ time: 0, phase: 0, walkProgress: 0 })

  // Enhanced materials for better robot skin - more like the reference robot
  const bodyMaterial = useMemo(() => new MeshStandardMaterial({
    color: '#60a5fa', // Bright blue for main body
    metalness: 0.6,
    roughness: 0.3,
    emissive: '#3b82f6',
    emissiveIntensity: 0.2
  }), [])

  const accentMaterial = useMemo(() => new MeshStandardMaterial({
    color: '#1e40af', // Deep blue for accents
    metalness: 0.7,
    roughness: 0.25,
    emissive: '#1e3a8a',
    emissiveIntensity: 0.15
  }), [])

  const jointMaterial = useMemo(() => new MeshStandardMaterial({
    color: '#475569', // Medium gray for joints (not too dark)
    metalness: 0.8,
    roughness: 0.2
  }), [])

  const eyeMaterial = useMemo(() => new MeshStandardMaterial({
    color: '#60a5fa',
    emissive: '#60a5fa',
    emissiveIntensity: 2.5,
    toneMapped: false
  }), [])

  const glowMaterial = useMemo(() => new MeshStandardMaterial({
    color: '#06b6d4',
    emissive: '#06b6d4',
    emissiveIntensity: 2,
    toneMapped: false,
    transparent: true,
    opacity: 0.9
  }), [])

  useFrame((state, delta) => {
    if (!groupRef.current) return

    animationRef.current.time += delta

    // Keep robot centered and stationary
    groupRef.current.position.x = 0
    groupRef.current.position.z = 0
    groupRef.current.rotation.y = 0

    // Cycle through animations every 3 seconds
    const cycleTime = animationRef.current.time % 6 // 6 seconds total cycle

    if (cycleTime < 3) {
      // First 3 seconds: Wave animation
      const waveSpeed = 4

      // Right arm waving
      if (rightArmRef.current) {
        rightArmRef.current.rotation.x = -1.5 // Arm up
        rightArmRef.current.rotation.z = 0.3 + Math.sin(animationRef.current.time * waveSpeed) * 0.4
      }

      // Left arm down
      if (leftArmRef.current) {
        leftArmRef.current.rotation.x = 0.2
        leftArmRef.current.rotation.z = -0.2
      }

      // Gentle breathing
      groupRef.current.position.y = Math.sin(animationRef.current.time * 1.5) * 0.05

      // Legs stay still
      if (leftLegRef.current) leftLegRef.current.rotation.x = 0
      if (rightLegRef.current) rightLegRef.current.rotation.x = 0

      // Head slightly tilted
      if (headRef.current) {
        headRef.current.rotation.z = Math.sin(animationRef.current.time * 2) * 0.1
        headRef.current.rotation.x = 0
      }
    } else {
      // Next 3 seconds: Thumbs up animation

      // Right arm thumbs up (arm bent, thumb pointing up)
      if (rightArmRef.current) {
        rightArmRef.current.rotation.x = -1.2
        rightArmRef.current.rotation.z = 0.5
      }

      // Left arm down
      if (leftArmRef.current) {
        leftArmRef.current.rotation.x = 0.2
        leftArmRef.current.rotation.z = -0.2
      }

      // Slight bounce
      groupRef.current.position.y = 0.1 + Math.abs(Math.sin(animationRef.current.time * 1.5)) * 0.08

      // Legs stay still
      if (leftLegRef.current) leftLegRef.current.rotation.x = 0
      if (rightLegRef.current) rightLegRef.current.rotation.x = 0

      // Head neutral
      if (headRef.current) {
        headRef.current.rotation.z = 0
        headRef.current.rotation.x = 0
      }
    }
  })

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Torso - Main body */}
      <mesh position={[0, 0.5, 0]} castShadow>
        <boxGeometry args={[0.9, 1.1, 0.6]} />
        <primitive object={bodyMaterial} attach="material" />

        {/* Chest panel accent */}
        <mesh position={[0, 0.2, 0.31]}>
          <boxGeometry args={[0.5, 0.6, 0.05]} />
          <primitive object={accentMaterial} attach="material" />
        </mesh>

        {/* Chest lights */}
        <mesh position={[-0.15, 0.3, 0.32]}>
          <sphereGeometry args={[0.05, 16, 16]} />
          <primitive object={glowMaterial} attach="material" />
        </mesh>
        <mesh position={[0.15, 0.3, 0.32]}>
          <sphereGeometry args={[0.05, 16, 16]} />
          <primitive object={glowMaterial} attach="material" />
        </mesh>
      </mesh>

      {/* Head - Rounded with visor */}
      <mesh ref={headRef} position={[0, 1.35, 0]} castShadow>
        <boxGeometry args={[0.7, 0.7, 0.7]} />
        <primitive object={bodyMaterial} attach="material" />

        {/* Visor */}
        <mesh position={[0, 0.05, 0.36]}>
          <boxGeometry args={[0.6, 0.3, 0.05]} />
          <meshStandardMaterial
            color="#1e293b"
            metalness={1}
            roughness={0}
            emissive="#0ea5e9"
            emissiveIntensity={0.5}
            transparent
            opacity={0.9}
          />
        </mesh>

        {/* Eyes (glowing) */}
        <mesh position={[-0.18, 0.05, 0.38]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <primitive object={eyeMaterial} attach="material" />
        </mesh>
        <mesh position={[0.18, 0.05, 0.38]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <primitive object={eyeMaterial} attach="material" />
        </mesh>

        {/* Antenna with glowing tip */}
        <mesh position={[0, 0.45, 0]}>
          <cylinderGeometry args={[0.04, 0.04, 0.4, 8]} />
          <primitive object={accentMaterial} attach="material" />
          <mesh position={[0, 0.25, 0]}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <primitive object={glowMaterial} attach="material" />
          </mesh>
        </mesh>

        {/* Helmet details */}
        <mesh position={[-0.35, 0, 0]}>
          <boxGeometry args={[0.05, 0.5, 0.5]} />
          <primitive object={accentMaterial} attach="material" />
        </mesh>
        <mesh position={[0.35, 0, 0]}>
          <boxGeometry args={[0.05, 0.5, 0.5]} />
          <primitive object={accentMaterial} attach="material" />
        </mesh>
      </mesh>

      {/* Left Arm - Shoulder joint and arm assembly */}
      <group position={[-0.52, 0.8, 0]}>
        {/* Shoulder joint sphere */}
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <primitive object={jointMaterial} attach="material" />
        </mesh>

        {/* Upper arm - rotates from shoulder */}
        <mesh ref={leftArmRef} position={[0, -0.35, 0]} castShadow>
          <boxGeometry args={[0.2, 0.6, 0.2]} />
          <primitive object={bodyMaterial} attach="material" />

          {/* Elbow joint */}
          <mesh position={[0, -0.35, 0]}>
            <sphereGeometry args={[0.12, 16, 16]} />
            <primitive object={jointMaterial} attach="material" />
          </mesh>

          {/* Forearm */}
          <mesh position={[0, -0.65, 0]}>
            <boxGeometry args={[0.17, 0.5, 0.17]} />
            <primitive object={accentMaterial} attach="material" />

            {/* Wrist joint */}
            <mesh position={[0, -0.3, 0]}>
              <sphereGeometry args={[0.1, 16, 16]} />
              <primitive object={jointMaterial} attach="material" />
            </mesh>

            {/* Hand */}
            <mesh ref={leftHandRef} position={[0, -0.4, 0]}>
              <boxGeometry args={[0.14, 0.18, 0.14]} />
              <primitive object={bodyMaterial} attach="material" />
            </mesh>
          </mesh>
        </mesh>
      </group>

      {/* Right Arm - Shoulder joint and arm assembly */}
      <group position={[0.52, 0.8, 0]}>
        {/* Shoulder joint sphere */}
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <primitive object={jointMaterial} attach="material" />
        </mesh>

        {/* Upper arm - rotates from shoulder */}
        <mesh ref={rightArmRef} position={[0, -0.35, 0]} castShadow>
          <boxGeometry args={[0.2, 0.6, 0.2]} />
          <primitive object={bodyMaterial} attach="material" />

          {/* Elbow joint */}
          <mesh position={[0, -0.35, 0]}>
            <sphereGeometry args={[0.12, 16, 16]} />
            <primitive object={jointMaterial} attach="material" />
          </mesh>

          {/* Forearm */}
          <mesh position={[0, -0.65, 0]}>
            <boxGeometry args={[0.17, 0.5, 0.17]} />
            <primitive object={accentMaterial} attach="material" />

            {/* Wrist joint */}
            <mesh position={[0, -0.3, 0]}>
              <sphereGeometry args={[0.1, 16, 16]} />
              <primitive object={jointMaterial} attach="material" />
            </mesh>

            {/* Hand */}
            <mesh ref={rightHandRef} position={[0, -0.4, 0]}>
              <boxGeometry args={[0.14, 0.18, 0.14]} />
              <primitive object={bodyMaterial} attach="material" />
            </mesh>
          </mesh>
        </mesh>
      </group>

      {/* Left Leg - Hip joint and leg assembly */}
      <group position={[-0.28, 0, 0]}>
        {/* Hip joint */}
        <mesh position={[0, 0.1, 0]}>
          <sphereGeometry args={[0.18, 16, 16]} />
          <primitive object={jointMaterial} attach="material" />
        </mesh>

        {/* Thigh */}
        <mesh ref={leftLegRef} position={[0, -0.4, 0]} castShadow>
          <boxGeometry args={[0.26, 0.9, 0.26]} />
          <primitive object={bodyMaterial} attach="material" />

          {/* Knee joint */}
          <mesh position={[0, -0.5, 0]}>
            <sphereGeometry args={[0.15, 16, 16]} />
            <primitive object={jointMaterial} attach="material" />
          </mesh>

          {/* Shin/Lower leg */}
          <mesh position={[0, -0.75, 0]}>
            <boxGeometry args={[0.23, 0.6, 0.24]} />
            <primitive object={accentMaterial} attach="material" />

            {/* Ankle joint */}
            <mesh position={[0, -0.35, 0]}>
              <sphereGeometry args={[0.12, 16, 16]} />
              <primitive object={jointMaterial} attach="material" />
            </mesh>

            {/* Foot */}
            <mesh position={[0, -0.45, 0.08]}>
              <boxGeometry args={[0.25, 0.14, 0.38]} />
              <primitive object={bodyMaterial} attach="material" />
            </mesh>
          </mesh>
        </mesh>
      </group>

      {/* Right Leg - Hip joint and leg assembly */}
      <group position={[0.28, 0, 0]}>
        {/* Hip joint */}
        <mesh position={[0, 0.1, 0]}>
          <sphereGeometry args={[0.18, 16, 16]} />
          <primitive object={jointMaterial} attach="material" />
        </mesh>

        {/* Thigh */}
        <mesh ref={rightLegRef} position={[0, -0.4, 0]} castShadow>
          <boxGeometry args={[0.26, 0.9, 0.26]} />
          <primitive object={bodyMaterial} attach="material" />

          {/* Knee joint */}
          <mesh position={[0, -0.5, 0]}>
            <sphereGeometry args={[0.15, 16, 16]} />
            <primitive object={jointMaterial} attach="material" />
          </mesh>

          {/* Shin/Lower leg */}
          <mesh position={[0, -0.75, 0]}>
            <boxGeometry args={[0.23, 0.6, 0.24]} />
            <primitive object={accentMaterial} attach="material" />

            {/* Ankle joint */}
            <mesh position={[0, -0.35, 0]}>
              <sphereGeometry args={[0.12, 16, 16]} />
              <primitive object={jointMaterial} attach="material" />
            </mesh>

            {/* Foot */}
            <mesh position={[0, -0.45, 0.08]}>
              <boxGeometry args={[0.25, 0.14, 0.38]} />
              <primitive object={bodyMaterial} attach="material" />
            </mesh>
          </mesh>
        </mesh>
      </group>

      {/* Glowing platform/base */}
      <mesh position={[0, -1.6, 0]} receiveShadow>
        <cylinderGeometry args={[1, 1, 0.1, 32]} />
        <meshStandardMaterial
          color="#1e40af"
          metalness={0.8}
          roughness={0.2}
          emissive="#3b82f6"
          emissiveIntensity={0.3}
          transparent
          opacity={0.6}
        />
      </mesh>
    </group>
  )
}

export default RobotCharacter
