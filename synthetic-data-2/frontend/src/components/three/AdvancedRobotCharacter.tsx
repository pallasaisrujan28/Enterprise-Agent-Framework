'use client'

import React, { useRef, useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import { AnimationMixer, AnimationAction, LoopRepeat, LoopOnce, LoopPingPong } from 'three'
import * as THREE from 'three'
import { SkeletonUtils } from 'three-stdlib'

// Preload the GLTF model
useGLTF.preload('/RobotExpressive.glb')

interface AdvancedRobotCharacterProps {
  animationState: 'idle' | 'walking' | 'running' | 'celebrating' | 'thinking' | 'death'
  lookAt?: { x: number; y: number; z: number }
}

const AdvancedRobotCharacter = ({ animationState = 'idle', lookAt }: AdvancedRobotCharacterProps) => {
  const groupRef = useRef<THREE.Group>(null!)
  const mixerRef = useRef<AnimationMixer | null>(null)
  const actionsRef = useRef<{ [key: string]: AnimationAction }>({})
  const currentActionRef = useRef<string>('')
  const animationCycleRef = useRef({ time: 0, currentGesture: 'idle' })

  // Load the GLTF model using useGLTF hook
  const { scene: gltfScene, animations } = useGLTF('/RobotExpressive.glb')

  // Clone the scene to avoid issues with multiple instances
  const model = useMemo(() => {
    // Use SkeletonUtils.clone() for proper skeleton cloning with rigged models
    const clonedScene = SkeletonUtils.clone(gltfScene)
    
    // Scale the model appropriately and position to show face
    clonedScene.scale.setScalar(1.5)
    
    // Rotate to face forward (towards camera)
    clonedScene.rotation.y = 0
    
    // Traverse and enhance materials - ensure ALL parts including arms/hands are fully visible
    clonedScene.traverse((child: THREE.Object3D) => {
      // Debug: log all object names to see structure
      if (child.name) {
      }

      if (child instanceof THREE.Mesh) {
        child.castShadow = true
        child.receiveShadow = true
        child.frustumCulled = false // Prevent parts from disappearing
        child.visible = true // Force all parts to be visible

        // Ensure proper rendering order
        child.renderOrder = 0

        // Enhance materials for better appearance and visibility
        if (child.material) {
          if (Array.isArray(child.material)) {
            child.material.forEach((mat) => {
              if (mat instanceof THREE.MeshStandardMaterial) {
                mat.metalness = 0.5
                mat.roughness = 0.3
                mat.envMapIntensity = 1.5
                mat.needsUpdate = true
                mat.side = THREE.FrontSide // Use front side only
                mat.depthWrite = true // Ensure proper depth writing
                mat.depthTest = true // Ensure proper depth testing
                // Force fully opaque to ensure arms/hands are visible
                mat.transparent = false
                mat.opacity = 1.0
                mat.polygonOffset = false
                mat.flatShading = false
              }
            })
          } else if (child.material instanceof THREE.MeshStandardMaterial) {
            child.material.metalness = 0.5
            child.material.roughness = 0.3
            child.material.envMapIntensity = 1.5
            child.material.needsUpdate = true
            child.material.side = THREE.FrontSide // Use front side only
            child.material.depthWrite = true // Ensure proper depth writing
            child.material.depthTest = true // Ensure proper depth testing
            // Force fully opaque to ensure arms/hands are visible
            child.material.transparent = false
            child.material.opacity = 1.0
            child.material.polygonOffset = false
            child.material.flatShading = false
          }
        }
      }

      // Check for SkinnedMesh which is used for rigged models (like hands)
      if (child instanceof THREE.SkinnedMesh) {
        // SkeletonUtils.clone() handles skeleton binding automatically
        // Just ensure visibility settings are correct
        child.visible = true
        child.frustumCulled = false

      }
    })
    
    return clonedScene
  }, [gltfScene])

  // Initialize animation mixer and actions
  useEffect(() => {
    if (!model || !animations.length) return

    const mixer = new AnimationMixer(model)
    mixerRef.current = mixer

    // Create actions for each animation
    const actions: { [key: string]: AnimationAction } = {}
    
    animations.forEach((clip: THREE.AnimationClip) => {
      const action = mixer.clipAction(clip)
      actions[clip.name] = action
      
      // Set up different loop modes for different animations
      if (clip.name.toLowerCase().includes('idle')) {
        action.setLoop(LoopRepeat, Infinity)
      } else {
        action.setLoop(LoopOnce, 1)
        action.clampWhenFinished = true
      }
    })

    actionsRef.current = actions

    // Start with idle animation if available
    const idleAction = actions['Idle'] || actions['idle'] || Object.values(actions)[0]
    if (idleAction) {
      idleAction.play()
      currentActionRef.current = idleAction.getClip().name
    }

    return () => {
      mixer.stopAllAction()
      mixerRef.current = null
    }
  }, [model, animations])

  // Handle animation state changes
  useEffect(() => {
    if (!mixerRef.current || !Object.keys(actionsRef.current).length) return

    const actions = actionsRef.current
    const currentAction = currentActionRef.current

    // Map animation states to actual animation names
    const animationMap: { [key: string]: string[] } = {
      idle: ['Idle', 'idle', 'Standing Idle', 'standing_idle'],
      walking: ['Walking', 'walking', 'Walk', 'walk'],
      running: ['Running', 'running', 'Run', 'run'],
      celebrating: ['Dance', 'dance', 'Victory', 'victory', 'Celebrate', 'celebrate', 'Jump', 'jump'],
      thinking: ['Thinking', 'thinking', 'Idle', 'idle'],
      death: ['Death', 'death', 'Falling', 'falling', 'Idle', 'idle']
    }

    // Find the best matching animation
    let targetAnimation = ''
    const possibleAnimations = animationMap[animationState] || ['Idle']
    
    for (const animName of possibleAnimations) {
      if (actions[animName]) {
        targetAnimation = animName
        break
      }
    }

    // If no specific animation found, use the first available one
    if (!targetAnimation && Object.keys(actions).length > 0) {
      targetAnimation = Object.keys(actions)[0]
    }

    // Switch animation if different from current
    if (targetAnimation && targetAnimation !== currentAction) {
      const currentActionObj = actions[currentAction]
      const targetActionObj = actions[targetAnimation]

      if (currentActionObj && targetActionObj) {
        // Smooth transition between animations
        currentActionObj.fadeOut(0.3)
        targetActionObj.reset().fadeIn(0.3).play()
        currentActionRef.current = targetAnimation
      }
    }
  }, [animationState])

  // Animation loop - cycles through walking, wave, and jump
  useFrame((state, delta) => {
    if (mixerRef.current) {
      mixerRef.current.update(delta)
    }

    if (!groupRef.current) return

    const actions = actionsRef.current
    const cycleTime = state.clock.elapsedTime % 3 // 3 second cycle

    // Handle death animation state
    if (animationState === 'death') {
      const deathAction = actions['Death'] || actions['death'] || actions['Falling'] || actions['falling'] || actions['Idle']

      if (deathAction && currentActionRef.current !== deathAction.getClip().name) {
        const currentAction = actions[currentActionRef.current]
        if (currentAction) currentAction.fadeOut(0.3)
        deathAction.reset().fadeIn(0.3).play()
        deathAction.setLoop(LoopOnce, 1)
        deathAction.clampWhenFinished = true
        currentActionRef.current = deathAction.getClip().name
      }

      // Fall down animation
      groupRef.current.rotation.x = Math.min(state.clock.elapsedTime * 0.5, Math.PI / 2)
      groupRef.current.position.y = Math.max(0.5 - state.clock.elapsedTime * 0.5, -1)
      return
    }

    // Reset rotation and position when coming back alive
    groupRef.current.rotation.x = 0
    groupRef.current.rotation.y = 0
    groupRef.current.position.x = 0
    groupRef.current.position.z = 0

    // Handle walking cycle with wave and dance
    if (animationState === 'walking') {
      let targetAction: AnimationAction | null = null
      let targetName = ''

      // Cycle: walking (0-1s) -> wave (1-2s) -> dance (2-3s)
      if (cycleTime < 1) {
        // Walking phase
        const walkAction = actions['Walking'] || actions['walking'] || actions['Walk'] || actions['walk']
        if (walkAction) {
          targetAction = walkAction
          targetName = 'walking'
          groupRef.current.position.y = Math.abs(Math.sin(state.clock.elapsedTime * 2)) * 0.08
        }
      } else if (cycleTime < 2) {
        // Wave phase
        const waveAction = actions['Wave'] || actions['wave'] || actions['ThumbsUp'] || actions['thumbsup']
        if (waveAction) {
          targetAction = waveAction
          targetName = 'wave'
          groupRef.current.position.y = 0
        }
      } else {
        // Dance phase
        const danceAction = actions['Dance'] || actions['dance'] || actions['Victory'] || actions['victory']
        if (danceAction) {
          targetAction = danceAction
          targetName = 'dance'
          groupRef.current.position.y = 0
        }
      }

      // Switch animation if needed
      if (targetAction && currentActionRef.current !== targetAction.getClip().name) {
        const currentAction = actions[currentActionRef.current]
        if (currentAction) currentAction.fadeOut(0.2)
        targetAction.reset().fadeIn(0.2).play()

        if (targetName === 'walking') {
          targetAction.setLoop(LoopRepeat, Infinity)
        } else {
          targetAction.setLoop(LoopRepeat, Infinity) // Keep all looping for smooth transitions
        }

        currentActionRef.current = targetAction.getClip().name
      }
    }
  })

  return (
    <group ref={groupRef} position={[0, 0.5, 0]}>
      <primitive object={model} />
    </group>
  )
}

export default AdvancedRobotCharacter