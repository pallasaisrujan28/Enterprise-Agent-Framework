'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/ui/sidebar'
import { Header } from '@/components/ui/header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { NewPersonaAnalyticsDashboard } from '@/components/persona/NewPersonaAnalyticsDashboard'

const PersonaAnalysis = () => {
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    // Check for user authentication in localStorage
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    } else {
      // Redirect to login if no user data found
      router.push('/')
    }
  }, [router])

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          title="Persona Analysis Dashboard"
          user={user}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          variant="dark"
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-900">
          <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <NewPersonaAnalyticsDashboard />
            </motion.div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default PersonaAnalysis