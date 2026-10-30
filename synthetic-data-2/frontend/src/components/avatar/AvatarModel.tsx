'use client';

import { useAnimations, useGLTF } from '@react-three/drei';
import { Suspense, useEffect, useRef } from 'react';
import { Group } from 'three';
import { useAvatarPersonaStore } from '../../store/avatarPersonaStore';
import { AvatarAsset } from './AvatarAsset';

// Define the avatar customization interface
interface AvatarCustomization {
  [key: string]: {
    asset?: {
      id: string;
      name: string;
    };
    color?: string;
  };
}

export function AvatarModel({ ...props }) {
  const group = useRef<Group>(null);
  const { nodes } = useGLTF('/models/Armature.glb');
  const { animations } = useGLTF('/models/Poses.glb');
  const { actions } = useAnimations(animations, group);
  
  // Get avatar customization from store
  const avatarCustomization = useAvatarPersonaStore((state) => state.avatarCustomization);
  const currentPose = useAvatarPersonaStore((state) => state.currentPose);
  
  // Use the pose from store
  const pose = currentPose;

  useEffect(() => {
    if (actions[pose]) {
      actions[pose]?.fadeIn(0.2).play();
      return () => {
        actions[pose]?.fadeOut(0.2).stop();
      };
    }
  }, [actions, pose]);

  return (
    <group ref={group} {...props} dispose={null}>
      <group name="Scene">
        <group name="Armature" rotation={[Math.PI / 2, 0, 0]} scale={0.01}>
          <primitive object={nodes.mixamorigHips} />
          {Object.keys(avatarCustomization).map(
            (key) =>
              avatarCustomization[key]?.asset && (
                <Suspense key={avatarCustomization[key]?.asset?.id}>
                  <AvatarAsset
                    categoryName={key}
                    url={`/models/${avatarCustomization[key]?.asset?.id}.glb`}
                    skeleton={(nodes as any).Plane?.skeleton}
                    color={avatarCustomization[key]?.color}
                  />
                </Suspense>
              )
          )}
        </group>
      </group>
    </group>
  );
}

// Preload the required models
useGLTF.preload('/models/Armature.glb');
useGLTF.preload('/models/Poses.glb');