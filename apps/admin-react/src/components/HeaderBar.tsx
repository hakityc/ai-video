import type { SectionConfig } from '../types'

interface HeaderBarProps {
  activeSection: SectionConfig
  query: string
  onQueryChange: (value: string) => void
}

export function HeaderBar({ activeSection, query, onQueryChange }: HeaderBarProps) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">AI Video 管理后台</p>
        <h2 className="topbar-title">{activeSection.label}</h2>
        <p className="topbar-copy">{activeSection.description}</p>
      </div>

      <div className="topbar-actions">
        <label className="search-box">
          <span className="search-label">搜索角色 / 剧集 / 任务</span>
          <input
            placeholder="例如：tomb-raider / shot-001"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
        <button className="ghost-button" type="button">
          导出日报
        </button>
      </div>
    </header>
  )
}
