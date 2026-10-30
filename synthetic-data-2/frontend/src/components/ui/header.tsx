'use client'

import React from 'react'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  title: string
  subtitle?: string
  user?: any
  sidebarOpen: boolean
  onToggleSidebar: () => void
  variant?: 'light' | 'dark'
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  user,
  sidebarOpen,
  onToggleSidebar,
  variant = 'light'
}) => {
  const router = useRouter()

  const isLightVariant = variant === 'light'
  
  const headerClasses = isLightVariant
    ? "bg-gradient-to-r from-white via-gray-50 to-white backdrop-blur-xl border-b border-gray-200/30 shadow-sm flex-shrink-0"
    : "bg-gray-800 shadow-lg border-b border-gray-700"

  const textClasses = isLightVariant
    ? "text-gray-900"
    : "text-white"

  const buttonClasses = isLightVariant
    ? "lg:hidden p-3 rounded-2xl bg-white/60 hover:bg-white/80 shadow-sm border border-gray-200/50 transition-all duration-300 hover:scale-105"
    : "p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 lg:hidden"

  const userTextClasses = isLightVariant
    ? "text-gray-900"
    : "text-gray-300"

  const getUserInitials = () => {
    if (!user?.name) return 'U'
    return user.name.split(' ').map((n: string) => n[0]).join('').toUpperCase()
  }

  return (
    <header className={headerClasses}>
      <div className={isLightVariant ? "px-6 py-5" : "max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8"}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <button
              onClick={onToggleSidebar}
              className={buttonClasses}
            >
              <svg className={`w-5 h-5 ${isLightVariant ? 'text-gray-700' : 'text-current'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="relative">
              {isLightVariant ? (
                <>
                  <h1 className="text-3xl font-extralight text-gray-900 tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                    {title}
                  </h1>
                  {subtitle && (
                    <p className="text-sm text-gray-500 font-medium mt-1">{subtitle}</p>
                  )}
                  <div className="absolute -bottom-1 left-0 w-12 h-0.5 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"></div>
                </>
              ) : (
                <h1 className={`ml-4 text-2xl font-bold ${textClasses}`}>
                  {title}
                </h1>
              )}
            </div>
          </div>
          
          {/* Center Logo - Only for light variant */}
          {isLightVariant && (
            <div className="flex-1 flex justify-center items-center">
              <img
                src="/images/Reply_Logo.png"
                alt="Reply Logo"
                className="h-12 opacity-90 hover:opacity-100 transition-opacity duration-200"
              />
            </div>
          )}
          
          {/* User Profile Section */}
          <div className="flex items-center space-x-4">
            {user && (
              <div className={`text-right hidden sm:block ${isLightVariant ? '' : 'text-sm'}`}>
                {isLightVariant ? (
                  <>
                    <p className="text-sm font-semibold text-gray-900">{user.name}</p>
                    <p className="text-xs text-gray-500 font-medium">{user.email}</p>
                  </>
                ) : (
                  <span className={userTextClasses}>
                    Welcome, {user.name || 'User'}
                  </span>
                )}
              </div>
            )}
            <div className="relative">
              {isLightVariant ? (
                <>
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg ring-2 ring-white/50">
                    <span className="text-white font-bold text-sm">
                      {getUserInitials()}
                    </span>
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white shadow-sm"></div>
                </>
              ) : (
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-white">
                    {getUserInitials()}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header