'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Image from 'next/image'
import Link from 'next/link'
import { cn } from '@/lib/utils'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  currentPage?: string
}

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z" />
      </svg>
    )
  },
  {
    name: 'Audience Generation',
    href: '/audience-generation',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    )
  },
  {
    name: 'Synthetic Audience Store',
    href: '/synthetic-audience',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    )
  },
  {
    name: 'Persona Generator',
    href: '/persona-generator',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    )
  }
]

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onToggle, currentPage = 'dashboard' }) => {
  const [mounted, setMounted] = useState(false)
  const [isLargeScreen, setIsLargeScreen] = useState(false)

  useEffect(() => {
    setMounted(true)
    setIsLargeScreen(window.innerWidth >= 1024)
    
    const handleResize = () => {
      setIsLargeScreen(window.innerWidth >= 1024)
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <>
      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onToggle}
            className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        initial={false}
        animate={{ 
          x: mounted && isLargeScreen ? 0 : (isOpen ? 0 : -280)
        }}
        transition={{ type: "spring", damping: 25, stiffness: 200 }}
        className="fixed left-0 top-0 h-full w-72 bg-white shadow-2xl z-50 lg:relative lg:translate-x-0 lg:shadow-none lg:border-r lg:border-gray-200 lg:static lg:z-auto"
      >
        {/* Header with Logo */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Reply</h2>
                <p className="text-xs text-gray-500">Synthetic Personas</p>
              </div>
            </div>
            <button
              onClick={onToggle}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-2">
          {navigationItems.map((item, index) => {
            const isActive = currentPage === item.href.replace('/', '')
            return (
              <motion.div
                key={item.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                    isActive
                      ? "bg-blue-50 text-blue-700 border border-blue-200"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  <div className={cn(
                    "transition-colors duration-200",
                    isActive ? "text-blue-600" : "text-gray-400 group-hover:text-gray-600"
                  )}>
                    {item.icon}
                  </div>
                  <span className="font-medium">{item.name}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeIndicator"
                      className="ml-auto w-2 h-2 bg-blue-600 rounded-full"
                    />
                  )}
                </Link>
              </motion.div>
            )
          })}
        </nav>


      </motion.div>
    </>
  )
}

export default Sidebar