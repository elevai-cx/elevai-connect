/**
 * AudioPlayer — minimal play/pause audio player driven by query parameters.
 *
 * Query params:
 *   src    - URL of the audio file to play (required).
 *   title  - Display title shown above the controls (default: 'Audio').
 *   color  - Accent colour for the play button (default: #1e40af — blue-800).
 *
 * Example:
 *   /audio-player?src=https://example.com/message.mp3&title=Voicemail
 */

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Play, Pause, Volume2 } from 'lucide-react'

/**
 * Extract the `src` value from the raw query string.
 *
 * Presigned S3 URLs contain bare `&` characters that `URLSearchParams`
 * treats as parameter delimiters, truncating the URL.  We parse manually:
 * grab everything after `src=` up to the next *app-level* parameter
 * (`&title=` / `&color=`) or end-of-string.
 */
function parseSrc(search: string): string {
  const idx = search.indexOf('src=')
  if (idx === -1) return ''
  let rest = search.substring(idx + 4)
  for (const p of ['&title=', '&color=']) {
    const i = rest.indexOf(p)
    if (i !== -1) rest = rest.substring(0, i)
  }
  return rest
}

export default function AudioPlayer() {
  const [params] = useSearchParams()

  const src    = parseSrc(window.location.search)
  const title  = params.get('title') ?? 'Audio'
  const accent = params.get('color') ?? '#1e40af'

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing,  setPlaying]  = useState(false)
  const [progress, setProgress] = useState(0)   // 0-100
  const [duration, setDuration] = useState(0)
  const [current,  setCurrent]  = useState(0)
  const [error,    setError]    = useState<string | null>(null)

  useEffect(() => {
    if (!src) return
    const audio = new Audio(src)
    audioRef.current = audio

    audio.addEventListener('loadedmetadata', () => setDuration(audio.duration))
    audio.addEventListener('timeupdate', () => {
      setCurrent(audio.currentTime)
      setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0)
    })
    audio.addEventListener('ended', () => setPlaying(false))
    audio.addEventListener('error', () => setError('Failed to load audio.'))

    return () => {
      audio.pause()
      audio.src = ''
    }
  }, [src])

  const togglePlay = () => {
    const audio = audioRef.current
    if (!audio) return
    if (playing) {
      audio.pause()
    } else {
      audio.play().catch(() => setError('Playback blocked by browser.'))
    }
    setPlaying(!playing)
  }

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current
    if (!audio || !duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - rect.left) / rect.width
    audio.currentTime = ratio * duration
  }

  const fmt = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  if (!src) {
    return (
      <div className="flex items-center justify-center h-screen bg-background text-muted-foreground text-sm px-4">
        No audio source provided. Add <code className="mx-1 px-1 bg-muted rounded">?src=…</code> to the URL.
      </div>
    )
  }

  return (
    <div className="w-full h-screen bg-background flex flex-col justify-center px-4 py-3 space-y-3">

      {/* Title row */}
      <div className="flex items-center gap-2 text-foreground">
        <Volume2 className="w-4 h-4 shrink-0" style={{ color: accent }} />
        <span className="font-medium text-sm truncate">{title}</span>
      </div>

      {/* Progress bar */}
      <div
        className="w-full h-2 rounded-full bg-muted cursor-pointer overflow-hidden"
        onClick={seek}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${progress}%`, backgroundColor: accent }}
        />
      </div>

      {/* Time + play button */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground tabular-nums">
          {fmt(current)} / {fmt(duration)}
        </span>

        <button
          onClick={togglePlay}
          className="flex items-center justify-center w-10 h-10 rounded-full text-white transition-opacity hover:opacity-80 active:opacity-60"
          style={{ backgroundColor: accent }}
          aria-label={playing ? 'Pause' : 'Play'}
        >
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  )
}
