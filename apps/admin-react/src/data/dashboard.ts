import type { DashboardMetrics, FilterKey, SectionConfig, TaskItem } from '../types'

export const sections: Record<SectionConfig['key'], SectionConfig> = {
  overview: {
    key: 'overview',
    label: '总览中控',
    kicker: 'Content Operations Deck',
    title: '把资产、生成、审核和修复压进一个控制台',
    description:
      '这版后台按 AI 视频工作流设计，不再是通用 CMS。角色包、镜头模板、生成任务、审核失败和 repair 都在同一个操作面里。',
    workspaceTitle: '任务编排与内容生产',
    scope: 'all',
    defaultFilter: 'all',
  },
  assets: {
    key: 'assets',
    label: '资产管理',
    kicker: 'Asset Library System',
    title: '让角色、场景、道具和镜头模板都变成可复用资产',
    description:
      '适合先把参考图、服装锁定、场景锚点和镜头模板收拢起来，避免每次生成都从零开始。',
    workspaceTitle: '资产相关内容与依赖任务',
    scope: 'assets',
    defaultFilter: 'all',
  },
  generation: {
    key: 'generation',
    label: '生成编排',
    kicker: 'Generation Orchestrator',
    title: '盯住整个生成链路，而不是盯住一堆孤立 prompt',
    description:
      '把 master scene、shot delta、bridge frame 和生成队列真正连起来，让内容生产是可追踪、可调度的。',
    workspaceTitle: '生成任务与链路调度',
    scope: 'generation',
    defaultFilter: 'running',
  },
  review: {
    key: 'review',
    label: '审核修复',
    kicker: 'QA And Repair Desk',
    title: '把审核失败变成明确的修复入口，而不是靠人工记忆',
    description:
      '身份漂移、服装变化、背景跳变都应该进入结构化问题池，并且回写到下一步 repair 或重生成。',
    workspaceTitle: '待审核与待修复任务',
    scope: 'review',
    defaultFilter: 'review',
  },
}

export const filters: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '生成中' },
  { key: 'review', label: '待审核' },
  { key: 'repair', label: '待修复' },
]

export const dashboardMetrics: DashboardMetrics = {
  hero: [
    { label: '角色包', value: '12', note: '本周新增 3 个可复用角色' },
    { label: '待生成镜头', value: '28', note: '含 9 个桥接帧续生成任务' },
    { label: 'QA 通过率', value: '91%', note: '比上周提升 6%' },
  ],
  strip: [
    { label: '在产剧集', value: '04', note: '长线内容并行推进' },
    { label: '场景模板', value: '17', note: '支持复用的镜头结构' },
    { label: '待修复帧', value: '06', note: '主要是身份与服装偏差' },
    { label: '今日产出', value: '13', note: '视频片段已进入审核池' },
  ],
}

export const weeklyTargets = [
  '固定角色包与参考图',
  '建立桥接帧续生成链路',
  '把 QA 结果回写到任务队列',
]

export const quickActions = [
  '创建新内容批次',
  '批量导入角色资产',
  '导出生成日报',
]

export const promptModes = ['Master Scene', 'Shot Delta', 'Bridge Frame']

export const issueDistribution = [
  { label: '身份漂移', value: '82%' },
  { label: '服装变化', value: '56%' },
  { label: '背景跳变', value: '39%' },
  { label: '镜头节奏', value: '28%' },
]

export const taskQueue: TaskItem[] = [
  {
    id: 'shot-014',
    title: 'EP004 / Shot-014 桥接续生成',
    status: 'running',
    statusLabel: '生成中',
    section: 'generation',
    summary: '使用上一镜头尾帧作为 first_frame，当前批准关键帧作为 last_frame。',
    owner: 'Seedance 1.5 Pro',
    stage: 'Bridge Frame Generation',
    assets: ['lara_v2_character_pack', 'rain_street_scene', 'bridge_motion_template'],
    issues: ['需要保持皮夹克反光', '禁止重写主光方向'],
    nextStep: '等待输出视频并抽帧进入 QA。',
  },
  {
    id: 'asset-pack-07',
    title: 'Asset / Lara 角色包补全',
    status: 'review',
    statusLabel: '待审核',
    section: 'assets',
    summary: '新补入 4 张服装参考图，等待审核后进入主角色资产库。',
    owner: 'Reference Intake',
    stage: 'Asset Approval',
    assets: ['lara_reference_pack', 'jacket_variants', 'wet_hair_closeups'],
    issues: ['候选 02 侧脸偏差较大', '候选 04 光比不稳定'],
    nextStep: '批准 2 张参考图并更新 generation metadata。',
  },
  {
    id: 'review-ep003-08',
    title: 'EP003 / Shot-008 身份一致性复核',
    status: 'review',
    statusLabel: '待审核',
    section: 'review',
    summary: '抽帧结果显示中段面部相似度下降，需确认是否进入 repair。',
    owner: 'InsightFace QA',
    stage: 'Identity Review',
    assets: ['lara_reference_pack', 'ep003_shot_008_frames'],
    issues: ['第 41 帧相似度 0.71', '湿发细节变成短发轮廓'],
    nextStep: '人工确认失败帧是否需要局部修复。',
  },
  {
    id: 'repair-006',
    title: 'Repair / Frame-006 局部修复',
    status: 'repair',
    statusLabel: '待修复',
    section: 'review',
    summary: '服装从黑色皮夹克漂移到深灰风衣，需要区域蒙版修复。',
    owner: 'Inpaint Pipeline',
    stage: 'Targeted Repair',
    assets: ['sam2_mask_face_cloth', 'failed_frame_006', 'jacket_reference'],
    issues: ['服装款式漂移', '肩线轮廓变窄'],
    nextStep: '调用局部修复流程后重新做身份评分。',
  },
  {
    id: 'master-scene-02',
    title: 'Master Scene / 工业走廊候选筛选',
    status: 'review',
    statusLabel: '待审核',
    section: 'generation',
    summary: '8 张候选场景图已生成，等待挑选后进入 shot delta 阶段。',
    owner: 'Candidate Search',
    stage: 'Master Scene Approval',
    assets: ['industrial_corridor_scene', 'lighting_reference_board'],
    issues: ['候选 03 灯带过亮', '候选 07 景深过浅'],
    nextStep: '批准 1 张主场景图并冻结场景锚点。',
  },
]
