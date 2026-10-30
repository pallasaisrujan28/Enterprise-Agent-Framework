'use client'

import React from 'react'
import { motion } from 'framer-motion'

interface Session {
  session_id: string
  created_at: string
  persona_count: number
  generation_method: string
}

interface SessionSelectorProps {
  sessions: Session[]
  selectedSession: string | null
  onSessionSelect: (sessionId: string) => void
  onSessionDelete?: (sessionId: string) => void
}

export const SessionSelector: React.FC<SessionSelectorProps> = ({
  sessions,
  selectedSession,
  onSessionSelect,
  onSessionDelete
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getMethodColor = (method: string) => {
    switch (method.toLowerCase()) {
      case 'hybrid_advanced':
        return 'bg-blue-500'
      case 'llm_only':
        return 'bg-green-500'
      case 'rule_based':
        return 'bg-orange-500'
      default:
        return 'bg-gray-500'
    }
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-300">No sessions found</h3>
        <p className="mt-1 text-sm text-gray-400">
          Generate some personas first to see analysis options.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Select Generation Session
      </label>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {sessions.map((session, index) => (
          <motion.div
            key={session.session_id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className={`
              relative rounded-lg border p-4 transition-all duration-200
              ${
                selectedSession === session.session_id
                  ? 'border-blue-500 bg-blue-500/10 ring-2 ring-blue-500/20'
                  : 'border-gray-600 bg-gray-700/50 hover:border-gray-500 hover:bg-gray-700'
              }
            `}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1 cursor-pointer" onClick={() => onSessionSelect(session.session_id)}>
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className={`w-3 h-3 rounded-full ${getMethodColor(session.generation_method)}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      Session {session.session_id.slice(0, 8)}...
                    </p>
                    <p className="text-xs text-gray-400">
                      {formatDate(session.created_at)}
                    </p>
                  </div>
                </div>
                <div className="mt-2 flex items-center space-x-4 text-xs text-gray-400">
                  <span className="flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    {session.persona_count} personas
                  </span>
                  <span className="flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {session.generation_method}
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {selectedSession === session.session_id && (
                  <div className="flex-shrink-0">
                    <svg className="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
                {onSessionDelete && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (window.confirm(`Are you sure you want to delete this session? This action cannot be undone.`)) {
                        onSessionDelete(session.session_id)
                      }
                    }}
                    className="flex-shrink-0 p-1 text-gray-400 hover:text-red-400 transition-colors duration-200"
                    title="Delete session"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}