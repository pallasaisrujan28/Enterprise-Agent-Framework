'use client';

import { useThree } from '@react-three/fiber';
import { useEffect } from 'react';

interface AvatarCameraManagerProps {
  loading: boolean;
}

export function AvatarCameraManager({ loading }: AvatarCameraManagerProps) {
  const { camera } = useThree();

  useEffect(() => {
    if (loading) {
      // Zoom out when loading
      camera.position.set(0, 0, 8);
    } else {
      // Normal position when loaded
      camera.position.set(0, 0, 5);
    }
    camera.lookAt(0, 0, 0);
  }, [camera, loading]);

  return null;
}