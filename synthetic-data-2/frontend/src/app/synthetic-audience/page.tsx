'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { motion } from 'framer-motion'
import { useRouter, useSearchParams } from 'next/navigation'
import { Sidebar } from '@/components/ui/sidebar'
import { Header } from '@/components/ui/header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { GroupChatDialog } from '@/components/audience/GroupChatDialog'
import { IndividualPersonaChat } from '@/components/audience/IndividualPersonaChat'
import { apiService } from '@/lib/api'
import {
  Users,
  MessageSquare,
  Eye,
  Loader2,
  UserCircle2,
  Sparkles,
  AlertCircle,
  MessageCircle,
  Trash2,
  User,
  Brain,
  Activity
} from 'lucide-react'

const SyntheticAudiencePage = () => {
  const router = useRouter()
  const searchParams = useSearchParams()
  const generationId = searchParams?.get('generation_id')

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [personas, setPersonas] = useState<any[]>([])
  const [audienceGroups, setAudienceGroups] = useState<any[]>([])
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const [showGroupChatDialog, setShowGroupChatDialog] = useState(false)
  const [selectedChatGroup, setSelectedChatGroup] = useState<any>(null)
  const [showIndividualChatDialog, setShowIndividualChatDialog] = useState(false)
  const [selectedChatPersona, setSelectedChatPersona] = useState<any>(null)
  const [selectedPersona, setSelectedPersona] = useState<any>(null)
  const [showPersonaDialog, setShowPersonaDialog] = useState(false)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    } else {
      router.push('/')
      return
    }
    loadPersonas(generationId || undefined)
  }, [router, generationId])

  const loadPersonas = async (genId?: string) => {
    setIsLoading(true)
    setError('')
    try {
      const payload: any = { limit: 100 }
      if (genId) payload.generation_id = genId
      const response = await apiService.getAudiencePersonas(payload)
      if (response.success) {
        setPersonas(response.personas)
        setAudienceGroups(response.groups || [])
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load personas')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen)
  const handleGenerateNewAudience = () => router.push('/audience-generation')

  const handleChatWithGroup = (groupKey: string) => {
    const group = audienceGroups.find(g => g.group_key === groupKey)
    if (!group) return
    setSelectedChatGroup(group)
    setShowGroupChatDialog(true)
  }

  const handlePersonaClickInGroupChat = (persona: any) => {
    setSelectedChatPersona(persona)
    setShowGroupChatDialog(false)
    setShowIndividualChatDialog(true)
  }

  const handleViewPersona = async (persona_uuid: string) => {
    setIsLoading(true)
    try {
      const response = await apiService.getPersonaDetail(persona_uuid)
      if (response.success) {
        setSelectedPersona(response.persona)
        setShowPersonaDialog(true)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load persona details')
    } finally {
      setIsLoading(false)
    }
  }

  const handleStartChat = (persona: any) => {
    setSelectedChatPersona(persona)
    setShowIndividualChatDialog(true)
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
      <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          title="Synthetic Audience Store"
          user={user}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          variant="dark"
        />

        <main className="flex-1 overflow-x-hidden overflow-y-auto" style={{ backgroundColor: '#130f30' }}>
          <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            {error && (
              <Alert className="mb-6 bg-red-500/10 border-red-500/50">
                <AlertCircle className="h-4 w-4 text-red-400" />
                <AlertDescription className="text-red-200">{error}</AlertDescription>
              </Alert>
            )}

            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="bg-white/10 backdrop-blur-md border-white/20 p-6">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold flex items-center">
                    <Users className="w-6 h-6 mr-2 text-blue-400" />
                    {selectedGroup ? 'Personas in Group' : 'Audience Groups'}
                    ({selectedGroup ? personas.filter(p => `${p.segment_name}_${p.campaign_context}` === selectedGroup).length : audienceGroups.length})
                  </h3>
                  <div className="flex gap-2">
                    {selectedGroup && (
                      <Button onClick={() => setSelectedGroup(null)} variant="outline" className="border-white/30 text-white hover:bg-white/10">
                        ← Back
                      </Button>
                    )}
                    <Button
                      onClick={async () => {
                        if (window.confirm('Delete ALL personas?')) {
                          try {
                            await fetch('http://localhost:8010/api/audience/delete-all-personas', { method: 'DELETE' })
                            setPersonas([])
                            setAudienceGroups([])
                            setSelectedGroup(null)
                          } catch (err) {
                            alert('Failed to delete')
                          }
                        }
                      }}
                      className="bg-red-600 hover:bg-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-2" /> Delete All
                    </Button>
                    <Button onClick={handleGenerateNewAudience} className="bg-blue-600 hover:bg-blue-700">
                      <Sparkles className="w-4 h-4 mr-2" /> Generate New
                    </Button>
                  </div>
                </div>

                {isLoading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
                  </div>
                ) : selectedGroup === null ? (
                  audienceGroups.length === 0 ? (
                    <div className="text-center py-12">
                      <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                      <p className="text-white text-lg mb-4">No audience groups found</p>
                      <Button onClick={handleGenerateNewAudience} className="bg-blue-600 hover:bg-blue-700">
                        Generate Audience
                      </Button>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {audienceGroups.map((group, index) => (
                        <Card key={group.group_name || index} className="bg-white/5 hover:bg-white/10 border-white/20 p-6">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center space-x-4">
                              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                                <Users className="w-8 h-8 text-white" />
                              </div>
                              <div>
                                <h4 className="text-lg font-bold text-white">{group.segment_name}</h4>
                                <p className="text-sm text-gray-400">{group.campaign_context}</p>
                              </div>
                            </div>
                            <Badge className="bg-blue-500/20 text-blue-300">{group.persona_count} personas</Badge>
                          </div>
                          <div className="flex gap-2">
                            <Button onClick={() => handleChatWithGroup(group.group_key)} className="flex-1 bg-blue-600 hover:bg-blue-700">
                              <MessageCircle className="w-4 h-4 mr-2" /> Chat
                            </Button>
                            <Button onClick={() => setSelectedGroup(group.group_name)} variant="outline" className="flex-1 border-white/30 text-white hover:bg-white/10">
                              <Eye className="w-4 h-4 mr-2" /> View
                            </Button>
                          </div>
                        </Card>
                      ))}
                    </div>
                  )
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {personas.filter(p => `${p.segment_name}_${p.campaign_context}` === selectedGroup).map((persona, index) => (
                      <Card key={persona.persona_uuid || index} className="bg-white/5 hover:bg-white/10 border-white/20 p-4">
                        <div className="flex items-center space-x-3 mb-3">
                          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                            <UserCircle2 className="w-7 h-7 text-white" />
                          </div>
                          <div>
                            <p className="text-white font-semibold">{persona.segment_name?.substring(0, 15) || `Persona ${persona.persona_uuid.substring(0, 8)}`}</p>
                            <p className="text-xs text-gray-400">{new Date(persona.generation_timestamp).toLocaleDateString()}</p>
                          </div>
                        </div>
                        <p className="text-sm text-gray-300 mb-4 line-clamp-2">{persona.narrative_summary || persona.campaign_context}</p>
                        <div className="flex space-x-2">
                          <Button onClick={() => handleViewPersona(persona.persona_uuid)} variant="outline" size="sm" className="flex-1 border-white/30 text-white hover:bg-white/10">
                            <Eye className="w-4 h-4 mr-1" /> View
                          </Button>
                          <Button onClick={() => handleStartChat(persona)} size="sm" className="flex-1 bg-blue-600 hover:bg-blue-700">
                            <MessageSquare className="w-4 h-4 mr-1" /> Chat
                          </Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>
          </div>
        </main>
      </div>

      {selectedChatGroup && (
        <GroupChatDialog
          open={showGroupChatDialog}
          onClose={() => setShowGroupChatDialog(false)}
          audienceGroup={{
            group_name: `${selectedChatGroup.segment_name}_${selectedChatGroup.campaign_context}`,
            segment_name: selectedChatGroup.segment_name,
            campaign_context: selectedChatGroup.campaign_context,
            persona_count: personas.filter(p => p.segment_name === selectedChatGroup.segment_name && p.campaign_context === selectedChatGroup.campaign_context).length
          }}
          personas={personas.filter(p => p.segment_name === selectedChatGroup.segment_name && p.campaign_context === selectedChatGroup.campaign_context)}
          onPersonaClick={handlePersonaClickInGroupChat}
        />
      )}

      {selectedChatPersona && (
        <IndividualPersonaChat
          open={showIndividualChatDialog}
          onClose={() => setShowIndividualChatDialog(false)}
          persona={selectedChatPersona}
          mode="dialog"
        />
      )}

      <Dialog open={showPersonaDialog} onOpenChange={setShowPersonaDialog}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto bg-gray-900 text-white border-gray-700">
          <DialogHeader>
            <DialogTitle className="text-2xl">Persona Details</DialogTitle>
          </DialogHeader>
          {selectedPersona && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="text-lg font-bold">{selectedPersona.segment}</h4>
                  <p className="text-sm text-gray-400">{selectedPersona.campaign_context}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Generated: {new Date(selectedPersona.generation_timestamp).toLocaleDateString()}
                  </p>
                </div>
                <Button onClick={() => { setSelectedChatPersona(selectedPersona); setShowPersonaDialog(false); setShowIndividualChatDialog(true); }} className="bg-blue-600 hover:bg-blue-700">
                  <MessageSquare className="w-4 h-4 mr-2" /> Chat
                </Button>
              </div>

              {/* Narrative Summary */}
              {selectedPersona.narrative && (
                <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                  <h5 className="text-sm font-semibold text-gray-300 mb-2">Narrative Profile</h5>
                  <p className="text-sm text-gray-400 whitespace-pre-wrap">{selectedPersona.narrative}</p>
                </div>
              )}

              {/* Demographics */}
              {selectedPersona.demographics && Object.keys(selectedPersona.demographics).length > 0 && (
                <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                  <h5 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-400" />
                    Demographics
                  </h5>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(selectedPersona.demographics)
                      .filter(([_, value]) => value && value !== 'unknown' && value !== '')
                      .map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}:</span>
                          <Badge variant="outline" className="text-xs bg-gray-800 border-gray-600 text-white">
                            {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                          </Badge>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Behavioral Traits */}
              {selectedPersona.behavioral_traits && Object.keys(selectedPersona.behavioral_traits).length > 0 && (
                <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                  <h5 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-purple-400" />
                    Behavioral Traits
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedPersona.behavioral_traits)
                      .filter(([_, value]) => value === true || (value && value !== 'unknown' && value !== false))
                      .map(([key, value]) => (
                        <Badge key={key} className="text-xs bg-purple-500/20 text-purple-300 border-purple-500/30">
                          {key.replace(/_/g, ' ')}
                          {typeof value !== 'boolean' && value !== true && `: ${value}`}
                        </Badge>
                      ))}
                  </div>
                </div>
              )}

              {/* All Traits (Additional) */}
              {selectedPersona.all_traits && Object.keys(selectedPersona.all_traits).length > 0 && (
                <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                  <h5 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                    <Brain className="w-4 h-4 text-green-400" />
                    Additional Traits
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(selectedPersona.all_traits)
                      .filter(([key, value]) => {
                        // Exclude traits already shown in demographics or behavioral
                        const isDemographic = selectedPersona.demographics && key in selectedPersona.demographics
                        const isBehavioral = selectedPersona.behavioral_traits && key in selectedPersona.behavioral_traits
                        return !isDemographic && !isBehavioral && value && value !== 'unknown' && value !== false
                      })
                      .map(([key, value]) => (
                        <Badge key={key} className="text-xs bg-green-500/20 text-green-300 border-green-500/30">
                          {key.replace(/_/g, ' ')}
                          {typeof value !== 'boolean' && value !== true && `: ${value}`}
                        </Badge>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

const SyntheticAudiencePageWrapper = () => (
  <Suspense fallback={<div className="flex items-center justify-center min-h-screen bg-gray-900"><Loader2 className="w-12 h-12 text-blue-400 animate-spin" /></div>}>
    <SyntheticAudiencePage />
  </Suspense>
)

export default SyntheticAudiencePageWrapper
