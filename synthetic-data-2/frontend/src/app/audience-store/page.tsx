"use client";

import { useEffect, useMemo, useState } from 'react';
import { apiService } from "@/lib/api";
import Link from "next/link";
import { Users, MessageSquare, UserCircle2, Loader2, Sparkles, ArrowRight } from "lucide-react";

interface GroupInfo {
  group_name: string;
  segment_name: string;
  campaign_context: string;
  persona_count: number;
}

export default function AudienceStorePage() {
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiService.getAudiencePersonas({ limit: 200 });
        setGroups(res.groups || []);
      } catch (e: any) {
        setError(e?.message || 'Failed to load groups');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const grid = useMemo(() => {
    return groups.sort((a, b) => b.persona_count - a.persona_count);
  }, [groups]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Users className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Audience Store
            </h1>
          </div>
          <p className="text-slate-300 mt-2 text-lg">Select a group to start a conversation or drill into individual personas.</p>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mr-3" />
            <span className="text-slate-300 text-lg">Loading audience groups...</span>
          </div>
        )}
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && groups.length === 0 && (
          <div className="text-center py-20">
            <Users className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 text-lg">No audience groups found</p>
            <p className="text-slate-500 text-sm mt-2">Generate an audience to see groups here</p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {grid.map((g) => (
            <div key={g.group_name} className="group rounded-xl border border-slate-700/60 bg-slate-800/60 backdrop-blur p-6 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/10 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">{g.segment_name}</div>
                  </div>
                  <div className="text-lg font-semibold mt-1 line-clamp-2 text-white">{g.campaign_context}</div>
                </div>
                <div className="flex items-center gap-1 text-slate-300 text-sm bg-slate-700/50 px-2 py-1 rounded-full">
                  <UserCircle2 className="w-4 h-4" />
                  <span className="font-medium">{g.persona_count}</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Link
                  href={{ pathname: '/audience-store/group', query: { group: g.group_name } }}
                  className="group/btn inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white py-3 px-4 text-sm font-medium shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 transition-all duration-200"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Chat with entire group</span>
                  <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                </Link>
                <Link
                  href={{ pathname: '/audience-store/individual', query: { group: g.group_name } }}
                  className="group/btn inline-flex items-center justify-center gap-2 rounded-lg bg-slate-700/80 hover:bg-slate-600/80 text-white py-3 px-4 text-sm font-medium shadow-lg hover:shadow-xl transition-all duration-200 border border-slate-600/50"
                >
                  <UserCircle2 className="w-4 h-4" />
                  <span>Chat with individual</span>
                  <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}




