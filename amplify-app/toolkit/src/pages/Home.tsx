import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
      <h1 className="text-2xl font-bold text-foreground">Elevai Toolkit</h1>
      <p className="mt-2 text-sm text-muted-foreground text-center max-w-md">
        Embeddable UI components for Amazon Connect step-by-step guides.
      </p>
      <Link
        to="/demo"
        className="mt-4 text-sm text-primary hover:underline"
      >
        View component demos
      </Link>
    </div>
  )
}
