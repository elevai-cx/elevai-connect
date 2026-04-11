/**
 * Banner — scrolling marquee driven by query parameters.
 *
 * Query params:
 *   message  - Text to display (required). URL-encode special characters.
 *   speed    - Scroll duration in seconds (default: 20). Lower = faster.
 *   bg       - Background colour as a CSS colour value (default: #1e40af — blue-800).
 *   color    - Text colour as a CSS colour value (default: #ffffff).
 *   size     - Font size as a CSS value (default: 1rem).
 *
 * Example:
 *   /banner?message=Hello+World&speed=15&bg=%23dc2626&color=%23fff
 */

import { useSearchParams } from 'react-router-dom'

export default function Banner() {
  const [params] = useSearchParams()

  const message = params.get('message') ?? 'No message provided.'
  const speed   = params.get('speed')   ?? '20'
  const bg      = params.get('bg')      ?? '#1e40af'
  const color   = params.get('color')   ?? '#ffffff'
  const size    = params.get('size')    ?? '1rem'

  return (
    <div
      className="w-full overflow-hidden flex items-center"
      style={{ backgroundColor: bg, height: '100vh' }}
    >
      <div
        className="whitespace-nowrap animate-marquee font-medium"
        style={
          {
            color,
            fontSize: size,
            '--marquee-duration': `${speed}s`,
          } as React.CSSProperties
        }
      >
        {message}
      </div>
    </div>
  )
}
