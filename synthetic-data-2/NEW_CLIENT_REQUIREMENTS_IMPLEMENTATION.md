# New Client Requirements Implementation

**Date:** October 28, 2025  
**Version:** 3.0.0  
**Status:** ✅ Backend Implemented | 🚧 Frontend Pending

---

## 📋 Client Request Summary

### **Old Flow (Previous):**
```
1. User uploads media (image/video)
2. User selects evaluation template
3. System runs evaluation
4. Shows results
```

### **New Flow (Client Requirement):**
```
1. User goes to Synthetic Audience Store
2. User sees all AUDIENCE GROUPS (grouped personas)
3. User selects an audience group
4. Two interaction options:
   a) Chat with ENTIRE GROUP (collective conversation)
   b) Chat with INDIVIDUAL personas in that group
5. Both chats support:
   - Text questions
   - Media upload (image/video) in chat
   - Get feedback on products/campaigns
   - Persistent conversation history
```

---

## ✅ Backend Implementation Complete

### **New API Endpoints:**

#### **1. `/api/audience/chat-with-group`** (Group Chat)
**Purpose:** Chat with an entire audience group collectively

**Request:**
```typescript
{
  audience_group: string     // e.g., "Healthcare Professionals_anti-aging serum"
  user_message: string       // User's question
  media_file?: File          // Optional image/video
  conversation_id?: string   // Optional for continuity
}
```

**Response:**
```typescript
{
  success: true,
  audience_group: string,
  num_personas: number,
  collective_response: string,    // Aggregated response from all personas
  individual_responses: [         // Individual persona perspectives
    {
      persona_uuid: string,
      response: string,
      persona_summary: string
    }
  ],
  has_media: boolean,
  timestamp: string
}
```

**How it works:**
1. Receives user question + optional media
2. Gets all personas in the specified audience group (max 10)
3. Each persona evaluates the question/media from their perspective
4. System aggregates all responses into a collective answer
5. Returns both collective summary and individual perspectives

---

#### **2. `/api/audience/chat-with-persona-enhanced`** (Individual Chat)
**Purpose:** Chat one-on-one with a specific persona, with media support

**Request:**
```typescript
{
  persona_uuid: string       // Specific persona ID
  user_message: string       // User's question
  media_file?: File          // Optional image/video
  conversation_id?: string   // Optional for continuity
}
```

**Response:**
```typescript
{
  success: true,
  persona_uuid: string,
  persona_summary: {
    segment: string,
    campaign_context: string,
    narrative_preview: string
  },
  response: string,              // Persona's response
  conversation_history: [        // Full chat history
    { role: "user", content: string },
    { role: "assistant", content: string }
  ],
  has_media: boolean,
  timestamp: string
}
```

**How it works:**
1. Receives user question + optional media
2. Loads persona's full profile (narrative, traits, demographics)
3. Persona responds authentically based on their character
4. Maintains conversation history
5. Returns response + context

---

## 🚧 Frontend Implementation Needed

### **Changes to Synthetic Audience Store Page:**

#### **Step 1: Update Group Display**
**File:** `frontend/src/app/synthetic-audience/page.tsx`

**Current State:**
```typescript
// Shows flat list of personas
personas.map(persona => <PersonaCard />)
```

**New State:**
```typescript
// Show audience groups first
audienceGroups.map(group => (
  <AudienceGroupCard
    groupName={group.group_name}
    segmentName={group.segment_name}
    campaignContext={group.campaign_context}
    personaCount={group.persona_count}
    onClick={() => selectGroup(group)}
  />
))
```

---

#### **Step 2: Add Group Chat Interface**
**New Component:** `GroupChatDialog.tsx`

