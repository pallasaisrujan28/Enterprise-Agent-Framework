'use client'

import React, { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Environment, ContactShadows, PerspectiveCamera } from '@react-three/drei'
import AdvancedRobotCharacter from './AdvancedRobotCharacter'

interface AdvancedRobotSceneProps {
  animationState?: 'idle' | 'walking' | 'running' | 'celebrating' | 'thinking' | 'death'
  lookAt?: { x: number; y: number; z: number }
  className?: string
  autoRotate?: boolean
  showEnvironment?: boolean
}

const AdvancedRobotScene = ({
  animationState = 'walking', // Default to walking animation
  lookAt,
  className = '',
  autoRotate = false,
  showEnvironment = true
}: AdvancedRobotSceneProps) => {
  return (
    <div className={`w-full h-full relative ${className}`}>
      {/* Background image layer */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          backgroundImage: 'url(/images/Background_robot.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          zIndex: 0
        }}
      />

      {/* Canvas layer */}
      <Canvas
        className="absolute inset-0"
        shadows
        gl={{
          alpha: true,
          antialias: true,
          powerPreference: "high-performance"
        }}
        style={{ background: 'transparent', zIndex: 1 }}
        dpr={[1, 2]}
      >
        <Suspense fallback={null}>
          
          <PerspectiveCamera
            makeDefault
            position={[0, 3, 10]}
            fov={90}
            near={0.1}
            far={120}
          />

          {/* Lab-style lighting setup */}
          <ambientLight intensity={0.8} color="#c5d9f0" />

          {/* Main overhead light (lab ceiling light) */}
          <directionalLight
            position={[0, 6, 2]}
            intensity={2.5}
            castShadow
            shadow-mapSize-width={2048}
            shadow-mapSize-height={2048}
            shadow-camera-far={20}
            shadow-camera-left={-10}
            shadow-camera-right={10}
            shadow-camera-top={10}
            shadow-camera-bottom={-10}
            color="#d4e4f7"
          />

          {/* Lab accent lights - blue tones */}
          <pointLight position={[-3, 3, 2]} intensity={1.2} color="#4d7ba8" distance={10} />
          <pointLight position={[3, 3, 2]} intensity={1.2} color="#5a8fc4" distance={10} />

          {/* Monitor screen glow simulation */}
          <spotLight
            position={[4, 2, 4]}
            angle={0.4}
            penumbra={0.8}
            intensity={0.8}
            color="#6ba3d8"
          />

          {/* Subtle rim light */}
          <directionalLight
            position={[-2, 1, -2]}
            intensity={0.6}
            color="#8db4d9"
          />

          {/* Environment for reflections - background disabled to show image */}
          {showEnvironment && (
            <Environment
              preset="city"
              background={false}
              blur={0.5}
            />
          )}

          {/* Robot Character - positioned higher to be fully visible */}
          <AdvancedRobotCharacter 
            animationState={animationState} 
            lookAt={lookAt} 
          />

          {/* Road/Path - realistic road surface */}
          <group position={[0, -0.8, 0]}>
            {/* Main road surface */}
            <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[4, 12]} />
              <meshStandardMaterial
                color="#2a3540"
                roughness={0.9}
                metalness={0.1}
                emissive="#1a2028"
                emissiveIntensity={0.05}
              />
            </mesh>

            {/* Center dashed line */}
            {Array.from({ length: 8 }).map((_, i) => (
              <mesh key={`center-${i}`} position={[0, 0.01, -5 + i * 1.5]} rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[0.08, 0.6]} />
                <meshBasicMaterial color="#ffd700" transparent opacity={0.8} />
              </mesh>
            ))}

            {/* Road edge lines */}
            <mesh position={[-1.9, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[0.05, 12]} />
              <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
            </mesh>
            <mesh position={[1.9, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[0.05, 12]} />
              <meshBasicMaterial color="#ffffff" transparent opacity={0.6} />
            </mesh>
          </group>

          {/* Contact shadows */}
          <ContactShadows
            position={[0, -0.79, 0]}
            opacity={0.5}
            scale={4}
            blur={2}
            far={4}
            color="#0f172a"
          />

          {/* Camera controls - zoom disabled, fixed view */}
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            enableRotate={false}
            autoRotate={autoRotate}
            autoRotateSpeed={0.2}
            target={[0, 1, 0]}
          />
        </Suspense>
      </Canvas>
      
      {/* Status indicator - properly positioned */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
        <div className="bg-black/70 backdrop-blur-sm rounded-full px-4 py-2">
        </div>
      </div>
    </div>
  )
}

export default AdvancedRobotScene