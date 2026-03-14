import {
  Sparkles,
  ShieldCheck,
  Settings2,
} from "lucide-react"
import type { NavigationItem, PrimaryKey, ProviderConnection } from "../types"

export const navigation: NavigationItem[] = [
  {
    key: "generation",
    label: "生成中心",
    description: "把文案、角色、资产、剧集、任务和视频产出收在一个工作台。",
    icon: Sparkles,
    sections: [
      { key: "scripts", label: "文案脚本", hint: "生成文案与文案库" },
      { key: "characters", label: "角色管理", hint: "生成角色与角色库" },
      { key: "assets", label: "资产设定", hint: "场景、道具、镜头模板" },
      { key: "episodes", label: "剧集生成", hint: "候选搜索与整集渲染" },
      { key: "jobs", label: "单条任务", hint: "手工任务与局部渲染" },
      { key: "outputs", label: "视频成果", hint: "分类查看成片输出" },
    ],
  },
  {
    key: "qa",
    label: "一致性 QA",
    description: "围绕角色一致性做关键帧、整集和桥接帧的闭环复核。",
    icon: ShieldCheck,
    sections: [
      { key: "overview", label: "待处理", hint: "先做最需要处理的 QA" },
      { key: "episodes", label: "整集复核", hint: "关键分数、问题与操作" },
      { key: "bridge", label: "桥接帧", hint: "重选 bridge frame" },
    ],
  },
  {
    key: "settings",
    label: "系统设置",
    description: "把供应商、模型策略和默认参数统一配好，生成页会直接读取。",
    icon: Settings2,
    sections: [
      { key: "providers", label: "供应商接入", hint: "API 地址、Key、本地服务" },
      { key: "models", label: "模型策略", hint: "默认模型与可选模型库" },
      { key: "defaults", label: "默认参数", hint: "比例、时长、分辨率" },
    ],
  },
]

export const defaultSecondaryState = navigation.reduce<Record<PrimaryKey, string>>((result, item) => {
  result[item.key] = item.sections[0]?.key ?? "overview"
  return result
}, {} as Record<PrimaryKey, string>)

export const taskKindLabels: Record<string, { category: "generation" | "rendering" | "qa"; label: string }> = {
  generate_script: { category: "generation", label: "文案生成" },
  generate_character: { category: "generation", label: "角色生成" },
  search_keyframes: { category: "generation", label: "候选搜索" },
  render_shortform: { category: "rendering", label: "整集渲染" },
  render_job: { category: "rendering", label: "单条渲染" },
  review_episode: { category: "qa", label: "整集复核" },
  review_keyframes: { category: "qa", label: "关键帧复核" },
  review_master_scene: { category: "qa", label: "主场景复核" },
  select_bridge_frame: { category: "qa", label: "桥接帧筛选" },
}

export const scriptLengthOptions = [
  { value: "flash", label: "快闪开场", estimate: "约 3-5 秒", guidance: "适合一句钩子和一个动作镜头。" },
  { value: "short", label: "标准短视频", estimate: "约 8-12 秒", guidance: "适合 3 到 5 个镜头节拍。" },
  { value: "medium", label: "完整短段落", estimate: "约 15-20 秒", guidance: "适合角色关系和冲突推进。" },
  { value: "long", label: "扩展叙事", estimate: "约 25-35 秒", guidance: "适合完整一小段情节。" },
]

export const characterPresetOptions = [
  { value: "standard", label: "快速双视图", description: "正脸 + 3/4 视角，适合快速定方向。" },
  { value: "turnaround", label: "稳定四视图", description: "补侧脸和全身，更适合后续一致性生产。" },
]

export const characterConsistencyTags = [
  "面部特征锁定",
  "发型稳定",
  "服装细节锁定",
  "配饰不能丢",
  "镜头切换不漂移",
  "多人同场要清楚主次",
]

export const scriptSeedPresets = [
  {
    title: "深夜便利店异响",
    slug: "late-night-store-whisper",
    concept: "深夜便利店只剩一名店员值班，收银机和自动门开始不合时宜地响应，像在提醒她店里还有另一个看不见的存在。",
    seed_text: "凌晨两点，便利店里没有客人，但收银机突然自己吐出一张小票。",
    tone: "悬疑、口语化、适合 10 到 15 秒链式短视频，镜头信息明确。",
    length_profile: "short" as const,
  },
  {
    title: "旧地铁末班之后",
    slug: "last-train-afterhours",
    concept: "停运后的老地铁站里，女站务员听见广播在重复一个并不存在的班次，她必须在废弃站台里找到声音来源。",
    seed_text: "最后一班车离开后，站台的广播却还在报站。",
    tone: "都市怪谈、真实感、镜头节奏清晰，便于拆成 4 到 5 个镜头。",
    length_profile: "medium" as const,
  },
  {
    title: "雨夜霓虹追踪",
    slug: "neon-rain-pursuit",
    concept: "女主在雨夜霓虹街区跟踪一个看似熟悉的人，却发现对方每次回头，脸都不太一样。",
    seed_text: "她追了三条街，前面那个人始终不快不慢，可每次回头都像换了一个人。",
    tone: "电影感、压迫感、短促有钩子，适合角色一致性测试。",
    length_profile: "short" as const,
  },
]

