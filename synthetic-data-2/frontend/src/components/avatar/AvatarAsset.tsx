'use client';

import { useGLTF } from '@react-three/drei';
import { useEffect } from 'react';
import { SkinnedMesh, Skeleton, Color } from 'three';

interface AvatarAssetProps {
  categoryName: string;
  url: string;
  skeleton?: Skeleton;
  color?: string;
}

export function AvatarAsset({ categoryName, url, skeleton, color }: AvatarAssetProps) {
  const { scene } = useGLTF(url);

  useEffect(() => {
    if (!scene) return;

    scene.traverse((child) => {
      if (child instanceof SkinnedMesh) {
        child.frustumCulled = false;
        child.castShadow = true;
        child.receiveShadow = true;
        
        if (skeleton) {
          child.skeleton = skeleton;
        }
        
        if (color && child.material) {
          // Apply color to the material
          if (Array.isArray(child.material)) {
            child.material.forEach((mat) => {
              if ('color' in mat) {
                mat.color = new Color(color);
              }
            });
          } else if ('color' in child.material) {
            child.material.color = new Color(color);
          }
        }
      }
    });
  }, [scene, skeleton, color]);

  return <primitive object={scene} />;
}