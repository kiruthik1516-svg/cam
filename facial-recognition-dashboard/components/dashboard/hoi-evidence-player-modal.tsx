'use client';

import React, { useRef, useState, useEffect } from 'react';
import type { HoiIncidentItem } from '@/lib/types';
import { getHoiVideoUrl, getHoiSnapshotUrl } from '@/lib/api/hoi';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Play,
  Pause,
  RotateCcw,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Volume2,
  VolumeX,
  Download,
  Copy,
  Check,
  Video,
  Camera,
  AlertTriangle,
  Clock,
  Shield,
  Activity,
  Layers,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface HoiEvidencePlayerModalProps {
  incident: HoiIncidentItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function HoiEvidencePlayerModal({
  incident,
  open,
  onOpenChange,
}: HoiEvidencePlayerModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isMuted, setIsMuted] = useState(true);
  const [activeView, setActiveView] = useState<'video' | 'snapshot'>('video');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open && incident) {
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(incident.duration_sec || 0);
      setActiveView('video');
    }
  }, [open, incident]);

  if (!incident) return null;

  const videoUrl = getHoiVideoUrl(incident.day, incident.clip_filename);
  const snapshotUrl = incident.snapshot_filename
    ? getHoiSnapshotUrl(incident.day, incident.snapshot_filename)
    : '';

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    const ms = Math.floor((secs % 1) * 1000);
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleSeek = (deltaSeconds: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, Math.min(videoRef.current.duration || 9999, videoRef.current.currentTime + deltaSeconds));
  };

  const handleFrameStep = (frames: number) => {
    if (!videoRef.current) return;
    videoRef.current.pause();
    setIsPlaying(false);
    // At ~30fps, 1 frame is ~0.0333s
    videoRef.current.currentTime = Math.max(0, Math.min(videoRef.current.duration || 9999, videoRef.current.currentTime + frames * (1 / 30)));
  };

  const setSpeed = (rate: number) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = rate;
    setPlaybackRate(rate);
  };

  const toggleFullscreen = () => {
    if (!videoRef.current) return;
    if (videoRef.current.requestFullscreen) {
      videoRef.current.requestFullscreen();
    }
  };

  const copyIncidentDetails = () => {
    const text = `Engine v2 Incident Report
ID: ${incident.incident_id}
Day: ${incident.day}
Severity: ${incident.severity}
Zone: ${incident.zone_name} (${incident.zone_id})
Active Hand: ${incident.active_hand}
Wrist Distance: ${incident.min_wrist_distance_px.toFixed(1)} px
Time: ${incident.start_time} - ${incident.end_time} (Duration: ${incident.duration_sec.toFixed(1)}s)
Clip: ${incident.clip_filename}`;

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse';
      case 'SEVERE':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'ELEVATED':
      default:
        return 'bg-sky-500/20 text-sky-300 border-sky-500/40';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl p-0 overflow-hidden bg-background/95 border-border/70 backdrop-blur-2xl shadow-2xl">
        <DialogHeader className="p-4 pb-2 border-b border-border/50 bg-card/40 flex flex-row items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex size-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex rounded-full size-3 bg-primary" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <DialogTitle className="text-base font-bold font-mono tracking-tight text-foreground flex items-center gap-2">
                  <span>Engine v2 Forensic Evidence Viewer</span>
                  <Badge variant="outline" className="font-mono text-xs px-2 py-0 border-primary/50 text-primary">
                    RFC 7233 Streaming
                  </Badge>
                </DialogTitle>
              </div>
              <DialogDescription className="text-xs font-mono text-muted-foreground mt-0.5">
                Session {incident.incident_id} &bull; Day {incident.day} &bull; 17-Keypoint YOLOv8-Pose HOI
              </DialogDescription>
            </div>
          </div>

          <div className="flex items-center gap-2 mr-6">
            <Badge variant="outline" className={cn('text-xs font-mono px-2.5 py-0.5 font-semibold', getSeverityBadgeClass(incident.severity))}>
              {incident.severity}
            </Badge>
            <Badge variant="secondary" className="font-mono text-xs px-2 py-0.5 bg-muted/60 text-foreground">
              {incident.zone_id}
            </Badge>
          </div>
        </DialogHeader>

        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[580px] bg-black/60">
          {/* Main Media Player / Snapshot Stage */}
          <div className="lg:col-span-8 flex flex-col justify-between bg-black relative border-r border-border/40">
            {/* View Switcher Bar */}
            <div className="absolute top-3 left-3 z-20 flex items-center gap-1.5 bg-background/80 backdrop-blur-md border border-border/60 rounded-lg p-1 shadow-lg">
              <button
                type="button"
                onClick={() => setActiveView('video')}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono font-medium transition-colors',
                  activeView === 'video'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <Video className="size-3.5" />
                <span>3K Video Stream</span>
              </button>
              {snapshotUrl && (
                <button
                  type="button"
                  onClick={() => {
                    setActiveView('snapshot');
                    if (videoRef.current) {
                      videoRef.current.pause();
                      setIsPlaying(false);
                    }
                  }}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1 rounded text-xs font-mono font-medium transition-colors',
                    activeView === 'snapshot'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Camera className="size-3.5" />
                  <span>Skeletal Sniper Snapshot</span>
                </button>
              )}
            </div>

            {/* Media Canvas */}
            <div className="relative flex-1 flex items-center justify-center min-h-[420px] bg-black">
              {activeView === 'video' ? (
                <video
                  ref={videoRef}
                  src={videoUrl}
                  controls={false}
                  playsInline
                  muted={isMuted}
                  preload="metadata"
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onTimeUpdate={() => {
                    if (videoRef.current) {
                      setCurrentTime(videoRef.current.currentTime);
                    }
                  }}
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      setDuration(videoRef.current.duration || incident.duration_sec);
                    }
                  }}
                  className="w-full h-full max-h-[520px] object-contain"
                />
              ) : (
                <div className="relative w-full h-full flex items-center justify-center p-2">
                  <img
                    src={snapshotUrl}
                    alt={`Forensic keypoint capture ${incident.incident_id}`}
                    className="max-w-full max-h-[520px] object-contain rounded border border-border/40 shadow-2xl"
                  />
                  <div className="absolute bottom-4 left-4 bg-background/85 backdrop-blur-md border border-border/70 rounded-md px-3 py-1.5 text-[11px] font-mono text-foreground flex items-center gap-2">
                    <Sparkles className="size-3.5 text-amber-400" />
                    <span>Peak Contact Keypoint Overlay: {incident.min_wrist_distance_px.toFixed(1)} px</span>
                  </div>
                </div>
              )}
            </div>

            {/* In-Browser Streaming Video Controls */}
            {activeView === 'video' && (
              <div className="p-3 bg-card/90 border-t border-border/50 backdrop-blur-md space-y-2">
                {/* Timeline Progress Bar */}
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={0}
                    max={duration || 1}
                    step={0.01}
                    value={currentTime}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setCurrentTime(val);
                      if (videoRef.current) {
                        videoRef.current.currentTime = val;
                      }
                    }}
                    className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>

                {/* Control Actions Ribbon */}
                <div className="flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={togglePlay}
                      className="size-8 p-0 text-foreground hover:bg-muted/60"
                      title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
                    >
                      {isPlaying ? <Pause className="size-4 fill-current" /> : <Play className="size-4 fill-current" />}
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleSeek(-5)}
                      className="size-8 p-0 text-muted-foreground hover:text-foreground hover:bg-muted/60"
                      title="Seek Backward 5s"
                    >
                      <RotateCcw className="size-3.5" />
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleSeek(5)}
                      className="size-8 p-0 text-muted-foreground hover:text-foreground hover:bg-muted/60"
                      title="Seek Forward 5s"
                    >
                      <RotateCw className="size-3.5" />
                    </Button>

                    <span className="w-px h-4 bg-border/60 mx-1" />

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleFrameStep(-1)}
                      className="h-7 px-2 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted/60"
                      title="Step 1 Frame Backward"
                    >
                      <ChevronLeft className="size-3.5" />
                      <span>-1F</span>
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleFrameStep(1)}
                      className="h-7 px-2 text-[10px] text-muted-foreground hover:text-foreground hover:bg-muted/60"
                      title="Step 1 Frame Forward"
                    >
                      <span>+1F</span>
                      <ChevronRight className="size-3.5" />
                    </Button>

                    <span className="w-px h-4 bg-border/60 mx-1" />

                    {/* Timecode Readout */}
                    <span className="text-foreground font-semibold font-mono text-[11px] tabular-nums">
                      {formatTime(currentTime)}
                    </span>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-muted-foreground font-mono text-[11px] tabular-nums">
                      {formatTime(duration)}
                    </span>
                  </div>

                  {/* Speed Controls & Fullscreen */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-muted-foreground uppercase mr-1">Speed:</span>
                    {[0.25, 0.5, 1.0, 2.0].map((rate) => (
                      <button
                        key={rate}
                        type="button"
                        onClick={() => setSpeed(rate)}
                        className={cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors',
                          playbackRate === rate
                            ? 'bg-primary text-primary-foreground font-bold'
                            : 'text-muted-foreground hover:text-foreground bg-muted/40'
                        )}
                      >
                        {rate}x
                      </button>
                    ))}

                    <span className="w-px h-4 bg-border/60 mx-1" />

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        const newMuted = !isMuted;
                        setIsMuted(newMuted);
                        if (videoRef.current) videoRef.current.muted = newMuted;
                      }}
                      className="size-7 p-0 text-muted-foreground hover:text-foreground"
                    >
                      {isMuted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={toggleFullscreen}
                      className="size-7 p-0 text-muted-foreground hover:text-foreground"
                    >
                      <Maximize2 className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Forensic Dossier & Metric Sidebar */}
          <div className="lg:col-span-4 p-5 flex flex-col justify-between bg-card/60 space-y-4 overflow-y-auto">
            <div className="space-y-4">
              <div className="border-b border-border/40 pb-3">
                <span className="text-[10px] font-mono uppercase text-muted-foreground tracking-wider block">
                  Incident Biometric Telemetry
                </span>
                <div className="flex items-center justify-between mt-1">
                  <span className="font-mono font-bold text-sm text-foreground">{incident.incident_id}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={copyIncidentDetails}
                    className="h-6 px-2 text-[10px] text-muted-foreground hover:text-foreground font-mono"
                  >
                    {copied ? <Check className="size-3 text-success mr-1" /> : <Copy className="size-3 mr-1" />}
                    <span>{copied ? 'Copied' : 'Copy Dossier'}</span>
                  </Button>
                </div>
              </div>

              {/* Wrist Reach Metric Highlight Card */}
              <div className="rounded-xl border border-primary/40 bg-primary/10 p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-primary font-mono flex items-center gap-1.5">
                    <Activity className="size-3.5" />
                    <span>HOI Wrist Reach Contact</span>
                  </span>
                  <Badge variant="outline" className="text-[10px] font-mono border-primary/50 text-primary">
                    {incident.active_hand} Hand
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-black font-mono text-foreground tabular-nums">
                    {incident.min_wrist_distance_px.toFixed(1)}
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">pixels from switch / valve boundary</span>
                </div>
                <div className="w-full bg-background/50 h-2 rounded-full overflow-hidden border border-border/40">
                  <div
                    className={cn(
                      'h-full transition-all',
                      incident.min_wrist_distance_px <= 12
                        ? 'bg-destructive w-[95%]'
                        : 'bg-primary w-[60%]'
                    )}
                  />
                </div>
                <span className="text-[10px] font-mono text-muted-foreground block">
                  Contact Threshold: &le; 12.0 px &bull; Interaction: {incident.interaction_type}
                </span>
              </div>

              {/* Forensic Details Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="rounded-lg border border-border/40 bg-background/40 p-2.5">
                  <span className="text-[10px] text-muted-foreground block uppercase">Operational Zone</span>
                  <span className="font-semibold text-foreground truncate block mt-0.5" title={incident.zone_name}>
                    {incident.zone_id}
                  </span>
                  <span className="text-[10px] text-muted-foreground truncate block">{incident.zone_name}</span>
                </div>

                <div className="rounded-lg border border-border/40 bg-background/40 p-2.5">
                  <span className="text-[10px] text-muted-foreground block uppercase">Track / Persona</span>
                  <span className="font-semibold text-foreground truncate block mt-0.5">
                    {incident.track_id || 'OP-RO-VALVE-01'}
                  </span>
                  <span className="text-[10px] text-success block">Verified Operator</span>
                </div>

                <div className="rounded-lg border border-border/40 bg-background/40 p-2.5">
                  <span className="text-[10px] text-muted-foreground block uppercase">Time Window</span>
                  <span className="font-semibold text-foreground block mt-0.5 tabular-nums">
                    {incident.start_time.split(' ')[1] || incident.start_time}
                  </span>
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    to {incident.end_time.split(' ')[1] || incident.end_time}
                  </span>
                </div>

                <div className="rounded-lg border border-border/40 bg-background/40 p-2.5">
                  <span className="text-[10px] text-muted-foreground block uppercase">Peak Contact Time</span>
                  <span className="font-semibold text-primary block mt-0.5 tabular-nums">
                    {incident.peak_time.split(' ')[1] || incident.peak_time}
                  </span>
                  <span className="text-[10px] text-muted-foreground tabular-nums">
                    Duration: {incident.duration_sec.toFixed(1)}s
                  </span>
                </div>
              </div>

              {/* Evidence File Details */}
              <div className="rounded-lg border border-border/40 bg-background/40 p-3 space-y-1 text-xs font-mono">
                <div className="flex items-center justify-between text-muted-foreground text-[10px]">
                  <span>Clip File</span>
                  <span>{incident.file_size_mb ? `${incident.file_size_mb} MB` : '3K Concatenated'}</span>
                </div>
                <div className="text-foreground truncate font-semibold text-[11px]" title={incident.clip_filename}>
                  {incident.clip_filename}
                </div>
              </div>
            </div>

            {/* Action Buttons: Direct Downloads */}
            <div className="pt-3 border-t border-border/40 space-y-2">
              <div className="flex items-center gap-2">
                <a
                  href={videoUrl}
                  download={incident.clip_filename}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 h-8 rounded-md gap-1.5 text-xs font-mono bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center justify-center font-medium transition-colors"
                >
                  <Download className="size-3.5" />
                  <span>Download MP4</span>
                </a>

                {snapshotUrl && (
                  <a
                    href={snapshotUrl}
                    download={incident.snapshot_filename}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 h-8 rounded-md gap-1.5 text-xs font-mono border border-border/70 text-foreground hover:bg-muted/60 inline-flex items-center justify-center font-medium transition-colors"
                  >
                    <Camera className="size-3.5" />
                    <span>Download Snapshot</span>
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
