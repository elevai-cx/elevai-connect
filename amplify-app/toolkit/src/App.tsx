/**
 * Toolkit App — root component
 *
 * Each route maps to a reusable UI component that can be embedded inside
 * Amazon Connect step-by-step guides or external applications via an iframe.
 * Components are driven entirely by URL query parameters — no Connect SDK needed.
 *
 * Routes:
 *   /banner        → Scrolling marquee banner driven by ?message=...&speed=...&bg=...
 *   /audio-player  → Audio player with play/pause driven by ?src=...&title=...
 *
 * Adding a new component:
 *   1. Create src/components/MyComponent.tsx
 *   2. Add a <Route path="/my-component" element={<MyComponent />} /> below
 *   3. Embed it: <iframe src="https://<toolkit-url>/my-component?param=value" />
 */

import { Routes, Route } from 'react-router-dom'
import Home from '@/pages/Home'
import Demo from '@/pages/Demo'
import Banner from '@/components/Banner'
import AudioPlayer from '@/components/AudioPlayer'
import ImageViewer from '@/components/ImageViewer'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/demo" element={<Demo />} />
      <Route path="/banner" element={<Banner />} />
      <Route path="/audio-player" element={<AudioPlayer />} />
      <Route path="/image-viewer" element={<ImageViewer />} />
    </Routes>
  )
}
