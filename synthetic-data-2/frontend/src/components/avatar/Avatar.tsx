'use client'

import { NodeIO } from "@gltf-transform/core"
import { dedup, draco, prune, quantize } from "@gltf-transform/functions"
import { useAnimations, useGLTF } from "@react-three/drei"
import { Suspense, useEffect, useRef, memo, useMemo } from "react"
import { GLTFExporter } from "three-stdlib"
import { useAvatarConfiguratorStore } from "@/store/avatarConfiguratorStore"
import { Asset } from "./Asset"

interface AvatarProps {
  [key: string]: any
}

const AvatarComponent = ({ ...props }: AvatarProps) => {
  const group = useRef<THREE.Group>(null)
  const { nodes } = useGLTF("/models/Armature.glb")
  const { animations } = useGLTF("/models/Poses.glb")
  const customization = useAvatarConfiguratorStore((state) => state.customization)
  
  // Filter animations to remove tracks for missing bones to prevent PropertyBinding errors
  const filteredAnimations = useMemo(() => {
    return animations.map(animation => {
      const filteredTracks = animation.tracks.filter(track => {
        // Check if the target node exists in the model
        const targetName = track.name.split('.')[0]
        return nodes[targetName] !== undefined
      })
      
      // Create a new AnimationClip with filtered tracks
      const newClip = animation.clone()
      newClip.tracks = filteredTracks
      return newClip
    })
  }, [animations, nodes])
  
  const { actions } = useAnimations(filteredAnimations, group)
  const setDownload = useAvatarConfiguratorStore((state) => state.setDownload)

  const pose = useAvatarConfiguratorStore((state) => state.pose)

  useEffect(() => {
    function download() {
      const exporter = new GLTFExporter()
      exporter.parse(
        group.current,
        async function (result) {
          const io = new NodeIO()

          // Read.
          const document = await io.readBinary(new Uint8Array(result as ArrayBuffer)) // Uint8Array → Document
          await document.transform(
            // Remove unused nodes, textures, or other data.
            prune(),
            // Remove duplicate vertex or texture data, if any.
            dedup(),
            // Compress mesh geometry with Draco.
            draco(),
            // Quantize mesh geometry.
            quantize()
          )

          // Write.
          const glb = await io.writeBinary(document) // Document → Uint8Array

          save(
            new Blob([glb], { type: "application/octet-stream" }),
            `avatar_${+new Date()}.glb`
          )
        },
        function (error) {
          console.error(error)
        },
        { binary: true }
      )
    }

    const link = document.createElement("a")
    link.style.display = "none"
    document.body.appendChild(link) // Firefox workaround, see #6594

    function save(blob: Blob, filename: string) {
      link.href = URL.createObjectURL(blob)
      link.download = filename
      link.click()
    }
    setDownload(download)
  }, [setDownload])

  useEffect(() => {
    // Add error handling and performance optimization for pose animations
    try {
      if (actions[pose] && typeof actions[pose].fadeIn === 'function') {
        actions[pose].reset().fadeIn(0.2).play()
      }
    } catch (error) {
      console.warn('Animation pose error:', error)
    }
    
    return () => {
      try {
        if (actions[pose] && typeof actions[pose].fadeOut === 'function') {
          actions[pose].fadeOut(0.2).stop()
        }
      } catch (error) {
        console.warn('Animation cleanup error:', error)
      }
    }
  }, [actions, pose])

  return (
    <group ref={group} {...props} dispose={null}>
      <group name="Scene">
        <group name="Armature" rotation={[Math.PI / 2, 0, 0]} scale={0.01}>
          <primitive object={nodes.mixamorigHips} />
          {Object.keys(customization).map(
            (key) =>
              customization[key]?.asset && (
                <Suspense key={customization[key].asset.id}>
                  <Asset
                    categoryName={key}
                    url={`/models/${customization[key].asset.id}.glb`}
                    skeleton={(nodes.Plane as any)?.skeleton}
                  />
                </Suspense>
              )
          )}
        </group>
      </group>
    </group>
  )
}

// Memoize the Avatar component for better performance
export const Avatar = memo(AvatarComponent)
Avatar.displayName = 'Avatar'