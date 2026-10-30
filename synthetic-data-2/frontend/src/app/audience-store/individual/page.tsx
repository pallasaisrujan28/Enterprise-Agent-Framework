"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams, useRouter } from "next/navigation";
import { apiService } from "@/src/lib/api";
import { UserCircle2, MessageSquare, Send, Loader2, ArrowLeft, Paperclip, X, Video, User } from "lucide-react";

interface PersonaItem { 
  persona_uuid: string; 
  narrative_summary?: string; 
  segment_name?: string; 
  campaign_context?: string;
}

interface ChatMessage { 
  role: 'user' | 'assistant'; 
  content: string;
  mediaUrl?: string;
  mediaType?: string;
}

export default function IndividualChatPage() {
  const params = useSearchParams();
  const router = useRouter();
  const audienceGroup = params.get('group') || '';
  const [personas, setPersonas] = useState<PersonaItem[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingPersonas, setLoadingPersonas] = useState<boolean>(true);
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      setLoadingPersonas(true);
      try {
        // Derive segment from group name prefix before underscore
        const seg = audienceGroup.split('_')[0];
        const res = await apiService.getAudiencePersonas({ audience_segment: seg, limit: 50 });
        setPersonas(res.personas || []);
      } catch (e: any) {
        console.error('Failed to load personas:', e);
      } finally {
        setLoadingPersonas(false);
      }
    })();
  }, [audienceGroup]);

  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setFilePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setFilePreview(null);
    }
  }, [file]);

  const selectedPersona = useMemo(() => personas.find(p => p.persona_uuid === selected), [personas, selected]);

  const sendMessage = useCallback(async () => {
    if (!selected || (!input.trim() && !file)) return;
    
    const currentInput = input;
    const currentFile = file;
    const userMsg: ChatMessage = { 
      role: 'user', 
      content: currentInput || (currentFile ? `[Uploaded ${currentFile.type.startsWith('image') ? 'image' : 'video'}]` : ''),
      mediaUrl: filePreview || undefined,
      mediaType: currentFile?.type
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setFile(null);
    setFilePreview(null);
    setLoading(true);
    
    try {
      const res = await apiService.chatWithPersonaEnhanced({ 
        persona_uuid: selected, 
        user_message: currentInput || 'See attached media', 
        mediaFile: currentFile || undefined 
      });
      const assistantMsg: ChatMessage = { role: 'assistant', content: res.response };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${e?.message || 'Failed to send message'}` 
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, file, filePreview, selected]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={() => router.push('/audience-store')}
            className="p-2 rounded-lg hover:bg-slate-800/50 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                <UserCircle2 className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-3xl font-bold">Individual Persona Chat</h1>
            </div>
            <p className="text-slate-300">Group: <span className="font-semibold text-purple-400">{audienceGroup}</span></p>
          </div>
          <div className="w-80">
            <select
              className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              value={selected}
              onChange={(e) => { setSelected(e.target.value); setMessages([]); }}
              disabled={loadingPersonas}
            >
              <option value="" disabled>
                {loadingPersonas ? 'Loading personas...' : 'Select a persona...'}
              </option>
              {personas.map(p => (
                <option key={p.persona_uuid} value={p.persona_uuid}>
                  {p.persona_uuid.slice(0, 8)} — {p.segment_name || p.campaign_context || 'Persona'}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 rounded-xl border border-slate-700/60 bg-slate-800/60 backdrop-blur shadow-2xl flex flex-col h-[75vh] overflow-hidden">
            <div ref={viewportRef} className="flex-1 overflow-y-auto space-y-4 p-6 pr-4">
              {!selected && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500/20 to-indigo-600/20 flex items-center justify-center mb-4">
                    <User className="w-10 h-10 text-purple-400" />
                  </div>
                  <p className="text-slate-400 text-lg">Select a persona to start chatting</p>
                  <p className="text-slate-500 text-sm mt-2">Choose from the dropdown above</p>
                </div>
              )}
              
              {selected && messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500/20 to-indigo-600/20 flex items-center justify-center mb-4">
                    <MessageSquare className="w-10 h-10 text-purple-400" />
                  </div>
                  <p className="text-slate-400 text-lg">Start a conversation with this persona</p>
                  <p className="text-slate-500 text-sm mt-2">Ask questions or share media to get their perspective</p>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                  <div className={`max-w-[80%] ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
                    {m.mediaUrl && (
                      <div className="rounded-lg overflow-hidden border border-slate-700/50">
                        {m.mediaType?.startsWith('image') ? (
                          <img src={m.mediaUrl} alt="Uploaded" className="max-w-full max-h-64 object-contain" />
                        ) : (
                          <video src={m.mediaUrl} controls className="max-w-full max-h-64" />
                        )}
                      </div>
                    )}
                    <div className={`rounded-2xl px-4 py-3 shadow-lg ${
                      m.role === 'user' 
                        ? 'bg-gradient-to-r from-indigo-500 to-indigo-600 text-white' 
                        : 'bg-slate-700/80 text-slate-100'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    </div>
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-slate-700/80 rounded-2xl px-4 py-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                    <span className="text-sm text-slate-300">Persona is thinking...</span>
                  </div>
                </div>
              )}
            </div>

            {filePreview && (
              <div className="px-6 pb-3 border-t border-slate-700/50 pt-3">
                <div className="flex items-center gap-3 bg-slate-900/50 rounded-lg p-3">
                  {file?.type.startsWith('image') ? (
                    <img src={filePreview} alt="Preview" className="w-16 h-16 object-cover rounded" />
                  ) : (
                    <div className="w-16 h-16 bg-slate-700 rounded flex items-center justify-center">
                      <Video className="w-6 h-6 text-slate-400" />
                    </div>
                  )}
                  <div className="flex-1">
                    <p className="text-sm text-slate-300">{file?.name}</p>
                    <p className="text-xs text-slate-500">{(file?.size || 0) / 1024} KB</p>
                  </div>
                  <button
                    onClick={() => { setFile(null); setFilePreview(null); }}
                    className="p-1 rounded hover:bg-slate-700 transition-colors"
                  >
                    <X className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
              </div>
            )}

            <div className="px-6 py-4 border-t border-slate-700/50 flex items-center gap-3 bg-slate-900/30">
              <label className="cursor-pointer p-2 rounded-lg hover:bg-slate-700/50 transition-colors group">
                <input 
                  type="file" 
                  accept="image/*,video/*" 
                  className="hidden" 
                  onChange={(e) => setFile(e.target.files?.[0] || null)} 
                  disabled={!selected}
                />
                <Paperclip className={`w-5 h-5 transition-colors ${selected ? 'text-slate-400 group-hover:text-indigo-400' : 'text-slate-600'}`} />
              </label>
              <input
                className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                placeholder={selected ? "Type your message..." : "Select a persona to start chatting"}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                disabled={!selected || loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !selected || (!input.trim() && !file)}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 text-sm font-medium shadow-lg shadow-indigo-500/25 transition-all"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Send</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 backdrop-blur shadow-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <UserCircle2 className="w-5 h-5 text-purple-400" />
              <div className="text-sm uppercase tracking-wider text-slate-400 font-semibold">Persona Details</div>
            </div>
            {!selectedPersona && (
              <div className="text-center py-12">
                <User className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">Select a persona to view details</p>
              </div>
            )}
            {selectedPersona && (
              <div className="space-y-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-xs text-slate-400 mb-1">UUID</div>
                  <div className="text-slate-200 text-sm break-all font-mono">{selectedPersona.persona_uuid}</div>
                </div>
                {selectedPersona.segment_name && (
                  <div>
                    <div className="text-xs text-slate-400 mb-1">Segment</div>
                    <div className="text-slate-300 text-sm font-medium">{selectedPersona.segment_name}</div>
                  </div>
                )}
                {selectedPersona.narrative_summary && (
                  <div>
                    <div className="text-xs text-slate-400 mb-2">Profile</div>
                    <div className="text-slate-300 text-sm leading-relaxed line-clamp-8">{selectedPersona.narrative_summary}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}




