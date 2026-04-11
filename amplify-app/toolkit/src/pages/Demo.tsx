/**
 * Demo — interactive showcase of all available toolkit components.
 *
 * Each component card lets you tweak query params and shows a live iframe
 * preview alongside the generated embed URL. Add a new card here whenever
 * a new component is added to the toolkit.
 */

import { useState } from 'react'
import { Copy, Check, ExternalLink } from 'lucide-react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildUrl(base: string, params: Record<string, string>): string {
  const url = new URL(base, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v) url.searchParams.set(k, v)
  })
  return url.toString()
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md border border-border bg-muted hover:bg-accent transition-colors text-muted-foreground"
    >
      {copied ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy URL'}
    </button>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-foreground">{label}</label>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {children}
    </div>
  )
}

const inputCls =
  'w-full text-sm rounded-md border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring'

// ---------------------------------------------------------------------------
// Banner demo
// ---------------------------------------------------------------------------

function BannerDemo() {
  const [message, setMessage] = useState('Important: System maintenance scheduled for Sunday 2 AM – 4 AM.')
  const [speed,   setSpeed]   = useState('20')
  const [bg,      setBg]      = useState('#1e40af')
  const [color,   setColor]   = useState('#ffffff')
  const [size,    setSize]    = useState('1rem')

  const url = buildUrl('/banner', { message, speed, bg, color, size })

  return (
    <ComponentCard
      title="Banner"
      route="/banner"
      description="Scrolling marquee. Embed in a step-by-step guide panel or as a header strip."
      url={url}
      previewHeight={50}
      recommendedHeight="50px"
      controls={
        <>
          <Field label="message" hint="Text to scroll across the screen.">
            <textarea
              className={`${inputCls} resize-none`}
              rows={2}
              value={message}
              onChange={e => setMessage(e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="speed" hint="Duration in seconds. Lower = faster.">
              <input
                type="number"
                min="1"
                max="120"
                className={inputCls}
                value={speed}
                onChange={e => setSpeed(e.target.value)}
              />
            </Field>
            <Field label="size" hint="CSS font-size (e.g. 1rem, 18px).">
              <input
                type="text"
                className={inputCls}
                value={size}
                onChange={e => setSize(e.target.value)}
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="bg" hint="Background colour.">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  className="h-8 w-10 cursor-pointer rounded border border-border"
                  value={bg}
                  onChange={e => setBg(e.target.value)}
                />
                <input
                  type="text"
                  className={`${inputCls} flex-1`}
                  value={bg}
                  onChange={e => setBg(e.target.value)}
                />
              </div>
            </Field>
            <Field label="color" hint="Text colour.">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  className="h-8 w-10 cursor-pointer rounded border border-border"
                  value={color}
                  onChange={e => setColor(e.target.value)}
                />
                <input
                  type="text"
                  className={`${inputCls} flex-1`}
                  value={color}
                  onChange={e => setColor(e.target.value)}
                />
              </div>
            </Field>
          </div>
        </>
      }
    />
  )
}

// ---------------------------------------------------------------------------
// AudioPlayer demo
// ---------------------------------------------------------------------------

const SAMPLE_AUDIO = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'

function AudioPlayerDemo() {
  const [src,   setSrc]   = useState(SAMPLE_AUDIO)
  const [title, setTitle] = useState('SoundHelix Song 1')
  const [color, setColor] = useState('#1e40af')

  const url = buildUrl('/audio-player', { src, title, color })

  return (
    <ComponentCard
      title="Audio Player"
      route="/audio-player"
      description="Minimal play/pause player with a progress bar. Useful for voicemail playback or audio guides."
      url={url}
      previewHeight={200}
      recommendedHeight="200px"
      controls={
        <>
          <Field label="src" hint="Direct URL to an MP3, WAV, or OGG file.">
            <input
              type="text"
              className={inputCls}
              value={src}
              onChange={e => setSrc(e.target.value)}
            />
          </Field>

          <Field label="title" hint="Display name shown above the controls.">
            <input
              type="text"
              className={inputCls}
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
          </Field>

          <Field label="color" hint="Accent colour for the play button and progress bar.">
            <div className="flex items-center gap-2">
              <input
                type="color"
                className="h-8 w-10 cursor-pointer rounded border border-border"
                value={color}
                onChange={e => setColor(e.target.value)}
              />
              <input
                type="text"
                className={`${inputCls} flex-1`}
                value={color}
                onChange={e => setColor(e.target.value)}
              />
            </div>
          </Field>
        </>
      }
    />
  )
}

// ---------------------------------------------------------------------------
// ImageViewer demo
// ---------------------------------------------------------------------------

const SAMPLE_IMAGES = [
  'https://picsum.photos/id/10/400/300',
  'https://picsum.photos/id/20/400/300',
  'https://picsum.photos/id/30/400/300',
]

function ImageViewerDemo() {
  const [sources, setSources] = useState(SAMPLE_IMAGES)
  const [alt, setAlt] = useState('Sample image')
  const [fit, setFit] = useState('contain')
  const [bg,  setBg]  = useState('#f8fafc')

  // Build URL with multiple src params
  const url = (() => {
    const u = new URL('/image-viewer', window.location.origin)
    sources.forEach(s => { if (s) u.searchParams.append('src', s) })
    if (alt) u.searchParams.set('alt', alt)
    if (fit) u.searchParams.set('fit', fit)
    if (bg) u.searchParams.set('bg', bg)
    return u.toString()
  })()

  const updateSource = (i: number, val: string) => {
    setSources(prev => prev.map((s, idx) => idx === i ? val : s))
  }
  const addSource = () => setSources(prev => [...prev, ''])
  const removeSource = (i: number) => setSources(prev => prev.filter((_, idx) => idx !== i))

  return (
    <ComponentCard
      title="Image Viewer"
      route="/image-viewer"
      description="Displays one or more images with carousel navigation. Useful for product photos, diagrams, or reference material."
      url={url}
      previewHeight={250}
      recommendedHeight="250px"
      controls={
        <>
          <Field label="src" hint="Image URLs. Add multiple for a carousel.">
            <div className="space-y-2">
              {sources.map((s, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="text"
                    className={`${inputCls} flex-1`}
                    value={s}
                    placeholder={`Image ${i + 1} URL`}
                    onChange={e => updateSource(i, e.target.value)}
                  />
                  {sources.length > 1 && (
                    <button
                      onClick={() => removeSource(i)}
                      className="text-xs text-muted-foreground hover:text-destructive shrink-0"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addSource}
                className="text-xs text-primary hover:underline"
              >
                + Add image
              </button>
            </div>
          </Field>

          <Field label="alt" hint="Alt text for accessibility.">
            <input
              type="text"
              className={inputCls}
              value={alt}
              onChange={e => setAlt(e.target.value)}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="fit" hint="How the image fits the container.">
              <select
                className={inputCls}
                value={fit}
                onChange={e => setFit(e.target.value)}
              >
                <option value="contain">contain</option>
                <option value="cover">cover</option>
                <option value="fill">fill</option>
                <option value="none">none</option>
              </select>
            </Field>
            <Field label="bg" hint="Background colour behind the image.">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  className="h-8 w-10 cursor-pointer rounded border border-border"
                  value={bg}
                  onChange={e => setBg(e.target.value)}
                />
                <input
                  type="text"
                  className={`${inputCls} flex-1`}
                  value={bg}
                  onChange={e => setBg(e.target.value)}
                />
              </div>
            </Field>
          </div>
        </>
      }
    />
  )
}

// ---------------------------------------------------------------------------
// Shared card shell
// ---------------------------------------------------------------------------

function ComponentCard({
  title,
  route,
  description,
  url,
  previewHeight,
  recommendedHeight,
  controls,
}: {
  title: string
  route: string
  description: string
  url: string
  previewHeight: number
  recommendedHeight?: string
  controls: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
            <code className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{route}</code>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
          {recommendedHeight && (
            <p className="mt-1 text-xs text-muted-foreground">
              Recommended <code className="px-1 py-0.5 rounded bg-muted">--application-height: {recommendedHeight}</code>
            </p>
          )}
        </div>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="ml-4 shrink-0 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Open
        </a>
      </div>

      {/* Body: controls (left) + preview (right) */}
      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border">
        {/* Controls */}
        <div className="p-5 space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Parameters</p>
          {controls}
        </div>

        {/* Preview */}
        <div className="p-5 space-y-3 bg-muted/30">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Preview</p>
            <CopyButton text={url} />
          </div>
          <div
            className="rounded-lg overflow-hidden border border-border bg-background"
            style={{ height: previewHeight }}
          >
            <iframe
              key={url}
              src={url}
              title={`${title} preview`}
              className="w-full h-full"
              style={{ border: 'none' }}
            />
          </div>
          <p className="text-xs text-muted-foreground break-all font-mono leading-relaxed">{url}</p>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Demo() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">

        {/* Page header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-foreground">Elevai Toolkit</h1>
          <p className="text-muted-foreground text-sm">
            A collection of embeddable UI components for Amazon Connect step-by-step guides and external apps.
            Each component is driven entirely by URL query parameters — configure them here, then copy the URL
            into your iframe or Connect flow.
          </p>
        </div>

        {/* Component demos — add new ones here */}
        <BannerDemo />
        <AudioPlayerDemo />
        <ImageViewerDemo />

      </div>
    </div>
  )
}
