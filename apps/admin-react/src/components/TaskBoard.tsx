import type { FilterKey, TaskItem } from '../types'

interface TaskBoardProps {
  activeFilter: FilterKey
  filters: { key: FilterKey; label: string }[]
  selectedTask: TaskItem | null
  tasks: TaskItem[]
  onFilterChange: (filter: FilterKey) => void
  onTaskSelect: (taskId: string) => void
}

export function TaskBoard({
  activeFilter,
  filters,
  selectedTask,
  tasks,
  onFilterChange,
  onTaskSelect,
}: TaskBoardProps) {
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">工作区</p>
          <h3 className="section-title">任务编排与内容生产</h3>
        </div>
        <div className="filter-row">
          {filters.map((filter) => (
            <button
              key={filter.key}
              className={`filter-chip ${activeFilter === filter.key ? 'is-active' : ''}`}
              onClick={() => onFilterChange(filter.key)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      <div className="workspace-grid">
        <div className="task-list" aria-label="任务列表">
          {tasks.length > 0 ? (
            tasks.map((task) => {
              const statusClass = `status-${task.status}`

              return (
                <button
                  key={task.id}
                  className={`task-card ${selectedTask?.id === task.id ? 'is-active' : ''}`}
                  onClick={() => onTaskSelect(task.id)}
                  type="button"
                >
                  <div className="task-card-header">
                    <h4 className="task-title">{task.title}</h4>
                    <span className={`status-pill ${statusClass}`}>{task.statusLabel}</span>
                  </div>
                  <p className="task-summary">{task.summary}</p>
                  <p className="task-meta">阶段：{task.stage}</p>
                </button>
              )
            })
          ) : (
            <article className="task-detail empty-state">
              <div>
                <p className="eyebrow">当前筛选</p>
                <h4 className="detail-title">这个分类下暂时没有任务</h4>
                <p className="empty-copy">你可以切换筛选条件，或者创建新的生成批次。</p>
              </div>
            </article>
          )}
        </div>

        {selectedTask ? (
          <article className="task-detail">
            <div className="task-detail-header">
              <div>
                <p className="eyebrow">任务详情</p>
                <h4 className="detail-title">{selectedTask.title}</h4>
              </div>
              <span className={`status-pill status-${selectedTask.status}`}>
                {selectedTask.statusLabel}
              </span>
            </div>

            <div className="detail-grid">
              <section className="detail-section">
                <strong>阶段</strong>
                <p className="detail-copy">{selectedTask.stage}</p>
              </section>
              <section className="detail-section">
                <strong>执行主体</strong>
                <p className="detail-copy">{selectedTask.owner}</p>
              </section>
              <section className="detail-section">
                <strong>上下文说明</strong>
                <p className="detail-copy">{selectedTask.summary}</p>
              </section>
              <section className="detail-section">
                <strong>输入资产</strong>
                <ul className="detail-list">
                  {selectedTask.assets.map((asset) => (
                    <li key={asset}>{asset}</li>
                  ))}
                </ul>
              </section>
              <section className="detail-section">
                <strong>风险与限制</strong>
                <ul className="detail-list">
                  {selectedTask.issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </section>
              <section className="detail-section">
                <strong>下一步</strong>
                <p className="detail-copy">{selectedTask.nextStep}</p>
              </section>
            </div>

            <div className="detail-actions">
              <button className="primary-button" type="button">
                继续推进
              </button>
              <button className="ghost-button" type="button">
                查看 YAML 配置
              </button>
            </div>
          </article>
        ) : (
          <article className="task-detail empty-state">
            <div>
              <p className="eyebrow">任务详情</p>
              <h4 className="detail-title">没有可展示的任务</h4>
              <p className="empty-copy">调整筛选或搜索条件后，这里会显示对应任务的上下文与动作。</p>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
