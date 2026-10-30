'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/loading'
import { cn } from '@/lib/utils'

const LandingPage = () => {
  const router = useRouter()
  const [isLogin, setIsLogin] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: ''
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    // Bypass authentication - accept any email and password
    // Basic validation: just check if email and password are not empty
    if (!formData.email.trim() || !formData.password.trim()) {
      alert('Please enter both email and password')
      setIsLoading(false)
      return
    }
    
    if (!isLogin && formData.password !== formData.confirmPassword) {
      alert('Passwords do not match')
      setIsLoading(false)
      return
    }
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    // Store user info in localStorage for session management
    localStorage.setItem('user', JSON.stringify({
      email: formData.email,
      name: formData.name || formData.email.split('@')[0],
      isAuthenticated: true
    }))
    
    setIsLoading(false)
    // Redirect to dashboard
    router.push('/dashboard')
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Section - 65% */}
      <motion.div 
        className="w-[65%] relative overflow-hidden"
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        {/* Background Image */}
        <div className="absolute inset-0">
          {/* Background image */}
          <div 
            className="w-full h-full bg-cover bg-center bg-no-repeat"
            style={{
              backgroundImage: "url('/images/Reply_Front_Page.png')"
            }}
          />
          {/* Overlay for better text readability */}
          <div className="absolute inset-0 bg-black/20" />
        </div>
        
        {/* Content Overlay */}
        <div className="relative z-10 h-full flex flex-col justify-center px-16 text-white">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <h1 className="text-7xl font-bold mb-8 leading-tight bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent drop-shadow-lg">
              Synthetic Persona
              <br />
              <span className="text-blue-300">Generation Platform</span>
            </h1>
            
            <motion.p 
              className="text-2xl mb-8 max-w-2xl leading-relaxed opacity-95 drop-shadow-md"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.8 }}
            >
              Create realistic, AI-generated personas from text descriptions, transform existing personas, and generate detailed character profiles for research, marketing, and content creation.
            </motion.p>
            
            <motion.div
                className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8, duration: 0.8 }}
              >
                <motion.div 
                  className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-lg mb-4 flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <h3 className="text-white font-bold text-lg mb-2">Persona Generator</h3>
                  <p className="text-white/80 text-sm">Create detailed synthetic personas with customizable demographics, traits, and backgrounds</p>
                </motion.div>
                
                <motion.div 
                  className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-lg mb-4 flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-white font-bold text-lg mb-2">Text-to-Persona</h3>
                  <p className="text-white/80 text-sm">Transform written descriptions into comprehensive persona profiles using AI</p>
                </motion.div>
                
                <motion.div 
                  className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="w-12 h-12 bg-gradient-to-br from-violet-400 to-purple-500 rounded-lg mb-4 flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                  </div>
                  <h3 className="text-white font-bold text-lg mb-2">Persona-to-Persona</h3>
                  <p className="text-white/80 text-sm">Transform and evolve existing personas into new variations and character types</p>
                </motion.div>
              </motion.div>
          </motion.div>
        </div>
      </motion.div>

      {/* Right Section - 35% */}
      <motion.div 
        className="w-[35%] bg-gradient-to-br from-gray-50 to-gray-100 flex flex-col justify-center px-8"
        initial={{ opacity: 0, x: 50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
      >
        <div className="max-w-md mx-auto w-full">
          {/* Auth Card */}
          <div className="bg-white/90 backdrop-blur-sm border-0 shadow-2xl rounded-xl p-8">
            {/* Logo */}
            <motion.div 
              className="text-center mb-8"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5, duration: 0.6 }}
            >
              {/* Logo */}
              <img 
                src="/images/Reply_Logo.png" 
                alt="Reply Logo" 
                className="mx-auto mb-4 w-32 h-auto drop-shadow-lg"
              />
              <h2 className="text-2xl font-bold text-gray-800">
                {isLogin ? 'Welcome Back' : 'Join Us'}
              </h2>
              <p className="text-gray-600 mt-2">
                {isLogin ? 'Sign in to your account' : 'Create your account'}
              </p>
            </motion.div>

          {/* Auth Form */}
          <motion.form 
            onSubmit={handleSubmit}
            className="space-y-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.6 }}
          >
            {!isLogin && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-500 text-black"
                  placeholder="Enter your full name"
                  required={!isLogin}
                />
              </motion.div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-500 text-black"
                placeholder="Enter your email"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-500 text-black"
                placeholder="Enter your password"
                required
              />
            </div>
            
            {!isLogin && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confirm Password
                </label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-500 text-black"
                  placeholder="Confirm your password"
                  required={!isLogin}
                />
              </motion.div>
            )}
            
            <Button
              type="submit"
              variant="gradient"
              size="lg"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <LoadingSpinner size="sm" className="mr-2" />
                  {isLogin ? 'Signing In...' : 'Creating Account...'}
                </div>
              ) : (
                isLogin ? 'Sign In' : 'Create Account'
              )}
            </Button>
          </motion.form>

            {/* Toggle Auth Mode */}
            <motion.div 
              className="text-center mt-6"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1, duration: 0.6 }}
            >
              <p className="text-gray-600">
                {isLogin ? "Don't have an account?" : "Already have an account?"}
              </p>
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="text-blue-600 hover:text-blue-700 font-medium mt-1 transition-colors duration-200"
              >
                {isLogin ? 'Sign Up' : 'Sign In'}
              </button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

export default LandingPage
