interface LogoProps {
  size?: number
  className?: string
}

export function Logo({ size = 32, className }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      fill="none"
      width={size}
      height={size}
      className={className}
      aria-label="3h2Os"
    >
      <defs>
        <linearGradient id="waveGradient" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" style={{ stopColor: "#2563EB" }} />
          <stop offset="100%" style={{ stopColor: "#22D3EE" }} />
        </linearGradient>
      </defs>
      <path
        d="M15 75 C 40 45, 60 95, 90 65"
        stroke="url(#waveGradient)"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <path
        d="M15 55 C 40 25, 60 75, 90 45"
        stroke="url(#waveGradient)"
        strokeWidth="12"
        strokeLinecap="round"
        opacity="0.85"
      />
      <path
        d="M15 35 C 40 5, 60 55, 90 25"
        stroke="url(#waveGradient)"
        strokeWidth="12"
        strokeLinecap="round"
        opacity="0.7"
      />
    </svg>
  )
}
