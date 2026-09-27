import { Compass } from 'lucide-react'
import { LinkButton } from '@/components/ui/LinkButton'
import { Reveal } from '@/components/motion/Reveal'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-neutral-25 px-6 text-center">
      <Reveal className="flex flex-col items-center gap-4">
        <Compass className="size-10 text-neutral-300 animate-float" aria-hidden="true" />
        <h1 className="text-2xl font-semibold text-neutral-900">Page not found</h1>
        <p className="max-w-sm text-sm text-neutral-500">The page you're looking for doesn't exist or may have moved.</p>
        <LinkButton to="/">Back to home</LinkButton>
      </Reveal>
    </div>
  )
}
