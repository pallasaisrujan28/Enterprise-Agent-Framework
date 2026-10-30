'use client'

import React, { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RobotCharacter from './RobotCharacter'

interface RobotSceneProps {
  animationState?: 'idle' | 'walking' | 'running' | 'celebrating' | 'thinking'
  lookAt?: { x: number; y: number; z: number }
  className?: string
}

const RobotScene = ({ animationState = 'idle', lookAt, className = '' }: RobotSceneProps) => {
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas
        camera={{ position: [4, 2, 4], fov: 45 }}
        shadows
        gl={{ alpha: true, antialias: true }}
        style={{ background: 'transparent' }}
      >
        <Suspense fallback={null}>
          {/* Enhanced Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight
            position={[8, 8, 5]}
            intensity={1.2}
            castShadow
            shadow-mapSize-width={2048}
            shadow-mapSize-height={2048}
            shadow-camera-far={50}
            shadow-camera-left={-10}
            shadow-camera-right={10}
            shadow-camera-top={10}
            shadow-camera-bottom={-10}
          />
          <pointLight position={[-6, 4, -4]} intensity={0.6} color="#8b5cf6" />
          <pointLight position={[6, 4, 6]} intensity={0.6} color="#3b82f6" />
          <spotLight position={[0, 8, 0]} intensity={0.4} angle={0.3} penumbra={1} color="#06b6d4" />

          {/* Robot */}
          <RobotCharacter animationState={animationState} lookAt={lookAt} />

          {/* Grid Floor */}
          <gridHelper args={[12, 12, '#1e293b', '#0f172a']} position={[0, -1.6, 0]} />

          {/* Camera Controls */}
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate={false}
            maxPolarAngle={Math.PI / 2.2}
            minPolarAngle={Math.PI / 5}
            target={[0, 0, 0]}
            enabled={false}
          />
        </Suspense>
      </Canvas>
    </div>
  )
}

export default RobotScene
