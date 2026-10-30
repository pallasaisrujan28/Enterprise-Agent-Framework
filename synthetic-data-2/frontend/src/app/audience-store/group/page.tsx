"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams, useRouter } from "next/navigation";
import { apiService } from "@/src/lib/api";
import { MessageSquare, Users, Send, Image as ImageIcon, Video, X, Loader2, ArrowLeft, Paperclip } from "lucide-react";

interface ChatMessage { 
  role: 'user' | 'assistant'; 
  content: string;
  mediaUrl?: string;
  mediaType?: string;
  individualResponses?: Array<{ persona_uuid: string; response: string; persona_summary: string }>;
}

export default function GroupChatPage() {
  const params = useSearchParams();
  const router = useRouter();
  const audienceGroup = params.get('group') || '';
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const viewportRef = useRef<HTMLDivElement>(null);

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

  const sendMessage = useCallback(async () => {
    if (!input.trim() && !file) return;
    
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
      const res = await apiService.chatWithGroup({ 
        audience_group: audienceGroup, 
        user_message: currentInput || 'See attached media', 
        mediaFile: currentFile || undefined 
      });
      const assistantMsg: ChatMessage = { 
        role: 'assistant', 
        content: res.collective_response,
        individualResponses: res.individual_responses
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${e?.message || 'Failed to send message'}` 
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, file, filePreview, audienceGroup]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={() => router.push('/audience-store')}
            className="p-2 rounded-lg hover:bg-slate-800/50 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Users className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-3xl font-bold">Group Chat</h1>
            </div>
            <p className="text-slate-300">Talking to: <span className="font-semibold text-indigo-400">{audienceGroup}</span></p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 backdrop-blur shadow-2xl flex flex-col h-[75vh] overflow-hidden">
          <div ref={viewportRef} className="flex-1 overflow-y-auto space-y-4 p-6 pr-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-600/20 flex items-center justify-center mb-4">
                  <MessageSquare className="w-10 h-10 text-indigo-400" />
                </div>
                <p className="text-slate-400 text-lg">Start a conversation with the entire group</p>
                <p className="text-slate-500 text-sm mt-2">All personas in this group will respond collectively</p>
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
                  {m.individualResponses && m.individualResponses.length > 0 && (
                    <div className="mt-2 space-y-2 w-full">
                      <div className="text-xs text-slate-400 mb-2">Individual responses ({m.individualResponses.length} personas):</div>
                      {m.individualResponses.slice(0, 3).map((resp, idx) => (
                        <div key={idx} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/30">
                          <div className="text-xs text-indigo-400 mb-1">Persona {idx + 1}</div>
                          <p className="text-xs text-slate-300 line-clamp-2">{resp.response}</p>
                        </div>
                      ))}
                      {m.individualResponses.length > 3 && (
                        <div className="text-xs text-slate-500">+{m.individualResponses.length - 3} more responses</div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-700/80 rounded-2xl px-4 py-3 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  <span className="text-sm text-slate-300">All personas are thinking...</span>
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
              />
              <Paperclip className="w-5 h-5 text-slate-400 group-hover:text-indigo-400 transition-colors" />
            </label>
            <input
              className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || (!input.trim() && !file)}
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
      </div>
    </div>
  );
}