export const characterSeedPresets = [
  {
    slug: "night-shift-clerk",
    concept: "二十多岁东亚女性，夜班便利店店员，黑色短发，略显疲惫但警觉，深色工服外套，胸牌 and 工作腰包是固定识别物，真实电影感。",
    relationship_hint: "她和便利店夜间常客彼此熟悉，但都在隐瞒一件事。",
    story_anchor: "便利店白色冷光、收银台、小票、玻璃门倒影不能变。",
    consistency_tags: ["面部特征锁定", "服装细节锁定", "配饰不能丢"],
    reference_preset: "turnaround",
  },
  {
    slug: "metro-duty-officer",
    concept: "三十岁左右东亚女性，旧地铁夜间站务员，中长发，黑框眼镜，深色制服外套，红色工作牌，克制冷静，城市纪实风格。",
    relationship_hint: "她和站务长互相提防又互相依赖。",
    story_anchor: "旧站台、广播噪音、红色工作牌、泛黄灯光不能漂移。",
    consistency_tags: ["面部特征锁定", "发型稳定", "镜头切换不漂移"],
    reference_preset: "turnaround",
  },
  {
    slug: "alley-investigator",
    concept: "三十岁东亚女性调查员，短发或低马尾，深灰风衣，功能性腰带和肩包，神情克制，雨夜霓虹城市质感，现实向电影风。",
    relationship_hint: "她和被跟踪对象像旧识，也像互相试探的对手。",
    story_anchor: "湿地反光、霓虹蓝红、风衣剪影和肩包位置不能变。",
    consistency_tags: ["面部特征锁定", "服装细节锁定", "镜头切换不漂移"],
    reference_preset: "turnaround",
  },
]

export const jobSeedPresets = [
  {
    id: "bridge-closeup",
    scene_brief: "中近景，角色停在门口回头，先稳住视线，再轻微迈步，镜头保持缓慢推进，重点测试脸和工作牌的一致性。",
    camera_plan: "镜头前 2 秒稳定，中段轻微推进，不要大幅摇晃；动作幅度小但表情要有迟疑变化。",
    storyboard_notes: "1. 站定回头；2. 视线锁定门外；3. 微弱后撤一步；4. 保持同一服装和胸牌位置。",
    seed: 42,
    fps: 16,
    num_frames: 81,
  },
  {
    id: "walking-medium",
    scene_brief: "中景跟拍，角色沿狭窄通道向前走，两侧环境缓慢掠过，重点测试行走时头发、外套和脸型是否稳定。",
    camera_plan: "轻微手持跟随，步伐不要太快，画面节奏均匀，环境只做低幅度运动。",
    storyboard_notes: "1. 起步；2. 走过一个灯源；3. 轻微回头；4. 继续向前。",
    seed: 84,
    fps: 16,
    num_frames: 81,
  },
]

export const providerPresetOptions: Array<{
  key: string
  label: string
  provider_type: ProviderConnection["provider_type"]
  base_url?: string
  note: string
  local_model?: string
  text_model?: string
  image_model?: string
  video_model?: string
  recommended_models?: {
    text?: string[]
    image?: string[]
    video?: string[]
  }
}> = [
  {
    key: "volcengine-ark",
    label: "火山方舟",
    provider_type: "openai-compatible",
    base_url: "https://ark.cn-beijing.volces.com/api/v3",
    note: "当前项目最常用的统一模型入口。",
  },
  {
    key: "siliconflow",
    label: "硅基流动",
    provider_type: "openai-compatible",
    base_url: "https://api.siliconflow.cn/v1",
    note: "适合补充文本和图片模型来源。",
  },
  {
    key: "openai-compatible",
    label: "OpenAI 兼容",
    provider_type: "openai-compatible",
    base_url: "https://api.openai.com/v1",
    note: "适合任意兼容 OpenAI 协议的平台。",
  },
  {
    key: "zynkapi",
    label: "Zynk API",
    provider_type: "openai-compatible",
    base_url: "https://zynkapi.com/v1",
    text_model: "deepseek-chat",
    image_model: "dall-e-3",
    note: "官方公开的是 OpenAI 兼容入口，适合统一接文本与图片模型；视频能力按账号开通情况再补充。",
    recommended_models: {
      text: ["deepseek-chat", "deepseek-reasoner", "claude-3-5-sonnet-20240620", "gpt-4o", "gpt-4-turbo"],
      image: ["dall-e-3", "dall-e-2"],
      video: [],
    },
  },
  {
    key: "bigmodel",
    label: "智谱开放平台",
    provider_type: "openai-compatible",
    base_url: "https://open.bigmodel.cn/api/paas/v4",
    text_model: "glm-4-flash",
    note: "已预置免费高效的 glm-4-flash 模型。这里已改为通用网关接口地址，以便支持生图生视频。",
    recommended_models: {
      text: ["glm-4-plus", "glm-4-0520", "glm-4-air", "glm-4-flash", "glm-4-flashx"],
      image: ["cogview-3-plus", "cogview-3"],
      video: ["cogvideox"],
    },
  },
  {
    key: "comfyui-local",
    label: "ComfyUI",
    provider_type: "comfyui",
    base_url: "http://127.0.0.1:8188",
    note: "本地工作流渲染服务。",
  },
  {
    key: "cogvideox-local",
    label: "CogVideoX",
    provider_type: "cogvideox",
    local_model: "THUDM/CogVideoX-5b-I2V",
    note: "本地视频模型。",
  },
  {
    key: "custom",
    label: "自定义",
    provider_type: "custom",
    note: "可自行填写地址、密钥和额外参数。",
  },
]
