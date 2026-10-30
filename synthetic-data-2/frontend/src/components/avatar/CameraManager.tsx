'use client'

import { CameraControls } from "@react-three/drei"
import { useEffect, useRef } from "react"
import { UI_MODES, useAvatarConfiguratorStore } from "@/store/avatarConfiguratorStore"

export const START_CAMERA_POSITION = [500, 10, 1000] as const
export const DEFAULT_CAMERA_POSITION = [-1, 1, 8] as const
export const DEFAULT_CAMERA_TARGET = [0, 0, 0] as const

interface CameraManagerProps {
  loading: boolean
}

export const CameraManager = ({ loading }: CameraManagerProps) => {
  const controls = useRef<CameraControls>(null)
  const currentCategory = useAvatarConfiguratorStore(
    (state) => state.currentCategory
  )
  const initialLoading = useAvatarConfiguratorStore((state) => state.loading)
  const mode = useAvatarConfiguratorStore((state) => state.mode)

  useEffect(() => {
    if (!controls.current) return
    
    if (initialLoading) {
      controls.current.setLookAt(
        ...START_CAMERA_POSITION,
        ...DEFAULT_CAMERA_TARGET
      )
    } else {
      // Use default camera position for all categories
      controls.current.setLookAt(
        ...DEFAULT_CAMERA_POSITION,
        ...DEFAULT_CAMERA_TARGET,
        true
      )
    }
  }, [currentCategory, mode, initialLoading, loading])

  return (
    <CameraControls
      ref={controls}
      minPolarAngle={Math.PI / 4}
      maxPolarAngle={Math.PI / 2}
      minDistance={3}
      maxDistance={12}
    />
  )
}