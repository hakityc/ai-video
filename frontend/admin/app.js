const queueItems = [
  {
    id: "shot-014",
    title: "EP004 / Shot-014 桥接续生成",
    status: "running",
    statusLabel: "生成中",
    summary: "使用上一镜头尾帧作为 first_frame，当前批准关键帧作为 last_frame。",
    owner: "Seedance 1.5 Pro",
    stage: "Bridge Frame Generation",
    assets: ["lara_v2_character_pack", "rain-street_scene", "bridge-motion_template"],
    issues: ["需要保持皮夹克反光", "禁止重写主光方向"],
    nextStep: "等待输出视频并抽帧进入 QA。",
  },
  {
    id: "review-ep003-08",
    title: "EP003 / Shot-008 身份一致性复核",
    status: "review",
    statusLabel: "待审核",
    summary: "抽帧结果显示中段面部相似度下降，需确认是否进入 repair。",
    owner: "InsightFace QA",
    stage: "Identity Review",
    assets: ["lara_reference_pack", "ep003_shot_008_frames"],
    issues: ["第 41 帧相似度 0.71", "湿发细节变成短发轮廓"],
    nextStep: "人工确认失败帧是否需要局部修复。",
  },
  {
    id: "repair-006",
    title: "Repair / Frame-006 局部修复",
    status: "repair",
    statusLabel: "待修复",
    summary: "服装从黑色皮夹克漂移到深灰风衣，需要区域蒙版修复。",
    owner: "Inpaint Pipeline",
    stage: "Targeted Repair",
    assets: ["sam2_mask_face_cloth", "failed_frame_006", "jacket_reference"],
    issues: ["服装款式漂移", "肩线轮廓变窄"],
    nextStep: "调用局部修复流程后重新做身份评分。",
  },
  {
    id: "master-scene-02",
    title: "Master Scene / 工业走廊候选筛选",
    status: "review",
    statusLabel: "待审核",
    summary: "8 张候选场景图已生成，等待挑选后进入 shot delta 阶段。",
    owner: "Candidate Search",
    stage: "Master Scene Approval",
    assets: ["industrial_corridor_scene", "lighting_reference_board"],
    issues: ["候选 03 灯带过亮", "候选 07 景深过浅"],
    nextStep: "批准 1 张主场景图并冻结场景锚点。",
  },
];

const navLinks = [...document.querySelectorAll(".nav-link")];
const chips = [...document.querySelectorAll(".chip")];
const queueList = document.querySelector("#queue-list");
const detailPanel = document.querySelector("#detail-panel");
const sectionTitle = document.querySelector("#section-title");

let activeSection = "overview";
let activeFilter = "all";
let activeItemId = queueItems[0].id;

const sectionLabels = {
  overview: "总览中控",
  assets: "资产管理",
  generation: "生成编排",
  review: "审核修复",
};

function renderQueue() {
  const visibleItems = queueItems.filter((item) => {
    if (activeFilter === "all") {
      return true;
    }
    return item.status === activeFilter;
  });

  queueList.innerHTML = visibleItems
    .map(
      (item) => `
        <button class="queue-item ${item.id === activeItemId ? "is-active" : ""}" data-id="${item.id}">
          <header>
            <h4>${item.title}</h4>
            <span class="status ${item.status}">${item.statusLabel}</span>
          </header>
          <p>${item.summary}</p>
          <div class="detail-meta">阶段：${item.stage}</div>
        </button>
      `,
    )
    .join("");

  const activeVisible = visibleItems.some((item) => item.id === activeItemId);
  if (!activeVisible && visibleItems[0]) {
    activeItemId = visibleItems[0].id;
  }

  if (!visibleItems.length) {
    detailPanel.innerHTML = `
      <div class="detail-empty">
        <p class="eyebrow">当前筛选</p>
        <h4>这个分类下暂时没有任务</h4>
        <p>你可以切换筛选，或者创建一个新的生成批次。</p>
      </div>
    `;
    return;
  }

  renderDetail();

  queueList.querySelectorAll(".queue-item").forEach((button) => {
    button.addEventListener("click", () => {
      activeItemId = button.dataset.id;
      renderQueue();
    });
  });
}

function renderDetail() {
  const item = queueItems.find((entry) => entry.id === activeItemId);

  if (!item) {
    return;
  }

  detailPanel.innerHTML = `
    <article class="detail-card">
      <header>
        <div>
          <p class="eyebrow">任务详情</p>
          <h4>${item.title}</h4>
        </div>
        <span class="badge ${item.status}">${item.statusLabel}</span>
      </header>

      <div class="detail-stack">
        <div class="detail-copy">
          <strong>阶段</strong>
          <p>${item.stage}</p>
        </div>
        <div class="detail-copy">
          <strong>执行主体</strong>
          <p>${item.owner}</p>
        </div>
        <div class="detail-copy">
          <strong>上下文说明</strong>
          <p>${item.summary}</p>
        </div>
        <div class="detail-copy">
          <strong>输入资产</strong>
          <ul class="detail-list">
            ${item.assets.map((asset) => `<li>${asset}</li>`).join("")}
          </ul>
        </div>
        <div class="detail-copy">
          <strong>风险与限制</strong>
          <ul class="detail-list">
            ${item.issues.map((issue) => `<li>${issue}</li>`).join("")}
          </ul>
        </div>
        <div class="detail-copy">
          <strong>下一步</strong>
          <p>${item.nextStep}</p>
        </div>
      </div>

      <div class="detail-actions">
        <button class="primary-action">继续推进</button>
        <button class="ghost-action">查看 YAML 配置</button>
      </div>
    </article>
  `;
}

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    activeSection = link.dataset.section;
    sectionTitle.textContent = sectionLabels[activeSection];

    navLinks.forEach((entry) => entry.classList.remove("is-active"));
    link.classList.add("is-active");
  });
});

chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    activeFilter = chip.dataset.filter;
    chips.forEach((entry) => entry.classList.remove("is-selected"));
    chip.classList.add("is-selected");
    renderQueue();
  });
});

renderQueue();
