import type { DashboardMetrics } from '../types'

interface InsightPanelsProps {
  dashboardMetrics: DashboardMetrics
  issueDistribution: { label: string; value: string }[]
  promptModes: string[]
}

export function InsightPanels({
  dashboardMetrics,
  issueDistribution,
  promptModes,
}: InsightPanelsProps) {
  return (
    <section className="insight-grid">
      <div className="metric-strip">
        {dashboardMetrics.strip.map((metric) => (
          <article key={metric.label} className="metric-card">
            <span className="metric-label">{metric.label}</span>
            <strong className="metric-value">{metric.value}</strong>
            <p className="insight-copy">{metric.note}</p>
          </article>
        ))}
      </div>

      <div className="workspace">
        <article className="insight-card">
          <p className="eyebrow">Prompt 台</p>
          <h3 className="section-title">生成指令草拟</h3>
          <div className="prompt-tags">
            {promptModes.map((mode) => (
              <span key={mode} className="prompt-tag">
                {mode}
              </span>
            ))}
          </div>
          <p className="prompt-copy">
            夜雨环境，角色从街灯下缓慢前进，保持皮夹克与湿发细节，摄像机低位推轨，情绪克制，不改变场景主光源。
          </p>
        </article>

        <article className="insight-card">
          <p className="eyebrow">审核面板</p>
          <h3 className="section-title">最近问题分布</h3>
          <div className="issue-list">
            {issueDistribution.map((issue) => (
              <div key={issue.label} className="issue-row">
                <span className="insight-copy">{issue.label}</span>
                <div className="issue-track">
                  <span className="issue-fill" style={{ ['--size' as string]: issue.value }} />
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  )
}
