'use client'

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/ui/sidebar'
import { Header } from '@/components/ui/header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const Dashboard = () => {
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
          title="Dashboard"
          user={user}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          variant="dark"
        />

        {/* Main Content Area */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-[#130f30]">
          <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
            {/* Page Header */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-8"
            >
              <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
              <p className="text-lg text-gray-400">Welcome back, {user.name}! Here's your overview.</p>
            </motion.div>

            <div>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="grid grid-cols-1 md:grid-cols-3 gap-6"
                >
                  {/* Quick Actions */}
                  <Card className="bg-white/10 backdrop-blur-md border-white/20 p-6 cursor-pointer hover:bg-white/20 transition-all"
                        onClick={() => router.push('/audience-generation')}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-14 h-14 rounded-xl bg-blue-500 flex items-center justify-center">
                        <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                      </div>
                    </div>
                    <h3 className="text-xl font-bold mb-2">Audience Generation</h3>
                    <p className="text-gray-400 text-sm">Create synthetic audience personas for your product</p>
                  </Card>

                  <Card className="bg-white/10 backdrop-blur-md border-white/20 p-6 cursor-pointer hover:bg-white/20 transition-all"
                        onClick={() => router.push('/synthetic-audience')}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-14 h-14 rounded-xl bg-purple-500 flex items-center justify-center">
                        <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                        </svg>
                      </div>
                    </div>
                    <h3 className="text-xl font-bold mb-2">Synthetic Audience Store</h3>
                    <p className="text-gray-400 text-sm">View and analyze your generated personas</p>
                  </Card>

                  <Card className="bg-white/10 backdrop-blur-md border-white/20 p-6 cursor-pointer hover:bg-white/20 transition-all"
                        onClick={() => router.push('/persona-generator')}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-14 h-14 rounded-xl bg-green-500 flex items-center justify-center">
                        <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                    </div>
                    <h3 className="text-xl font-bold mb-2">Persona Generator</h3>
                    <p className="text-gray-400 text-sm">Create detailed synthetic personas</p>
                  </Card>
                </motion.div>

                {/* Welcome Message */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  className="mt-8"
                >
                  <Card className="bg-white/10 backdrop-blur-md border-white/20 p-8">
                    <h2 className="text-2xl font-bold mb-4">Welcome to Synthetic Audience Platform</h2>
                    <p className="text-gray-300 mb-6 text-base">
                      Generate realistic, AI-powered synthetic personas for marketing research, product testing, and audience analysis.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                          <span className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center mr-2">
                            <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </span>
                          Features
                        </h3>
                        <ul className="space-y-3 text-gray-300 text-sm">
                          <li className="flex items-start">
                            <span className="text-blue-400 mr-3 mt-0.5">✓</span>
                            AI-powered trait selection based on your product
                          </li>
                          <li className="flex items-start">
                            <span className="text-blue-400 mr-3 mt-0.5">✓</span>
                            Statistical sampling for realistic distributions
                          </li>
                          <li className="flex items-start">
                            <span className="text-blue-400 mr-3 mt-0.5">✓</span>
                            LLM-generated persona narratives
                          </li>
                          <li className="flex items-start">
                            <span className="text-blue-400 mr-3 mt-0.5">✓</span>
                            Template-based audience evaluation
                          </li>
                          <li className="flex items-start">
                            <span className="text-blue-400 mr-3 mt-0.5">✓</span>
                            Memory-enabled chat with personas
                          </li>
                        </ul>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold mb-4 flex items-center">
                          <span className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center mr-2">
                            <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                          </span>
                          Getting Started
                        </h3>
                        <ol className="space-y-3 text-gray-300 text-sm">
                          <li className="flex items-start">
                            <span className="text-purple-400 mr-3 font-bold">1.</span>
                            <span>Click "Audience Generation" to create new personas</span>
                          </li>
                          <li className="flex items-start">
                            <span className="text-purple-400 mr-3 font-bold">2.</span>
                            <span>Describe your product and select target segment</span>
                          </li>
                          <li className="flex items-start">
                            <span className="text-purple-400 mr-3 font-bold">3.</span>
                            <span>Review and select relevant traits</span>
                          </li>
                          <li className="flex items-start">
                            <span className="text-purple-400 mr-3 font-bold">4.</span>
                            <span>Generate personas with AI narratives</span>
                          </li>
                          <li className="flex items-start">
                            <span className="text-purple-400 mr-3 font-bold">5.</span>
                            <span>Analyze results and chat with personas</span>
                          </li>
                        </ol>
                      </div>
                    </div>
                    <div className="mt-8">
                      <Button
                        onClick={() => router.push('/audience-generation')}
                        className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-6 py-3 rounded-xl transition-all"
                      >
                        Get Started →
                      </Button>
                    </div>
                  </Card>
                </motion.div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Dashboard
