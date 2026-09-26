// Generated cover art for a post: a stable SVG pattern per slug, drawn in the current theme colors.
import { useId, useMemo, type ReactNode } from 'react'

import { accentPair, hashString, patternFor, seededRandom, tone, type Accent } from '@/lib/covers'
import { cn } from '@/lib/utils'

const W = 400
const H = 200

type Draw = { a: Accent; b: Accent; rand: () => number; id: string }

function Orbits({ a, b, rand, id }: Draw) {
  const cx = 250 + rand() * 90
  const cy = 70 + rand() * 60
  const tilt = -20 + rand() * 40
  const moon = rand() * Math.PI * 2
  return (
    <g transform={`rotate(${tilt} ${cx} ${cy})`}>
      {[0, 1, 2, 3, 4].map((i) => {
        const rx = 46 + i * 44
        return (
          <ellipse
            key={i}
            cx={cx}
            cy={cy}
            rx={rx}
            ry={rx * 0.36}
            fill="none"
            strokeWidth={1}
            style={{ stroke: tone(i % 2 ? b : a, 60), opacity: 0.75 - i * 0.12 }}
          />
        )
      })}
      <circle cx={cx} cy={cy} r={17} style={{ fill: `url(#${id}-core)` }} />
      <circle
        cx={cx + 90 * Math.cos(moon)}
        cy={cy + 90 * 0.36 * Math.sin(moon)}
        r={4}
        style={{ fill: tone(b, 90) }}
      />
    </g>
  )
}

function Waves({ a, b, rand }: Draw) {
  const phase = rand() * 120
  return (
    <g fill="none" strokeWidth={1.25}>
      {Array.from({ length: 8 }, (_, i) => {
        const y = 36 + i * 20
        const amp = 18 + rand() * 26
        return (
          <path
            key={i}
            d={`M-20 ${y} C ${110 + phase} ${y - amp}, ${250 - phase / 2} ${y + amp}, ${W + 20} ${y - amp / 3}`}
            style={{ stroke: tone(i % 3 ? a : b, 65), opacity: 0.25 + i * 0.07 }}
          />
        )
      })}
    </g>
  )
}

function Constellation({ a, b, rand }: Draw) {
  const stars = Array.from({ length: 13 }, () => ({
    x: 20 + rand() * (W - 40),
    y: 18 + rand() * (H - 36),
    r: 1.2 + rand() * 1.8,
  })).sort((p, q) => p.x - q.x)
  return (
    <g>
      <polyline
        points={stars.map((s) => `${s.x},${s.y}`).join(' ')}
        fill="none"
        strokeWidth={0.8}
        style={{ stroke: tone(b, 55), opacity: 0.7 }}
      />
      {stars.map((s, i) => (
        <g key={i}>
          {i % 4 === 0 && (
            <circle cx={s.x} cy={s.y} r={s.r * 4} style={{ fill: tone(a, 60), opacity: 0.25 }} />
          )}
          <circle cx={s.x} cy={s.y} r={s.r} style={{ fill: tone(a, 95) }} />
        </g>
      ))}
    </g>
  )
}

function DotGrid({ a, rand }: Draw) {
  const freq = 0.25 + rand() * 0.35
  const phase = rand() * Math.PI * 2
  const dots: ReactNode[] = []
  for (let col = 0; col < 20; col++) {
    const peak = 5 + 3.2 * Math.sin(col * freq + phase)
    for (let row = 0; row < 10; row++) {
      const lit = Math.abs(row - peak) < 1
      dots.push(
        <circle
          key={`${col}-${row}`}
          cx={10 + col * 20}
          cy={10 + row * 20}
          r={lit ? 2.6 : 1.2}
          style={{
            fill: lit ? tone(a, 90) : 'color-mix(in oklab, var(--nb-ink) 18%, transparent)',
          }}
        />,
      )
    }
  }
  return <g>{dots}</g>
}

function Blobs({ a, b, rand, id }: Draw) {
  return (
    <g>
      <g filter={`url(#${id}-blur)`}>
        <circle cx={rand() * W} cy={rand() * H} r={90} style={{ fill: tone(a, 55) }} />
        <circle cx={rand() * W} cy={rand() * H} r={70} style={{ fill: tone(b, 50) }} />
      </g>
      <circle
        cx={120 + rand() * 160}
        cy={60 + rand() * 80}
        r={46}
        fill="none"
        strokeWidth={1}
        style={{ stroke: tone(b, 70), opacity: 0.6 }}
      />
    </g>
  )
}

const PATTERN_ART = {
  orbits: Orbits,
  waves: Waves,
  constellation: Constellation,
  grid: DotGrid,
  blobs: Blobs,
}

export function Cover({ seed, className }: { seed: string; className?: string }) {
  const id = `c${useId().replace(/[^a-zA-Z0-9]/g, '')}`
  const [a, b] = useMemo(() => accentPair(seed), [seed])
  // A fresh generator per render, so shapes are identical every time for this seed.
  const draw: Draw = { a, b, rand: seededRandom(hashString(seed)), id }
  const Art = PATTERN_ART[patternFor(seed)]

  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      className={cn('block size-full', className)}
    >
      <defs>
        <radialGradient id={`${id}-glow`} cx="85%" cy="0%" r="90%">
          <stop offset="0" style={{ stopColor: tone(a, 40) }} />
          <stop offset="1" style={{ stopColor: tone(a, 40), stopOpacity: 0 }} />
        </radialGradient>
        <radialGradient id={`${id}-core`} cx="35%" cy="30%" r="75%">
          <stop offset="0" style={{ stopColor: tone(b, 100) }} />
          <stop offset="1" style={{ stopColor: tone(a, 75) }} />
        </radialGradient>
        <filter id={`${id}-blur`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={30} />
        </filter>
      </defs>
      <rect width={W} height={H} style={{ fill: tone(a, 16) }} />
      <rect width={W} height={H} fill={`url(#${id}-glow)`} />
      <Art {...draw} />
    </svg>
  )
}
