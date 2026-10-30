'use client'

import { useGLTF } from "@react-three/drei"
import { useEffect, useMemo } from "react"
import { useAvatarConfiguratorStore } from "@/store/avatarConfiguratorStore"
import { Mesh, SkinnedMesh } from "three"

interface AssetProps {
  url: string
  categoryName: string
  skeleton: any
}

export const Asset = ({ url, categoryName, skeleton }: AssetProps) => {
  const { scene } = useGLTF(url)

  const customization = useAvatarConfiguratorStore((state) => state.customization)
  const lockedGroups = useAvatarConfiguratorStore((state) => state.lockedGroups)

  const assetColor = customization[categoryName]?.color

  const skin = useAvatarConfiguratorStore((state) => state.skin)

  useEffect(() => {
    scene.traverse((child) => {
      if ((child as Mesh).isMesh) {
        const mesh = child as Mesh
        if (Array.isArray(mesh.material)) {
          mesh.material.forEach((material) => {
            if (material.name?.includes("Color_")) {
              material.color.set(assetColor)
            }
          })
        } else if (mesh.material?.name?.includes("Color_")) {
          mesh.material.color.set(assetColor)
        }
      }
    })
  }, [assetColor, scene])

  const attachedItems = useMemo(() => {
    const items: any[] = []
    scene.traverse((child) => {
      if ((child as Mesh).isMesh) {
        const mesh = child as SkinnedMesh
        items.push({
          geometry: mesh.geometry,
          material: Array.isArray(mesh.material)
            ? mesh.material.map((mat) => mat.name?.includes("Skin_") ? skin : mat)
            : mesh.material?.name?.includes("Skin_") ? skin : mesh.material,
          morphTargetDictionary: mesh.morphTargetDictionary,
          morphTargetInfluences: mesh.morphTargetInfluences,
        })
      }
    })
    return items
  }, [scene, skin])

  if (lockedGroups[categoryName]) {
    return null
  }

  return (
    <>
      {attachedItems.map((item, index) => (
        <skinnedMesh
          key={index}
          geometry={item.geometry}
          material={item.material}
          skeleton={skeleton}
          morphTargetDictionary={item.morphTargetDictionary}
          morphTargetInfluences={item.morphTargetInfluences}
          castShadow
          receiveShadow
        />
      ))}
    </>
  )
}