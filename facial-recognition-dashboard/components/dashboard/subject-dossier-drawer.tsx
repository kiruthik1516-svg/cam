'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSubjectIntelligence } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { formatTime, formatDateTime } from '@/lib/format'
import {
  X,
  UserCheck,
  Clock,
  Calendar,
  Activity,
  GitMerge,
  Sparkles,
  AlertTriangle,
  Camera,
  Layers,
  Fingerprint,
  CheckCircle2,
  ExternalLink,
  Loader2,
  TrendingUp,
  ShieldAlert,
  Sun,
  Sunset,
  Moon,
  Eye,
  Hash,
} from 'lucide-react'

interface SubjectDossierDrawerProps {
  subjectId: string | null
  onClose: () => void
  onMerge?: (targetSubjectId: string, candidateSubjectId: string) => void
  onRename?: (subjectId: string, currentName: string) => void
  onRegister?: (subjectId: string) => void
}

export function SubjectDossierDrawer({
  subjectId,
  onClose,
  onMerge,
  onRename,
  onRegister,
}: SubjectDossierDrawerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'punches' | 'vectors'>('overview')

  const { data: intel, isLoading, isError, error } = useQuery({
    queryKey: ['subject-intelligence', subjectId],
    queryFn: () => (subjectId ? fetchSubjectIntelligence(subjectId) : null),
    enabled: !!subjectId,
    staleTime: 30000,
  })

  if (!subjectId) return null

  const maxHourlyCount = intel?.hourly_frequency ? Math.max(...intel.hourly_frequency, 1) : 1

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-background/80 backdrop-blur-sm animate-in fade-in-0">
      <div className="relative flex h-full w-full max-w-2xl flex-col border-l border-border bg-card shadow-2xl animate-in slide-in-from-right duration-200">
        
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-border bg-muted/40 p-4">
          <div className="flex items-center gap-3">
            {intel?.exemplar_face_image ? (
              <img
                src={`data:image/jpeg;base64,${intel.exemplar_face_image}`}
                alt={intel.display_name}
                className="size-12 rounded-xl object-cover ring-2 ring-primary/30"
              />
            ) : (
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Fingerprint className="size-6" />
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold tracking-tight text-foreground">
                  {intel?.display_name || subjectId}
                </h2>
                <Badge
                  variant={intel?.status === 'profile' ? 'default' : 'secondary'}
                  className="text-[10px] uppercase font-semibold"
                >
                  {intel?.status === 'profile' ? 'Enrolled Profile' : 'Unregistered Subject'}
                </Badge>
                {intel?.exemplar_quality && (
                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 text-[10px]">
                    <Sparkles className="mr-1 size-3 text-emerald-400" />
                    {intel.exemplar_quality}% Quality
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                ID: {subjectId} • {intel?.total_sightings || 0} sightings recorded
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {onRename && intel && (
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => onRename(intel.subject_id, intel.display_name)}
              >
                Rename
              </Button>
            )}
            {onRegister && intel && intel.status === 'unregistered' && (
              <Button
                size="sm"
                className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => onRegister(intel.subject_id)}
              >
                <UserCheck className="mr-1.5 size-3.5" />
                Enroll Profile
              </Button>
            )}
            <Button variant="ghost" size="icon" className="size-8" onClick={onClose}>
              <X className="size-4" />
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border bg-muted/20 px-4">
          <button
            onClick={() => setActiveTab('overview')}
            className={cn(
              'flex items-center gap-2 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors',
              activeTab === 'overview'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <Activity className="size-3.5" />
            Forensic Intelligence
          </button>
          <button
            onClick={() => setActiveTab('punches')}
            className={cn(
              'flex items-center gap-2 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors',
              activeTab === 'punches'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <Calendar className="size-3.5" />
            Daily Attendance Punches ({intel?.daily_punches?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('vectors')}
            className={cn(
              'flex items-center gap-2 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors',
              activeTab === 'vectors'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <GitMerge className="size-3.5" />
            Vector Similarities ({intel?.candidate_vector_matches?.length || 0})
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="flex h-64 flex-col items-center justify-center gap-3 text-muted-foreground">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="text-sm font-medium">Aggregating forensic vectors & timings...</p>
            </div>
          ) : isError ? (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-center">
              <AlertTriangle className="mx-auto size-8 text-destructive mb-2" />
              <h3 className="text-sm font-semibold text-destructive">Failed to Load Intelligence</h3>
              <p className="text-xs text-muted-foreground mt-1">{String(error)}</p>
            </div>
          ) : !intel ? null : (
            <>
              {activeTab === 'overview' && (
                <>
                  {/* 4-Card Primary Metrics Ribbon */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="rounded-xl border border-border bg-muted/30 p-3">
                      <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                        <Eye className="size-3 text-sky-400" />
                        Sightings
                      </span>
                      <p className="text-xl font-bold text-foreground mt-1">{intel.total_sightings}</p>
                      <span className="text-[10px] text-muted-foreground">Total frames</span>
                    </div>

                    <div className="rounded-xl border border-border bg-muted/30 p-3">
                      <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                        <Calendar className="size-3 text-emerald-400" />
                        Attendance
                      </span>
                      <p className="text-xl font-bold text-emerald-400 mt-1">
                        {intel.active_days_count} / 30
                      </p>
                      <span className="text-[10px] text-muted-foreground">
                        {((intel.active_days_count / 30) * 100).toFixed(0)}% Facility Presence
                      </span>
                    </div>

                    <div className="rounded-xl border border-border bg-muted/30 p-3">
                      <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                        <Clock className="size-3 text-amber-400" />
                        Avg Dwell
                      </span>
                      <p className="text-xl font-bold text-foreground mt-1">
                        {intel.average_daily_dwell_minutes}m
                      </p>
                      <span className="text-[10px] text-muted-foreground">Per active day</span>
                    </div>

                    <div className="rounded-xl border border-border bg-muted/30 p-3">
                      <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                        <Camera className="size-3 text-violet-400" />
                        Locations
                      </span>
                      <p className="text-xl font-bold text-foreground mt-1">
                        {intel.observed_cameras.length}
                      </p>
                      <span className="text-[10px] text-muted-foreground">Distinct cameras</span>
                    </div>
                  </div>

                  {/* Global First and Last Seen Timestamps */}
                  <div className="rounded-xl border border-border bg-muted/20 p-3.5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                        <div className="size-2 rounded-full bg-emerald-500" />
                        First Sighting in Archive:
                      </span>
                      <span className="font-mono text-foreground font-semibold">
                        {intel.global_first_seen ? formatDateTime(intel.global_first_seen) : 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                        <div className="size-2 rounded-full bg-sky-500" />
                        Last Sighting in Archive:
                      </span>
                      <span className="font-mono text-foreground font-semibold">
                        {intel.global_last_seen ? formatDateTime(intel.global_last_seen) : 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs border-t border-border/50 pt-2">
                      <span className="text-muted-foreground">Total Operational Span:</span>
                      <span className="font-semibold text-emerald-400">
                        {intel.presence_span_hours} Hours across timeline
                      </span>
                    </div>
                  </div>

                  {/* Shift Breakdown (Diurnal Regimes) */}
                  <div className="rounded-xl border border-border bg-muted/30 p-3.5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <TrendingUp className="size-3.5 text-primary" />
                        Operational Shift Distribution
                      </h4>
                      {intel.shift_breakdown.night_shift_c > 0 && (
                        <Badge variant="destructive" className="text-[10px]">
                          <ShieldAlert className="mr-1 size-3" />
                          {intel.shift_breakdown.night_shift_c} Nocturnal Sightings
                        </Badge>
                      )}
                    </div>

                    <div className="space-y-2 text-xs">
                      {/* Shift A: Morning */}
                      <div>
                        <div className="flex justify-between font-medium mb-1">
                          <span className="flex items-center gap-1 text-amber-300">
                            <Sun className="size-3.5 text-amber-400" />
                            Shift A (Morning 06:00 - 13:59)
                          </span>
                          <span className="font-mono font-bold">
                            {intel.shift_breakdown.morning_shift_a} ({intel.shift_breakdown.morning_percentage}%)
                          </span>
                        </div>
                        <Progress value={intel.shift_breakdown.morning_percentage} className="h-1.5 bg-muted" />
                      </div>

                      {/* Shift B: Afternoon */}
                      <div>
                        <div className="flex justify-between font-medium mb-1">
                          <span className="flex items-center gap-1 text-sky-300">
                            <Sunset className="size-3.5 text-sky-400" />
                            Shift B (Afternoon 14:00 - 21:59)
                          </span>
                          <span className="font-mono font-bold">
                            {intel.shift_breakdown.afternoon_shift_b} ({intel.shift_breakdown.afternoon_percentage}%)
                          </span>
                        </div>
                        <Progress value={intel.shift_breakdown.afternoon_percentage} className="h-1.5 bg-muted" />
                      </div>

                      {/* Shift C: Night Vigilance */}
                      <div>
                        <div className="flex justify-between font-medium mb-1">
                          <span className="flex items-center gap-1 text-purple-300">
                            <Moon className="size-3.5 text-purple-400" />
                            Shift C (Night Vigil 22:00 - 05:59)
                          </span>
                          <span className="font-mono font-bold text-destructive">
                            {intel.shift_breakdown.night_shift_c} ({intel.shift_breakdown.night_percentage}%)
                          </span>
                        </div>
                        <Progress value={intel.shift_breakdown.night_percentage} className="h-1.5 bg-muted" />
                      </div>
                    </div>
                  </div>

                  {/* 24-Hour Diurnal Hourly Histogram */}
                  <div className="rounded-xl border border-border bg-muted/30 p-3.5 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Clock className="size-3.5 text-primary" />
                        24-Hour Diurnal Sighting Frequency
                      </h4>
                      <span className="text-[10px] text-muted-foreground font-mono">00:00 to 23:00 IST</span>
                    </div>

                    <div className="flex h-24 items-end gap-1 pt-2">
                      {intel.hourly_frequency.map((count, hr) => {
                        const heightPct = Math.max(6, Math.round((count / maxHourlyCount) * 100))
                        const isNight = hr < 6 || hr >= 22
                        const isMorning = hr >= 6 && hr < 14
                        return (
                          <div
                            key={hr}
                            className="group relative flex-1 flex flex-col items-center h-full justify-end"
                          >
                            {/* Bar */}
                            <div
                              style={{ height: `${heightPct}%` }}
                              className={cn(
                                'w-full rounded-t transition-all group-hover:brightness-125',
                                isNight
                                  ? 'bg-purple-500/80'
                                  : isMorning
                                  ? 'bg-amber-400/90'
                                  : 'bg-sky-400/90'
                              )}
                            />
                            {/* Hover Tooltip */}
                            <div className="absolute -top-7 hidden group-hover:flex z-20 rounded bg-slate-900 px-1.5 py-0.5 text-[9px] font-mono text-white whitespace-nowrap shadow-lg border border-slate-700">
                              {hr}:00 — {count}x
                            </div>
                            {/* Hour label */}
                            {hr % 4 === 0 && (
                              <span className="text-[8px] text-muted-foreground mt-1 font-mono">{hr}h</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* 30-Day Attendance Calendar Grid */}
                  <div className="rounded-xl border border-border bg-muted/30 p-3.5 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Calendar className="size-3.5 text-primary" />
                        30-Day Physical Presence Matrix
                      </h4>
                      <span className="text-[10px] text-muted-foreground">
                        {intel.active_days_count} of 30 Operational Days
                      </span>
                    </div>

                    <div className="grid grid-cols-10 gap-1.5 pt-1">
                      {Array.from({ length: 30 }, (_, i) => {
                        const dayNum = i + 1
                        const dayStr = `2026-09-${String(dayNum).padStart(2, '0')}`
                        const isActive = intel.active_dates.includes(dayStr)
                        const punch = intel.daily_punches.find((p) => p.date === dayStr)
                        return (
                          <div
                            key={dayNum}
                            className={cn(
                              'group relative flex flex-col items-center justify-center p-2 rounded-lg border text-center transition-all',
                              isActive
                                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 font-bold'
                                : 'bg-muted/10 border-border/40 text-muted-foreground/40'
                            )}
                          >
                            <span className="text-xs font-mono">D{dayNum}</span>
                            {isActive && (
                              <div className="size-1.5 rounded-full bg-emerald-400 mt-0.5" />
                            )}
                            {/* Tooltip */}
                            {isActive && punch && (
                              <div className="absolute bottom-full mb-1 hidden group-hover:flex flex-col z-20 rounded-lg bg-slate-900 p-2 text-[10px] text-white shadow-xl border border-slate-700 whitespace-nowrap">
                                <span className="font-bold text-emerald-400">Day {dayNum} Attendance:</span>
                                <span>In: {punch.first_seen} • Out: {punch.last_seen}</span>
                                <span>Dwell: {Math.round(punch.dwell_seconds / 60)} mins</span>
                                <span>{punch.sightings_count} sightings</span>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'punches' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      Daily In/Out Timings ({intel.daily_punches.length} Active Days)
                    </h3>
                  </div>

                  <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-muted/50 text-muted-foreground uppercase text-[10px] font-semibold border-b border-border">
                        <tr>
                          <th className="p-2.5">Date</th>
                          <th className="p-2.5">In-Time (First)</th>
                          <th className="p-2.5">Out-Time (Last)</th>
                          <th className="p-2.5">Dwell Duration</th>
                          <th className="p-2.5 text-right">Frames</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {intel.daily_punches.map((p) => (
                          <tr key={p.date} className="hover:bg-muted/20">
                            <td className="p-2.5 font-mono font-semibold text-foreground">{p.date}</td>
                            <td className="p-2.5 font-mono text-emerald-400">{p.first_seen || '-'}</td>
                            <td className="p-2.5 font-mono text-sky-400">{p.last_seen || '-'}</td>
                            <td className="p-2.5">
                              {Math.floor(p.dwell_seconds / 3600)}h {Math.floor((p.dwell_seconds % 3600) / 60)}m
                            </td>
                            <td className="p-2.5 text-right font-mono font-bold text-foreground">
                              {p.sightings_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {activeTab === 'vectors' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Cosine Similarity Nearest Neighbors
                      </h3>
                      <p className="text-[11px] text-muted-foreground">
                        Subjects with high 512-D vector proximity ($&gt;50\%$ match)
                      </p>
                    </div>
                  </div>

                  {intel.candidate_vector_matches.length === 0 ? (
                    <div className="rounded-xl border border-border bg-muted/20 p-6 text-center text-muted-foreground text-xs">
                      No nearby duplicate candidates found within threshold.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {intel.candidate_vector_matches.map((cand) => (
                        <div
                          key={cand.id}
                          className="flex items-center justify-between rounded-xl border border-border bg-muted/20 p-3 hover:bg-muted/40 transition-colors"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-xs">
                              {cand.name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-xs text-foreground">{cand.name}</span>
                                <Badge variant="outline" className="text-[10px]">
                                  {cand.role}
                                </Badge>
                              </div>
                              <span className="text-[10px] font-mono text-muted-foreground">ID: {cand.id}</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <div className="text-right">
                              <span
                                className={cn(
                                  'text-xs font-mono font-bold',
                                  cand.similarity >= 85
                                    ? 'text-emerald-400'
                                    : cand.similarity >= 70
                                    ? 'text-sky-400'
                                    : 'text-amber-400'
                                )}
                              >
                                {cand.similarity}% Match
                              </span>
                              <Progress value={cand.similarity} className="h-1 w-20 mt-1 bg-muted" />
                            </div>

                            {onMerge && !cand.is_profile && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs border-primary/40 hover:bg-primary/20"
                                onClick={() => onMerge(intel.subject_id, cand.id)}
                              >
                                <GitMerge className="mr-1 size-3 text-primary" />
                                Merge
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

      </div>
    </div>
  )
}

