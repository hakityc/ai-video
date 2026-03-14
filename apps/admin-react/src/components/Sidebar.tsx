import type { SectionConfig, SectionKey } from '../types'

interface SidebarProps {
  activeSection: SectionKey
  sections: Record<SectionKey, SectionConfig>
  weeklyTargets: string[]
  quickActions: string[]
  onSectionChange: (section: SectionKey) => void
}

export function Sidebar({
  activeSection,
  sections,
  weeklyTargets,
  quickActions,
  onSectionChange,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">AV</div>
        <div>
          <p className="eyebrow">Control Plane</p>
          <h1 className="brand-title">Studio Console</h1>
        </div>
      </div>

      <nav className="nav" aria-label="主导航">
        {Object.values(sections).map((section) => (
          <button
            key={section.key}
            className={`nav-button ${activeSection === section.key ? 'is-active' : ''}`}
            onClick={() => onSectionChange(section.key)}
            type="button"
          >
            {section.label}
          </button>
        ))}
      </nav>

      <section className="sidebar-card">
        <p className="eyebrow">本周目标</p>
        <h2 className="sidebar-title">把角色、场景、镜头模板纳入同一个工作流</h2>
        <ul className="target-list">
          {weeklyTargets.map((target) => (
            <li key={target}>{target}</li>
          ))}
        </ul>
      </section>

      <section className="sidebar-card">
        <p className="eyebrow">立即动作</p>
        <div className="action-stack">
          <button className="primary-button" type="button">
            {quickActions[0]}
          </button>
          {quickActions.slice(1).map((action) => (
            <button key={action} className="ghost-button" type="button">
              {action}
            </button>
          ))}
        </div>
      </section>
    </aside>
  )
}