```typescript
interface GroupChatDialogProps {
  audienceGroup: string
  personas: Persona[]
  onClose: () => void
}

const GroupChatDialog = ({ audienceGroup, personas, onClose }: GroupChatDialogProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [mediaFile, setMediaFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = async () => {
    const formData = new FormData()
    formData.append('audience_group', audienceGroup)
    formData.append('user_message', userMessage)
    if (mediaFile) {
      formData.append('media_file', mediaFile)
    }

    const response = await fetch('/api/audience/chat-with-group', {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    
    setMessages([
      ...messages,
      { role: 'user', content: userMessage, hasMedia: !!mediaFile },
      { 
        role: 'assistant', 
        content: data.collective_response,
        individualResponses: data.individual_responses
      }
    ])
  }

  return (
    <Dialog>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            Chat with {audienceGroup}
            <Badge>{personas.length} personas</Badge>
          </DialogTitle>
        </DialogHeader>

        {/* Chat Messages */}
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
              <div className="inline-block p-4 rounded-lg bg-slate-800">
                {msg.content}
                
                {/* Show individual responses if assistant message */}
                {msg.role === 'assistant' && msg.individualResponses && (
                  <div className="mt-4 space-y-2">
                    <Button 
                      variant="ghost" 
                      onClick={() => setShowIndividualResponses(!showIndividualResponses)}
                    >
                      {showIndividualResponses ? 'Hide' : 'Show'} Individual Perspectives
                    </Button>
                    
                    {showIndividualResponses && msg.individualResponses.map(resp => (
                      <div key={resp.persona_uuid} className="p-2 bg-slate-700 rounded">
                        <p className="text-xs text-slate-400">{resp.persona_summary}</p>
                        <p className="text-sm mt-1">{resp.response}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="flex gap-2">
          <input
            type="file"
            accept="image/*,video/*"
            onChange={(e) => setMediaFile(e.target.files?.[0] || null)}
            className="hidden"
            id="media-upload"
          />
          <label htmlFor="media-upload">
            <Button variant="outline" as="span">
              📎 Upload Media
            </Button>
          </label>
          
          {mediaFile && <Badge>{mediaFile.name}</Badge>}
          
          <input
            type="text"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Ask the group a question..."
            className="flex-1 p-2 rounded bg-slate-800"
          />
          
          <Button onClick={sendMessage} disabled={isLoading}>
            Send
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

---

#### **Step 3: Add Individual Persona Chat**
**New Component:** `PersonaChatDialog.tsx`

```typescript
interface PersonaChatDialogProps {
  persona: Persona
  onClose: () => void
}

