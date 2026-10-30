'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Send,
  Image as ImageIcon,
  X,
  Loader2,
  User,
  Maximize2,
  Minimize2
} from 'lucide-react'

interface Persona {
  persona_uuid: string
  segment_name?: string
  segment?: string
  campaign_context?: string
  narrative_profile?: string
  demographic_info?: any
  [key: string]: any
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  hasMedia?: boolean
  mediaUrl?: string
  timestamp: Date
}

interface IndividualPersonaChatProps {
  open: boolean
  onClose: () => void
  persona: Persona
  mode?: 'dialog' | 'inline' // Can open as dialog or inline in same window
}

export const IndividualPersonaChat: React.FC<IndividualPersonaChatProps> = ({
  open,
  onClose,
  persona,
  mode = 'dialog'
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [mediaFile, setMediaFile] = useState<File | null>(null)
  const [mediaPreview, setMediaPreview] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isMaximized, setIsMaximized] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Prevent focus loss on re-render
  useEffect(() => {
    if (open && textareaRef.current) {
      const timer = setTimeout(() => {
        textareaRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [open])

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // Handle media file selection
  const handleMediaSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setMediaFile(file)
      
      const reader = new FileReader()
      reader.onloadend = () => {
        setMediaPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const clearMedia = () => {
    setMediaFile(null)
    setMediaPreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const sendMessage = useCallback(async () => {
    if (!userMessage.trim() && !mediaFile) return

    setIsLoading(true)

    // Add user message
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      hasMedia: !!mediaFile,
      mediaUrl: mediaPreview || undefined,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMsg])
    
    // Clear input
    const messageToSend = userMessage
    const fileToSend = mediaFile
    setUserMessage('')
    clearMedia()

    try {
      // Send to backend
      const formData = new FormData()
      formData.append('persona_uuid', persona.persona_uuid)
      formData.append('user_message', messageToSend)
      if (fileToSend) {
        formData.append('media_file', fileToSend)
      }

      const response = await fetch('http://localhost:8010/api/audience/chat-with-persona-enhanced', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()

      if (data.success) {
        const personaMsg: ChatMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date()
        }
        
        setMessages(prev => [...prev, personaMsg])
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }, [userMessage, mediaFile, mediaPreview, persona.persona_uuid])

  // Memoized handler to prevent unnecessary re-renders
  const handleMessageChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUserMessage(e.target.value)
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }, [sendMessage])

  const ChatContent = () => (
    <>
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-lg">
              {persona.segment_name?.charAt(0) || 'P'}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">
                {persona.segment_name || persona.segment || 'Persona'}
              </h3>
              <p className="text-sm text-slate-400">
                {persona.campaign_context || 'Chat with this persona'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {mode === 'dialog' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMaximized(!isMaximized)}
              >
                {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </Button>
            )}
          </div>
        </div>

        {/* Persona Info */}
        <div className="mt-3 p-3 bg-slate-800/50 rounded-lg">
          <p className="text-xs text-slate-300 line-clamp-2">
            {persona.narrative_profile?.substring(0, 200)}...
          </p>
        </div>
      </div>

      {/* Messages */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-6 space-y-4"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <User className="w-16 h-16 text-slate-600 mb-4" />
            <h3 className="text-lg font-semibold text-slate-300 mb-2">
              Start your 1-on-1 conversation
            </h3>
            <p className="text-sm text-slate-500 max-w-md">
              Ask questions, share media, and get personalized feedback from this persona
            </p>
          </div>
        )}

        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`flex gap-3 ${
                message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              {/* Avatar */}
              {message.role === 'assistant' && (
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold">
                    {persona.segment_name?.charAt(0) || 'P'}
                  </div>
                </div>
              )}

              {/* Message Content */}
              <div className={`flex-1 max-w-2xl ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-100'
                  }`}
                >
                  {message.hasMedia && message.mediaUrl && (
                    <div className="mb-2 rounded-lg overflow-hidden">
                      <img 
                        src={message.mediaUrl} 
                        alt="Uploaded content" 
                        className="max-w-full h-auto max-h-64 object-contain"
                      />
                    </div>
                  )}
                  
                  {/* Markdown rendering for assistant responses, plain text for user */}
                  {message.role === 'assistant' ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({node, ...props}) => <p className="text-sm mb-2 last:mb-0" {...props} />,
                          ul: ({node, ...props}) => <ul className="text-sm list-disc ml-4 mb-2" {...props} />,
                          ol: ({node, ...props}) => <ol className="text-sm list-decimal ml-4 mb-2" {...props} />,
                          li: ({node, ...props}) => <li className="text-sm mb-1" {...props} />,
                          strong: ({node, ...props}) => <strong className="font-bold text-white" {...props} />,
                          em: ({node, ...props}) => <em className="italic" {...props} />,
                          code: ({node, ...props}) => <code className="bg-slate-700 px-1 py-0.5 rounded text-xs" {...props} />,
                          blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-slate-600 pl-3 italic text-slate-300" {...props} />
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}
                  
                  <p className="text-xs opacity-60 mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <div className="flex items-center gap-2 text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Persona is typing...</span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-white/10 p-4">
        {/* Media Preview */}
        {mediaPreview && (
          <div className="mb-3 relative inline-block">
            <img 
              src={mediaPreview} 
              alt="Preview" 
              className="max-h-32 rounded-lg"
            />
            <button
              onClick={clearMedia}
              className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full hover:bg-red-600"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        )}

        {/* Input */}
        <div className="flex items-end gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleMediaSelect}
            accept="image/*,video/*"
            className="hidden"
          />
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="flex-shrink-0"
          >
            <ImageIcon className="w-5 h-5" />
          </Button>

          <textarea
            ref={textareaRef}
            value={userMessage}
            onChange={handleMessageChange}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 bg-slate-800 border border-white/10 rounded-lg px-4 py-3 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={isLoading}
            autoComplete="off"
          />

          <Button
            onClick={sendMessage}
            disabled={isLoading || (!userMessage.trim() && !mediaFile)}
            className="flex-shrink-0"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </>
  )

  if (mode === 'inline') {
    // Render inline (same window)
    return (
      <div className="flex flex-col h-full bg-slate-900">
        <ChatContent />
      </div>
    )
  }

  // Render as dialog (popup)
  return (
    <Dialog open={open} onOpenChange={onClose} modal={false}>
      <DialogContent
        className={`p-0 gap-0 bg-slate-900 text-white ${isMaximized ? 'max-w-7xl h-[90vh]' : 'max-w-3xl h-[70vh]'}`}
        onOpenAutoFocus={(e) => e.preventDefault()}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DialogTitle className="sr-only">
          Chat with {persona?.segment_name || persona?.segment || 'Persona'}
        </DialogTitle>
        <div className="flex flex-col h-full">
          <ChatContent />
        </div>
      </DialogContent>
    </Dialog>
  )
}
