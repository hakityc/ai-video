import type { SectionConfig, StatItem } from '../types'

interface HeroPanelProps {
  section: SectionConfig
  metrics: StatItem[]
}

export function HeroPanel({ section, metrics }: HeroPanelProps) {
  return (
    <section className="hero-card">
      <div>
        <p className="eyebrow">{section.kicker}</p>
        <h3 className="hero-title">{section.title}</h3>
        <p className="hero-copy">{section.description}</p>
      </div>

      <div className="hero-metrics">
        {metrics.map((metric) => (
          <article key={metric.label} className="hero-stat">
            <span className="hero-stat-label">{metric.label}</span>
            <strong className="hero-stat-value">{metric.value}</strong>
            <small className="hero-stat-label">{metric.note}</small>
          </article>
        ))}
      </div>
    </section>
  )
}