const PersonaChatDialog = ({ persona, onClose }: PersonaChatDialogProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [userMessage, setUserMessage] = useState('')
  const [mediaFile, setMediaFile] = useState<File | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = async () => {
    const formData = new FormData()
    formData.append('persona_uuid', persona.uuid)
    formData.append('user_message', userMessage)
    if (mediaFile) {
      formData.append('media_file', mediaFile)
    }

    const response = await fetch('/api/audience/chat-with-persona-enhanced', {
      method: 'POST',
      body: formData
    })

    const data = await response.json()
    
    setMessages([
      ...messages,
      { role: 'user', content: userMessage, hasMedia: !!mediaFile },
      { role: 'assistant', content: data.response }
    ])
  }

  return (
    <Dialog>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Chat with {persona.segment}</DialogTitle>
          <p className="text-sm text-slate-400">{persona.narrative_preview}</p>
        </DialogHeader>

        {/* Similar chat interface as group chat */}
        {/* But simpler - just user/assistant messages */}
      </DialogContent>
    </Dialog>
  )
}
```

---

#### **Step 4: Update Main Page Layout**
**File:** `frontend/src/app/synthetic-audience/page.tsx`

```typescript
const SyntheticAudiencePage = () => {
  const [viewMode, setViewMode] = useState<'groups' | 'personas'>('groups')
  const [selectedGroup, setSelectedGroup] = useState<AudienceGroup | null>(null)
  const [showGroupChat, setShowGroupChat] = useState(false)
  const [showPersonaChat, setShowPersonaChat] = useState(false)
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)

  return (
    <div>
      {/* Tab Navigation */}
      <Tabs value={viewMode} onValueChange={setViewMode}>
        <TabsList>
          <TabsTrigger value="groups">Audience Groups</TabsTrigger>
          <TabsTrigger value="personas">All Personas</TabsTrigger>
        </TabsList>

        {/* Groups View */}
        <TabsContent value="groups">
          <div className="grid grid-cols-3 gap-4">
            {audienceGroups.map(group => (
              <Card key={group.group_name}>
                <h3>{group.segment_name}</h3>
                <p>{group.campaign_context}</p>
                <Badge>{group.persona_count} personas</Badge>
                
                <div className="flex gap-2 mt-4">
                  <Button onClick={() => {
                    setSelectedGroup(group)
                    setShowGroupChat(true)
                  }}>
                    💬 Chat with Group
                  </Button>
                  
                  <Button 
                    variant="outline"
                    onClick={() => {
                      setSelectedGroup(group)
                      setViewMode('personas')
                    }}
                  >
                    👥 View Personas
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Personas View (when group selected) */}
        <TabsContent value="personas">
          {selectedGroup && (
            <div>
              <h2>Personas in {selectedGroup.segment_name}</h2>
              <div className="grid grid-cols-3 gap-4">
                {personas
                  .filter(p => p.segment === selectedGroup.segment_name)
                  .map(persona => (
                    <Card key={persona.uuid}>
                      <h4>{persona.segment}</h4>
                      <p className="text-sm">{persona.narrative_preview}</p>
                      
                      <Button onClick={() => {
                        setSelectedPersona(persona)
                        setShowPersonaChat(true)
                      }}>
                        💬 Chat 1-on-1
                      </Button>
                    </Card>
                  ))}
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      {showGroupChat && selectedGroup && (
        <GroupChatDialog
          audienceGroup={selectedGroup.group_name}
          personas={personas.filter(p => p.segment === selectedGroup.segment_name)}
          onClose={() => setShowGroupChat(false)}
        />
      )}

      {showPersonaChat && selectedPersona && (
        <PersonaChatDialog
          persona={selectedPersona}
          onClose={() => setShowPersonaChat(false)}
        />
      )}
    </div>
  )
}
```

---

## 🎯 User Flow with New Implementation

### **Scenario: User wants feedback on anti-aging serum from healthcare professionals**

1. **User navigates to Synthetic Audience Store**
   - Sees audience groups displayed as cards
   - Each card shows: segment name, campaign context, persona count

2. **User clicks "Healthcare Professionals - Anti-aging serum" group**
   - Two options appear:
     - "💬 Chat with Group" (collective conversation)
     - "👥 View Personas" (see individual personas)

3. **Option A: Group Chat**
   - User clicks "Chat with Group"
   - Chat dialog opens
   - User types: "What do you think about the $200 price point?"
   - User optionally uploads product image
   - System shows:
     - Collective response (aggregated from all 10 personas)
     - Option to expand and see each persona's individual perspective
   - User continues conversation with context maintained

4. **Option B: Individual Chat**
   - User clicks "View Personas"
   - Sees all 10 healthcare professional personas
   - Clicks "Chat 1-on-1" with "Dr. Sarah Chen, age 42"
   - Chat dialog opens for just that persona
   - User asks: "Would you recommend this to your patients?"
   - User uploads before/after photo
   - Persona responds based on their specific traits
   - Conversation continues with that individual

---

## 📊 Benefits of New Approach

### **For Client:**
1. ✅ More intuitive workflow (group-first)
2. ✅ Flexible interaction (group or individual)
3. ✅ Media in conversation context (not separate step)
4. ✅ Persistent conversations with personas
5. ✅ Deeper insights (compare group vs individual perspectives)

### **For Users:**
1. ✅ Natural conversation flow
2. ✅ Upload media when needed in chat
3. ✅ See collective sentiment + individual nuances
4. ✅ Build on previous questions (conversation history)

---

## 🚀 Next Steps

### **Backend:** ✅ COMPLETE
- [x] Group chat endpoint
- [x] Enhanced individual chat with media
- [x] Media processing in chat context
- [x] Response aggregation

### **Frontend:** 🚧 TO DO
- [ ] Update audience store page layout
- [ ] Create GroupChatDialog component
- [ ] Create PersonaChatDialog component
- [ ] Add media upload to chat interface
- [ ] Update API service with new endpoints
- [ ] Add conversation history display
- [ ] Add individual responses expansion

---

## 📝 API Integration Guide

### **TypeScript Service (frontend/src/lib/api.ts):**

```typescript
// Add these methods to apiService

async chatWithGroup(
  audienceGroup: string,
  message: string,
  mediaFile?: File
): Promise<GroupChatResponse> {
  const formData = new FormData()
  formData.append('audience_group', audienceGroup)
  formData.append('user_message', message)
  if (mediaFile) {
    formData.append('media_file', mediaFile)
  }

  const response = await fetch(`${API_BASE_URL}/api/audience/chat-with-group`, {
    method: 'POST',
    body: formData
  })

  return response.json()
}

async chatWithPersonaEnhanced(
  personaUuid: string,
  message: string,
  mediaFile?: File
): Promise<PersonaChatResponse> {
  const formData = new FormData()
  formData.append('persona_uuid', personaUuid)
  formData.append('user_message', message)
  if (mediaFile) {
    formData.append('media_file', mediaFile)
  }

  const response = await fetch(`${API_BASE_URL}/api/audience/chat-with-persona-enhanced`, {
    method: 'POST',
    body: formData
  })

  return response.json()
}
```

---

## 🎨 UI/UX Recommendations

### **Group Chat:**
- Display group avatar (collage of persona faces)
- Show "X personas typing..." indicator
- Collapsible individual responses
- Highlight consensus vs divergent opinions

### **Individual Chat:**
- Display persona avatar/photo
- Show persona traits sidebar
- Indicate persona's "mood" based on response
- Show related personas from same group

### **Media Upload:**
- Drag-and-drop support
- Image/video preview before sending
- Progress indicator for upload
- Show media thumbnail in chat history

---

## ⚠️ Important Notes

1. **Group chat limited to 10 personas** to avoid rate limits and slow responses
2. **Media files processed with Claude Vision API** - costs apply
3. **Conversation history** currently in-memory - consider PostgreSQL storage for persistence
4. **Both endpoints support** image and video formats

---

**Ready for frontend implementation! 🚀**
