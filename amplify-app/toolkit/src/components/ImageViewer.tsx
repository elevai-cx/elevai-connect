/**
 * ImageViewer — displays one or more images with navigation, driven by query parameters.
 *
 * Query params:
 *   src   - URL of an image (required, repeatable for multiple images).
 *   alt   - Alt text for accessibility (default: 'Image').
 *   fit   - CSS object-fit value (default: contain). Options: contain, cover, fill, none.
 *   bg    - Background colour behind the image (default: transparent).
 *
 * Examples:
 *   Single image:
 *     /image-viewer?src=https://picsum.photos/400/300
 *
 *   Multiple images (carousel):
 *     /image-viewer?src=https://picsum.photos/id/10/400/300&src=https://picsum.photos/id/20/400/300
 */

import { useSearchParams } from 'react-router-dom'
import { ImageOff, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState } from 'react'

export default function ImageViewer() {
  const [params] = useSearchParams()

  const sources = params.getAll('src').filter(Boolean)
  const alt = params.get('alt') ?? 'Image'
  const fit = params.get('fit') ?? 'contain'
  const bg  = params.get('bg')  ?? 'transparent'

  const [index, setIndex] = useState(0)
  const [failedSet, setFailedSet] = useState<Set<number>>(() => new Set())

  if (sources.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-background text-muted-foreground text-sm px-4">
        No image source provided. Add <code className="mx-1 px-1 bg-muted rounded">?src=…</code> to the URL.
      </div>
    )
  }

  const currentSrc = sources[index]
  const hasPrev = index > 0
  const hasNext = index < sources.length - 1
  const multi = sources.length > 1

  const handleError = () => {
    setFailedSet(prev => new Set(prev).add(index))
  }

  return (
    <div
      className="w-full h-screen flex items-center justify-center relative overflow-hidden"
      style={{ backgroundColor: bg }}
    >
      {failedSet.has(index) ? (
        <div className="flex flex-col items-center text-muted-foreground text-sm gap-2">
          <ImageOff className="w-6 h-6" />
          <span>Failed to load image.</span>
        </div>
      ) : (
        <img
          key={index}
          src={currentSrc}
          alt={`${alt}${multi ? ` ${index + 1}` : ''}`}
          onError={handleError}
          className="max-w-full max-h-full"
          style={{ objectFit: fit as React.CSSProperties['objectFit'] }}
        />
      )}

      {/* Navigation */}
      {multi && (
        <>
          <button
            onClick={() => setIndex(i => i - 1)}
            disabled={!hasPrev}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 disabled:opacity-30 disabled:cursor-default transition-colors"
            aria-label="Previous image"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => setIndex(i => i + 1)}
            disabled={!hasNext}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 disabled:opacity-30 disabled:cursor-default transition-colors"
            aria-label="Next image"
          >
            <ChevronRight className="w-5 h-5" />
          </button>

          {/* Dots indicator */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
            {sources.map((_, i) => (
              <button
                key={i}
                onClick={() => setIndex(i)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  i === index ? 'bg-white' : 'bg-white/40'
                }`}
                aria-label={`Image ${i + 1}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
