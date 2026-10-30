import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  }

  return (
    <motion.div
      className={cn(
        'border-2 border-gray-300 border-t-blue-600 rounded-full',
        sizeClasses[size],
        className
      )}
      animate={{ rotate: 360 }}
      transition={{
        duration: 1,
        repeat: Infinity,
        ease: 'linear'
      }}
    />
  )
}

interface LoadingDotsProps {
  className?: string
}

export const LoadingDots: React.FC<LoadingDotsProps> = ({ className }) => {
  return (
    <div className={cn('flex space-x-1', className)}>
      {[0, 1, 2].map((index) => (
        <motion.div
          key={index}
          className="w-2 h-2 bg-blue-600 rounded-full"
          animate={{
            y: [0, -10, 0],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            delay: index * 0.1
          }}
        />
      ))}
    </div>
  )
}

interface LoadingPulseProps {
  className?: string
}

export const LoadingPulse: React.FC<LoadingPulseProps> = ({ className }) => {
  return (
    <motion.div
      className={cn(
        'w-16 h-16 bg-blue-600 rounded-full',
        className
      )}
      animate={{
        scale: [1, 1.2, 1],
        opacity: [0.7, 1, 0.7]
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: 'easeInOut'
      }}
    />
  )
}

interface LoadingSkeletonProps {
  className?: string
  lines?: number
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ 
  className, 
  lines = 3 
}) => {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <motion.div
          key={index}
          className="h-4 bg-gray-200 rounded animate-pulse"
          style={{ width: `${Math.random() * 40 + 60}%` }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: index * 0.1 }}
        />
      ))}
    </div>
  )
}