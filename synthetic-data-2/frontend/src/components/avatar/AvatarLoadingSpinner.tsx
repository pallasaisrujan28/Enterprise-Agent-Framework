'use client';

import { Html } from '@react-three/drei';

interface AvatarLoadingSpinnerProps {
  loading: boolean;
}

export function AvatarLoadingSpinner({ loading }: AvatarLoadingSpinnerProps) {
  if (!loading) return null;

  return (
    <Html center>
      <div className="flex flex-col items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <p className="mt-4 text-sm text-gray-600">Loading Avatar...</p>
      </div>
    </Html>
  );
}