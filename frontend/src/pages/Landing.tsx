import {
  Camera,
  ClipboardCheck,
  Sparkles,
  ShieldCheck,
  Store,
  FileSearch,
  Leaf,
  Utensils,
  MessageSquareWarning,
  ArrowRight,
} from 'lucide-react'
import { LinkButton } from '@/components/ui/LinkButton'
import { Reveal } from '@/components/motion/Reveal'
import { FeatureCard } from '@/components/marketing/FeatureCard'
import { useParallax } from '@/hooks/useParallax'

const FEATURES = [
  {
    icon: Camera,
    title: 'Report with evidence',
    description: 'File a food safety report in minutes with photo evidence of the concern.',
  },
  {
    icon: Sparkles,
    title: 'Preliminary AI assessment',
    description: 'Get an instant, transparent preliminary visual read while your report awaits human review.',
  },
  {
    icon: ClipboardCheck,
    title: 'Track every step',
    description: 'Follow your report and complaint from submission through resolution.',
  },
]

const JOURNEY = [
  {
    icon: Store,
    title: 'Explore restaurants',
    description: 'Browse the restaurants in your community that are part of the FoodGuard network.',
  },
  {
    icon: FileSearch,
    title: 'Inspect food reports',
    description: 'See how concerns are documented — photos, descriptions, and current status.',
  },
  {
    icon: Sparkles,
    title: 'Understand AI insights',
    description: 'Every report gets a preliminary visual read to flag possible concerns for human review.',
  },
  {
    icon: MessageSquareWarning,
    title: 'Raise a complaint',
    description: 'Turn a submitted report into a formal complaint that reviewers track to resolution.',
  },
]

export default function Landing() {
  const blobLayer = useParallax<HTMLDivElement>(0.15)
  const contentLayer = useParallax<HTMLDivElement>(-0.05)

  return (
    <div className="min-h-screen overflow-x-clip bg-neutral-25">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-7 text-primary-700" aria-hidden="true" />
          <span className="text-lg font-semibold text-neutral-900">FoodGuard AI</span>
        </div>
        <div className="flex items-center gap-3">
          <LinkButton to="/login" variant="ghost">Sign in</LinkButton>
          <LinkButton to="/register">Get started</LinkButton>
        </div>
      </header>

      <main>
        {/* ---------------------------------------------------------------- */}
        {/* Cinematic hero                                                    */}
        {/* ---------------------------------------------------------------- */}
        <section className="relative isolate overflow-hidden">
          <div
            ref={blobLayer}
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary-950 via-primary-900 to-neutral-25"
          >
            <div className="absolute left-[8%] top-[10%] size-72 rounded-full bg-primary-500/30 blur-3xl animate-float" />
            <div
              className="absolute right-[10%] top-[30%] size-96 rounded-full bg-primary-300/20 blur-3xl animate-float"
              style={{ animationDelay: '1.5s' }}
            />
            <div
              className="absolute left-[30%] top-[55%] size-64 rounded-full bg-warning-500/10 blur-3xl animate-float"
              style={{ animationDelay: '3s' }}
            />
            <svg className="absolute inset-0 size-full opacity-[0.04] mix-blend-overlay" aria-hidden="true">
              <filter id="grain">
                <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
              </filter>
              <rect width="100%" height="100%" filter="url(#grain)" />
            </svg>
          </div>

          <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 hidden sm:block">
            <Utensils className="absolute left-[12%] top-[22%] size-6 text-white/20 animate-float" />
            <Leaf
              className="absolute right-[18%] top-[18%] size-5 text-white/20 animate-float"
              style={{ animationDelay: '2s' }}
            />
            <Sparkles
              className="absolute right-[28%] top-[42%] size-5 text-white/25 animate-float"
              style={{ animationDelay: '4s' }}
            />
          </div>

          <div ref={contentLayer} className="mx-auto max-w-4xl px-6 pb-28 pt-24 text-center sm:pt-32">
            <Reveal variant="fade">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white backdrop-blur">
                <Sparkles className="size-3.5" aria-hidden="true" />
                Civic food-safety reporting
              </span>
            </Reveal>
            <Reveal delay={80}>
              <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white sm:text-6xl">
                Explore Food.
                <br />
                Understand What You Eat.
              </h1>
            </Reveal>
            <Reveal delay={160}>
              <p className="mx-auto mt-5 max-w-2xl text-lg text-white/70">
                Discover restaurants, inspect food reports, and see a preliminary AI read on every
                concern — so you can report issues with evidence and eat with confidence.
              </p>
            </Reveal>
            <Reveal delay={240}>
              <div className="mt-8 flex items-center justify-center gap-3">
                <LinkButton to="/register" size="lg">Create a report</LinkButton>
                <LinkButton to="/login" size="lg" variant="outline">
                  Sign in
                </LinkButton>
              </div>
            </Reveal>
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Food exploration journey                                          */}
        {/* ---------------------------------------------------------------- */}
        <section className="mx-auto max-w-6xl px-6 py-24">
          <Reveal variant="fade" className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary-600">
              Explore with FoodGuard
            </span>
            <h2 className="mx-auto mt-3 max-w-xl text-2xl font-semibold tracking-tight text-neutral-900 sm:text-3xl">
              From discovery to accountability
            </h2>
          </Reveal>

          <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {JOURNEY.map((step, i) => (
              <Reveal key={step.title} delay={i * 90}>
                <FeatureCard icon={step.icon} title={step.title} description={step.description} />
              </Reveal>
            ))}
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Product features                                                  */}
        {/* ---------------------------------------------------------------- */}
        <section className="mx-auto max-w-5xl px-6 pb-24">
          <div className="grid gap-6 sm:grid-cols-3">
            {FEATURES.map((feature, i) => (
              <Reveal key={feature.title} delay={i * 90}>
                <FeatureCard icon={feature.icon} title={feature.title} description={feature.description} />
              </Reveal>
            ))}
          </div>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Final CTA                                                         */}
        {/* ---------------------------------------------------------------- */}
        <section className="mx-auto max-w-4xl px-6 pb-24">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl bg-primary-900 px-8 py-14 text-center shadow-popover sm:px-16">
              <div className="pointer-events-none absolute -left-10 -top-10 size-56 rounded-full bg-primary-500/20 blur-3xl animate-float" />
              <div
                className="pointer-events-none absolute -bottom-10 -right-10 size-56 rounded-full bg-warning-500/10 blur-3xl animate-float"
                style={{ animationDelay: '2s' }}
              />
              <h2 className="relative text-2xl font-semibold text-white sm:text-3xl">
                Ready to eat with confidence?
              </h2>
              <p className="relative mx-auto mt-3 max-w-md text-white/70">
                Create your account and file your first report in minutes.
              </p>
              <div className="relative mt-7 flex items-center justify-center gap-3">
                <LinkButton to="/register" size="lg">
                  Get started
                  <ArrowRight className="size-4" aria-hidden="true" />
                </LinkButton>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="border-t border-neutral-100 py-8 text-center text-sm text-neutral-400">
        FoodGuard AI — preliminary AI assessments are not a food-safety certification.
      </footer>
    </div>
  )
}
