'use client'

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { 
  Send, 
  Image as ImageIcon, 
  Video, 
  Users, 
  X,
  MessageSquare,
  MessageCircle,
  Loader2,
  ChevronRight,
  BarChart3,
  TrendingUp,
  AlertCircle,
  Target,
  ThumbsUp,
  ThumbsDown,
  Paperclip,
  FileText,
  Upload
} from 'lucide-react'

interface Persona {
  persona_uuid: string
  segment_name: string
  campaign_context: string
  narrative_profile: string
  demographic_info: any
}

interface ChatMessage {
  id: string
  type: 'user' | 'persona' | 'asset'
  persona_uuid?: string
  persona_name?: string
  content: string
  hasMedia?: boolean
  mediaUrl?: string
  mediaType?: 'image' | 'video' | 'pdf'
  fileName?: string
  timestamp: Date
}

interface GroupChatDialogProps {
  open: boolean
  onClose: () => void
  audienceGroup: {
    group_name: string
    segment_name: string
    campaign_context: string
    persona_count: number
  }
  personas: Persona[]
  onPersonaClick: (persona: Persona) => void
}

export const GroupChatDialog: React.FC<GroupChatDialogProps> = ({
  open,
  onClose,
  audienceGroup,
  personas,
  onPersonaClick
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)  // NEW: Track conversation ID
  const [uploadedAssets, setUploadedAssets] = useState<Array<{
    id: string
    file: File
    preview: string
    type: 'image' | 'video' | 'pdf'
  }>>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showParticipants, setShowParticipants] = useState(true)
  
  // Insights Dashboard state
  const [showDashboard, setShowDashboard] = useState(false)
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false)
  
  const assetInputRef = useRef<HTMLInputElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const dashboardRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages])

  // Handle asset file selection (multiple files)
  const handleAssetUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      // Validate file type
      const fileType = file.type
      let assetType: 'image' | 'video' | 'pdf' | null = null
      
      if (fileType.startsWith('image/')) {
        assetType = 'image'
      } else if (fileType.startsWith('video/')) {
        assetType = 'video'
      } else if (fileType === 'application/pdf') {
        assetType = 'pdf'
      }

      if (!assetType) {
        alert(`File ${file.name} is not supported. Please upload images, videos, or PDFs only.`)
        return
      }

      // Create preview URL
      const reader = new FileReader()
      reader.onloadend = () => {
        const newAsset = {
          id: `${Date.now()}-${Math.random()}`,
          file,
          preview: reader.result as string,
          type: assetType!
        }
        
        setUploadedAssets(prev => [...prev, newAsset])
        
        // Add asset message to chat
        const assetMessage: ChatMessage = {
          id: newAsset.id,
          type: 'asset',
          content: `Uploaded ${assetType}: ${file.name}`,
          hasMedia: true,
          mediaUrl: reader.result as string,
          mediaType: assetType!,
          fileName: file.name,
          timestamp: new Date()
        }
        setMessages(prev => [...prev, assetMessage])
      }
      reader.readAsDataURL(file)
    })

    // Reset input
    if (assetInputRef.current) {
      assetInputRef.current.value = ''
    }
  }

  const removeAsset = (assetId: string) => {
    setUploadedAssets(prev => prev.filter(a => a.id !== assetId))
    setMessages(prev => prev.filter(m => m.id !== assetId))
  }

  const sendMessage = async () => {
    if (!userMessage.trim()) return

    setIsLoading(true)

    // Add user message to chat
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMsg])
    
    // Clear input and reset textarea height
    const messageToSend = userMessage
    setUserMessage('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      // Send to backend
      const formData = new FormData()
      // Use segment_name for the backend query, combine with campaign_context if available
      const groupIdentifier = audienceGroup.campaign_context 
        ? `${audienceGroup.segment_name}_${audienceGroup.campaign_context}`
        : audienceGroup.segment_name
      formData.append('audience_group', groupIdentifier)
      formData.append('user_message', messageToSend)
      
      // Include conversation_id if we have one (for shared memory continuity)
      if (conversationId) {
        formData.append('conversation_id', conversationId)
      } else {
      }
      
      // Include first asset as media_file (backend currently supports single file)
      if (uploadedAssets.length > 0) {
        formData.append('media_file', uploadedAssets[0].file)
      }


      const response = await fetch('http://localhost:8010/api/audience/chat-with-group', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()

      // Store conversation_id for shared memory continuity
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id)
      }

      // Add persona responses one by one (Teams-style)
      if (data.success && data.individual_responses) {
        // Simulate personas responding one-by-one with slight delays
        for (let i = 0; i < data.individual_responses.length; i++) {
          const personaResponse = data.individual_responses[i]
          
          // Find persona details
          const persona = personas.find(p => p.persona_uuid === personaResponse.persona_uuid)
          const personaName = persona 
            ? `${persona.segment_name} - Persona ${i + 1}`
            : `Persona ${i + 1}`

          await new Promise(resolve => setTimeout(resolve, 500 * (i + 1))) // Stagger responses
          
          const personaMsg: ChatMessage = {
            id: `${Date.now()}-${i}`,
            type: 'persona',
            persona_uuid: personaResponse.persona_uuid,
            persona_name: personaName,
            content: personaResponse.response,
            timestamp: new Date()
          }
          
          setMessages(prev => [...prev, personaMsg])
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      // Show error message in chat
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'persona',
        persona_name: 'System',
        content: 'Sorry, there was an error processing your message. Please try again.',
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // NEW: Generate Insights Dashboard
  const handleShowInsights = async () => {
    if (messages.length === 0) {
      alert('Have a conversation first to generate insights!')
      return
    }
    
    if (uploadedAssets.length === 0) {
      alert('Please upload at least one asset (image, video, or PDF) to analyze!')
      return
    }

    setIsLoadingDashboard(true)
    
    try {
      const formData = new FormData()
      // Use segment_name for consistency
      const groupIdentifier = audienceGroup.campaign_context 
        ? `${audienceGroup.segment_name}_${audienceGroup.campaign_context}`
        : audienceGroup.segment_name
      formData.append('audience_group', groupIdentifier)
      formData.append('campaign_context', audienceGroup.campaign_context)
      formData.append('campaign_goal', 'Drive awareness and sales')
      formData.append('conversation_history', JSON.stringify(messages))
      
      // Include all uploaded assets
      uploadedAssets.forEach((asset, index) => {
        formData.append(`assets`, asset.file)
      })
      
      const response = await fetch('http://localhost:8010/api/audience/generate-insights-dashboard', {
        method: 'POST',
        body: formData
      })
      
      const data = await response.json()
      
      if (data.success) {
        setDashboardData(data.dashboard)
        setShowDashboard(true)
        
        // Scroll to dashboard after it renders
        setTimeout(() => {
          dashboardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 300)
      } else {
        alert('Failed to generate insights')
      }
    } catch (error) {
      console.error('Error fetching insights:', error)
      alert('Error generating insights. Please try again.')
    } finally {
      setIsLoadingDashboard(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-7xl h-[85vh] p-0 gap-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border-slate-700">
        {/* Modern Header with Gradient */}
        <DialogHeader className="px-6 py-4 border-b border-slate-700/50 bg-gradient-to-r from-blue-900/20 to-purple-900/20 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/20">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div>
                <DialogTitle className="text-2xl font-bold text-white flex items-center gap-2">
                  {audienceGroup.segment_name}
                  <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 ml-2">
                    {personas.length} members
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-sm text-slate-300 mt-1">
                  {audienceGroup.campaign_context}
                </DialogDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Upload Assets Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => assetInputRef.current?.click()}
                className="border-blue-500/30 bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 hover:border-blue-400/50"
              >
                <Upload className="w-4 h-4 mr-2" />
                Assets
                {uploadedAssets.length > 0 && (
                  <Badge className="ml-2 bg-blue-600 text-white">
                    {uploadedAssets.length}
                  </Badge>
                )}
              </Button>
              <input
                ref={assetInputRef}
                type="file"
                accept="image/*,video/*,.pdf"
                multiple
                onChange={handleAssetUpload}
                className="hidden"
              />
              
              {/* Insights Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleShowInsights}
                disabled={isLoadingDashboard || messages.length === 0}
                className="border-purple-500/30 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 hover:border-purple-400/50"
              >
                {isLoadingDashboard ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Insights
                  </>
                )}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowParticipants(!showParticipants)}
                className="text-slate-300 hover:text-white hover:bg-slate-700/50"
              >
                <ChevronRight className={`w-5 h-5 transition-transform ${showParticipants ? 'rotate-90' : ''}`} />
              </Button>
            </div>
          </div>
        </DialogHeader>

        {/* Main Content */}
        <div className="flex flex-1 overflow-hidden bg-slate-900">
          {/* Chat Area */}
          <div className="flex-1 flex flex-col">
            {/* Messages */}
            <div 
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-6 space-y-4"
            >
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <MessageSquare className="w-16 h-16 text-slate-600 mb-4" />
                  <h3 className="text-lg font-semibold text-slate-300 mb-2">
                    Start the conversation
                  </h3>
                  <p className="text-sm text-slate-500 max-w-md">
                    Ask questions, share media, and get feedback from all {personas.length} personas in this group
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
                      message.type === 'user' ? 'flex-row-reverse' : 
                      message.type === 'asset' ? 'justify-center' : 'flex-row'
                    }`}
                  >
                    {/* Asset Message - Special Display */}
                    {message.type === 'asset' && (
                      <div className="w-full max-w-3xl">
                        <div className="bg-slate-800/50 border border-white/10 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              {message.mediaType === 'image' && <ImageIcon className="w-5 h-5 text-blue-400" />}
                              {message.mediaType === 'video' && <Video className="w-5 h-5 text-purple-400" />}
                              {message.mediaType === 'pdf' && <FileText className="w-5 h-5 text-red-400" />}
                              <div>
                                <p className="text-sm font-medium text-white">{message.fileName}</p>
                                <p className="text-xs text-slate-400">
                                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeAsset(message.id)}
                              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          
                          {/* Asset Preview */}
                          {message.mediaType === 'image' && message.mediaUrl && (
                            <div className="rounded-lg overflow-hidden bg-black/20">
                              <img 
                                src={message.mediaUrl} 
                                alt={message.fileName} 
                                className="w-full h-auto max-h-96 object-contain"
                              />
                            </div>
                          )}
                          
                          {message.mediaType === 'video' && message.mediaUrl && (
                            <div className="rounded-lg overflow-hidden bg-black/20">
                              <video 
                                src={message.mediaUrl} 
                                controls 
                                className="w-full h-auto max-h-96"
                              />
                            </div>
                          )}
                          
                          {message.mediaType === 'pdf' && (
                            <div className="bg-slate-700/30 rounded-lg p-8 text-center">
                              <FileText className="w-16 h-16 text-red-400 mx-auto mb-2" />
                              <p className="text-sm text-slate-300">PDF Document</p>
                              <p className="text-xs text-slate-500 mt-1">Available for persona analysis</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {/* Regular Messages */}
                    {message.type !== 'asset' && (
                      <>
                        {/* Avatar */}
                        {message.type === 'persona' && (
                          <div 
                            className="flex-shrink-0 cursor-pointer"
                            onClick={() => {
                              const persona = personas.find(p => p.persona_uuid === message.persona_uuid)
                              if (persona) {
                                onPersonaClick(persona)
                              }
                            }}
                          >
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-semibold">
                              {message.persona_name?.charAt(0) || 'P'}
                            </div>
                          </div>
                        )}

                        {/* Message Content */}
                        <div className={`flex-1 max-w-2xl ${message.type === 'user' ? 'flex justify-end' : ''}`}>
                          {message.type === 'persona' && (
                            <p className="text-xs text-slate-400 mb-1 ml-1">
                              {message.persona_name}
                            </p>
                          )}
                          
                          <div
                            className={`rounded-2xl px-4 py-3 ${
                              message.type === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-slate-800 text-slate-100'
                            }`}
                          >
                            {/* Markdown rendering for persona responses, plain text for user */}
                            {message.type === 'persona' ? (
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
                      </>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {isLoading && (
                <div className="flex items-center gap-2 text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Personas are responding...</span>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t border-white/10 p-4">
              {/* Input */}
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={userMessage}
                  onChange={(e) => {
                    setUserMessage(e.target.value)
                    // Auto-resize textarea
                    e.target.style.height = 'auto'
                    e.target.style.height = e.target.scrollHeight + 'px'
                  }}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 bg-slate-800 border border-white/10 rounded-lg px-4 py-3 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 overflow-hidden"
                  rows={1}
                  style={{ minHeight: '44px', maxHeight: '200px' }}
                  disabled={isLoading}
                />

                <Button
                  onClick={sendMessage}
                  disabled={isLoading || !userMessage.trim()}
                  className="flex-shrink-0"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>

          {/* Participants Sidebar (Teams-style) */}
          <AnimatePresence>
            {showParticipants && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 320, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="border-l border-slate-700/50 bg-gradient-to-b from-slate-800/50 to-slate-900/50 backdrop-blur-sm overflow-hidden"
              >
                <div className="p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                      Team Members
                    </h3>
                    <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-xs">
                      {personas.length}
                    </Badge>
                  </div>
                  
                  <div className="space-y-1">
                    {personas.map((persona, index) => {
                      const initials = persona.segment_name?.split(' ').map(w => w[0]).join('').slice(0, 2) || 'P'
                      const colors = [
                        'from-blue-500 to-cyan-500',
                        'from-purple-500 to-pink-500',
                        'from-green-500 to-emerald-500',
                        'from-orange-500 to-red-500',
                        'from-indigo-500 to-purple-500',
                        'from-pink-500 to-rose-500',
                      ]
                      const colorClass = colors[index % colors.length]
                      
                      return (
                        <motion.button
                          key={persona.persona_uuid}
                          onClick={() => onPersonaClick(persona)}
                          className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-700/50 transition-all duration-200 text-left group relative overflow-hidden"
                          whileHover={{ scale: 1.02, x: 4 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          {/* Hover gradient effect */}
                          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                          
                          {/* Avatar with status indicator */}
                          <div className="relative flex-shrink-0">
                            <div className={`w-11 h-11 rounded-full bg-gradient-to-br ${colorClass} flex items-center justify-center text-white font-bold text-sm shadow-lg`}>
                              {initials}
                            </div>
                            {/* Online status indicator */}
                            <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-slate-800 rounded-full" />
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-white truncate group-hover:text-blue-300 transition-colors">
                              {persona.segment_name}
                            </p>
                            <p className="text-xs text-slate-400 truncate">
                              Persona #{index + 1}
                            </p>
                          </div>
                          
                          {/* Chat icon on hover */}
                          <MessageCircle className="w-4 h-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </motion.button>
                      )
                    })}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* NEW: Insights Dashboard Section */}
        {showDashboard && dashboardData && (
          <div 
            ref={dashboardRef}
            className="border-t border-white/10 bg-slate-900 p-6 max-h-[60vh] overflow-y-auto"
          >
            <div className="max-w-6xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-6 h-6 text-blue-400" />
                    Marketing Insights Dashboard
                  </h3>
                  <p className="text-sm text-slate-400 mt-1">
                    Real-time analysis of {dashboardData.total_personas_analyzed} personas • {dashboardData.conversation_messages} messages analyzed
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowDashboard(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>

              {/* Key Metrics Row - Extended with new metrics */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div className="bg-slate-800 p-4 rounded-lg border border-blue-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Add to Cart Rate</p>
                    <TrendingUp className="w-4 h-4 text-blue-400" />
                  </div>
                  <p className="text-3xl font-bold text-blue-400">
                    {dashboardData.key_metrics?.add_to_cart_rate || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Purchase likelihood</p>
                </div>

                <div className="bg-slate-800 p-4 rounded-lg border border-green-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Purchase Intent</p>
                    <Target className="w-4 h-4 text-green-400" />
                  </div>
                  <p className="text-3xl font-bold text-green-400">
                    {dashboardData.key_metrics?.purchase_intent_score || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Conversion potential</p>
                </div>

                <div className="bg-slate-800 p-4 rounded-lg border border-purple-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Brand Affinity</p>
                    <ThumbsUp className="w-4 h-4 text-purple-400" />
                  </div>
                  <p className="text-3xl font-bold text-purple-400">
                    {dashboardData.key_metrics?.brand_affinity || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Brand sentiment</p>
                </div>

                <div className="bg-slate-800 p-4 rounded-lg border border-orange-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Net Promoter</p>
                    <Users className="w-4 h-4 text-orange-400" />
                  </div>
                  <p className="text-3xl font-bold text-orange-400">
                    {dashboardData.key_metrics?.net_promoter_score || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Would recommend</p>
                </div>
              </div>

              {/* NEW: Additional Value Metrics Row */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gradient-to-br from-cyan-900/40 to-cyan-800/20 p-4 rounded-lg border border-cyan-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Conversion Probability</p>
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                  </div>
                  <p className="text-2xl font-bold text-cyan-400">
                    {dashboardData.key_metrics?.conversion_probability || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Ready to buy now</p>
                </div>

                <div className="bg-gradient-to-br from-pink-900/40 to-pink-800/20 p-4 rounded-lg border border-pink-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Engagement Score</p>
                    <MessageCircle className="w-4 h-4 text-pink-400" />
                  </div>
                  <p className="text-2xl font-bold text-pink-400">
                    {dashboardData.key_metrics?.engagement_score || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Overall interest</p>
                </div>

                <div className="bg-gradient-to-br from-amber-900/40 to-amber-800/20 p-4 rounded-lg border border-amber-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Risk Score</p>
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                  </div>
                  <p className="text-2xl font-bold text-amber-400">
                    {dashboardData.key_metrics?.risk_score || 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Concerns identified</p>
                </div>

                <div className="bg-gradient-to-br from-emerald-900/40 to-emerald-800/20 p-4 rounded-lg border border-emerald-500/30">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-400">Market Readiness</p>
                    <Target className="w-4 h-4 text-emerald-400" />
                  </div>
                  <p className="text-2xl font-bold text-emerald-400">
                    {dashboardData.key_metrics?.market_readiness || 'N/A'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Campaign status</p>
                </div>
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Sentiment Breakdown */}
                <div className="bg-slate-800 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-blue-400" />
                    Sentiment Analysis
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">Positive</span>
                        <span className="text-sm font-semibold text-green-400">
                          {dashboardData.sentiment_breakdown?.positive || 0}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div 
                          className="bg-green-500 h-2 rounded-full" 
                          style={{ width: `${dashboardData.sentiment_breakdown?.positive || 0}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">Neutral</span>
                        <span className="text-sm font-semibold text-gray-400">
                          {dashboardData.sentiment_breakdown?.neutral || 0}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div 
                          className="bg-gray-500 h-2 rounded-full" 
                          style={{ width: `${dashboardData.sentiment_breakdown?.neutral || 0}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-slate-300">Negative</span>
                        <span className="text-sm font-semibold text-red-400">
                          {dashboardData.sentiment_breakdown?.negative || 0}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2">
                        <div 
                          className="bg-red-500 h-2 rounded-full" 
                          style={{ width: `${dashboardData.sentiment_breakdown?.negative || 0}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Demographics */}
                <div className="bg-slate-800 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-white mb-3">
                    Demographic Distribution
                  </h4>
                  <div className="space-y-2">
                    {dashboardData.demographic_distribution?.age_distribution && 
                      Object.entries(dashboardData.demographic_distribution.age_distribution).map(([age, percent]: [string, any]) => (
                        <div key={age} className="flex items-center justify-between">
                          <span className="text-sm text-slate-300">{age}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-slate-700 rounded-full h-2">
                              <div 
                                className="bg-blue-500 h-2 rounded-full" 
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                            <span className="text-sm font-semibold text-blue-400 w-10 text-right">
                              {percent}%
                            </span>
                          </div>
                        </div>
                      ))
                    }
                  </div>
                </div>
              </div>

              {/* Objections & Recommendations */}
              <div className="grid grid-cols-2 gap-4">
                {/* Key Objections */}
                <div className="bg-slate-800 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400" />
                    Key Objections
                  </h4>
                  <div className="space-y-3">
                    {dashboardData.objections_analysis && dashboardData.objections_analysis.length > 0 ? (
                      dashboardData.objections_analysis.slice(0, 3).map((objection: any, index: number) => (
                        <div key={index} className="p-3 bg-slate-700/50 rounded-lg border-l-2 border-red-500">
                          <div className="flex items-start justify-between mb-1">
                            <p className="text-sm font-medium text-slate-200">{objection.objection}</p>
                            <Badge variant="secondary" className="text-xs">
                              {objection.severity}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-400">{objection.recommended_response}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-500">No major objections identified</p>
                    )}
                  </div>
                </div>

                {/* Recommendations */}
                <div className="bg-slate-800 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4 text-green-400" />
                    Targeting Recommendations
                  </h4>
                  <div className="space-y-3">
                    {dashboardData.recommendations && dashboardData.recommendations.length > 0 ? (
                      dashboardData.recommendations.slice(0, 3).map((rec: any, index: number) => (
                        <div key={index} className="p-3 bg-slate-700/50 rounded-lg border-l-2 border-green-500">
                          <div className="flex items-start justify-between mb-1">
                            <Badge variant="secondary" className="text-xs">
                              {rec.priority} priority
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-slate-200 mb-1">{rec.action}</p>
                          <p className="text-xs text-slate-400">{rec.expected_impact}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-slate-500">Analyzing recommendations...</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Targeting Insights Summary */}
              {dashboardData.targeting_insights && (
                <div className="mt-6 bg-gradient-to-r from-blue-900/30 to-purple-900/30 p-4 rounded-lg border border-blue-500/30">
                  <h4 className="text-sm font-semibold text-white mb-2">🎯 Primary Target Audience</h4>
                  <p className="text-lg font-bold text-blue-400 mb-2">
                    {dashboardData.targeting_insights.primary_audience}
                  </p>
                  <p className="text-sm text-slate-300">
                    <strong>Best Message:</strong> {dashboardData.targeting_insights.optimal_messaging}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
