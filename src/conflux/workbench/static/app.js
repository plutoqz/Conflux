const $ = (id) => document.getElementById(id);

let statusCache = null;
let busyCount = 0;
let initialized = false;
let selectedReportPath = '';
let appStarted = false;
let activeQuery = null;
let profileOptimizationOriginal = null;
let profileOptimizationDraft = null;
let profileOptimizationState = 'idle';
let projectsCache = [];
let selectedProjectId = '';
let projectRegistryDir = 'projects';
// P3.3 snapshot-driven project page
let p3ProjectsCache = [];
let p3StateCache = {};
let p3Sse = null;
let p3SseProjectId = '';
let p3RefreshTimer = null;
let p3ConfirmTarget = null;
let activeP3Tab = 'overview';
let queryProjectContext = null;
let activeAssistantTab = 'chat';
let assistantNotes = [];
const MODEL_TIERS = ['quick', 'standard', 'deep'];
const FEATURE_MODELS = [
  { key: 'profile_optimization', prefix: 'profileOptimization' },
  { key: 'paper_review', prefix: 'paperReview' },
  { key: 'plan_analysis', prefix: 'planAnalysis' },
  { key: 'project_charter', prefix: 'projectCharter' },
  { key: 'research_radar', prefix: 'researchRadar' },
  { key: 'plan_translation', prefix: 'planTranslation' }
];

function normalizeTier(value) {
  return MODEL_TIERS.includes(value) ? value : 'standard';
}

function tierFieldId(tier, suffix) {
  return normalizeTier(tier) + suffix;
}

function tierModelPayload(tier) {
  const resolved = normalizeTier(tier);
  return {
    base_url: $(tierFieldId(resolved, 'BaseUrl')).value.trim(),
    model: $(tierFieldId(resolved, 'ModelName')).value.trim(),
    api_key: $(tierFieldId(resolved, 'ApiKey')).value,
    temperature: Number($(tierFieldId(resolved, 'Temperature')).value || 0.2),
    depth: resolved
  };
}

function allTierModelsPayload() {
  const payload = {};
  MODEL_TIERS.forEach((tier) => { payload[tier] = tierModelPayload(tier); });
  return payload;
}

function featureModelPayload(feature) {
  const item = FEATURE_MODELS.find((candidate) => candidate.key === feature);
  if (!item) return {};
  return {
    base_url: $(item.prefix + 'BaseUrl').value.trim(),
    model: $(item.prefix + 'ModelName').value.trim(),
    api_key: $(item.prefix + 'ApiKey').value,
    temperature: Number($(item.prefix + 'Temperature').value || 0)
  };
}

function allFeatureModelsPayload() {
  const payload = {};
  FEATURE_MODELS.forEach((item) => { payload[item.key] = featureModelPayload(item.key); });
  return payload;
}

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function fmtSize(bytes) {
  const value = Number(bytes || 0);
  if (!value) return '0 B';
  if (value < 1024) return value + ' B';
  if (value < 1048576) return (value / 1024).toFixed(1) + ' KB';
  return (value / 1048576).toFixed(1) + ' MB';
}

function fmtDate(timestamp) {
  if (!timestamp) return '-';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  }).format(new Date(Number(timestamp) * 1000));
}

function refreshIcons() {
  if (window.lucide) {
    window.lucide.createIcons({ attrs: { 'stroke-width': 1.9 } });
  }
}

function toast(message, kind = 'info') {
  const iconMap = { ok: 'circle-check', warn: 'triangle-alert', err: 'circle-x', info: 'info' };
  const item = document.createElement('div');
  item.className = 'toast ' + kind;
  item.setAttribute('role', kind === 'err' ? 'alert' : 'status');
  item.innerHTML = '<i data-lucide="' + iconMap[kind] + '" aria-hidden="true"></i>' +
    '<span>' + escapeHtml(message) + '</span>' +
    '<button type="button" aria-label="关闭通知"><i data-lucide="x" aria-hidden="true"></i></button>';
  item.querySelector('button').addEventListener('click', () => item.remove());
  $('toastBox').appendChild(item);
  refreshIcons();
  window.setTimeout(() => item.remove(), kind === 'err' ? 7000 : 4200);
}

function enterBusy(button, label = '处理中') {
  busyCount += 1;
  $('busyDot').className = 'busy-dot running';
  $('busyText').textContent = label;
  if (button) {
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
  }
}

function leaveBusy(button) {
  busyCount = Math.max(0, busyCount - 1);
  if (busyCount === 0) {
    $('busyDot').className = 'busy-dot';
    $('busyText').textContent = '系统就绪';
  }
  if (button) {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  }
  refreshIcons();
}

async function api(path, payload) {
  const response = await authFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {})
  });
  const data = await response.json();
  if (!response.ok && !data.error) data.error = '请求失败（HTTP ' + response.status + '）';
  return data;
}

function fmtIsoDate(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  }).format(parsed);
}

async function authFetch(path, options) {
  const response = await fetch(path, options);
  if (response.status === 401 && path !== '/api/login') {
    showAuthDialog('登录状态已失效，请重新输入访问令牌。');
  }
  return response;
}

function showAuthDialog(message = '') {
  const dialog = $('authDialog');
  if (!dialog) return;
  const error = $('authError');
  error.textContent = message;
  error.hidden = !message;
  if (!dialog.open) dialog.showModal();
  refreshIcons();
  window.setTimeout(() => $('accessToken').focus(), 0);
}

async function ensureAuthenticated() {
  try {
    const response = await fetch('/api/auth/status', { cache: 'no-store' });
    if (!response.ok) return true;
    const data = await response.json();
    if (data.required && !data.authenticated) {
      showAuthDialog();
      return false;
    }
  } catch (error) {
    return true;
  }
  return true;
}

async function login(event) {
  event.preventDefault();
  const button = $('loginButton');
  const token = $('accessToken').value;
  const previousHtml = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<span class="spin" aria-hidden="true"></span><span>验证中</span>';
  $('authError').hidden = true;
  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.authenticated) {
      throw new Error(data.error || '访问令牌验证失败');
    }
    $('accessToken').value = '';
    $('authDialog').close();
    if (appStarted) {
      await Promise.all([refreshStatus(), renderDashboard()]);
    } else {
      await startWorkbench();
    }
  } catch (error) {
    $('authError').textContent = error.message;
    $('authError').hidden = false;
    $('accessToken').focus();
  } finally {
    button.disabled = false;
    button.innerHTML = previousHtml;
    refreshIcons();
  }
}

function closeSidebar() {
  $('sidebar').classList.remove('open');
  $('sidebarBackdrop').classList.remove('open');
  $('menuButton').setAttribute('aria-expanded', 'false');
}

function nav(target, options = {}) {
  const nextNav = document.querySelector('.nav-item[data-target="' + target + '"]');
  const nextView = $(target);
  if (!nextNav || !nextView) return;

  document.querySelectorAll('.nav-item').forEach((button) => {
    const active = button === nextNav;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  document.querySelectorAll('.view').forEach((view) => view.classList.toggle('active', view === nextView));
  $('pageTitle').textContent = nextNav.dataset.title;
  $('pageSubtitle').textContent = nextNav.dataset.subtitle;
  if (window.location.hash !== '#' + target) history.replaceState(null, '', '#' + target);
  closeSidebar();
  if (target !== 'projects') closeP3Sse();
  if (target === 'assistant') loadAssistantData();
  if (options.focus) $('pageTitle').focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: 'instant' });
}

function toggleProfileMode() {
  const checked = document.querySelector('input[name="profileMode"]:checked');
  const inline = checked && checked.value === 'inline';
  $('profileFileFields').hidden = inline;
  $('profileInlineFields').hidden = !inline;
  $('profileInlineExtra').hidden = !inline;
}

function readInlineProfile() {
  return {
    profile_name: $('profileName').value.trim(),
    fields: $('profileFields').value.trim(),
    keywords: $('profileKeywords').value.trim(),
    description: $('profileDescription').value.trim(),
    negative_keywords: $('profileNegativeKeywords').value.trim()
  };
}

function writeInlineProfile(profile) {
  $('profileFields').value = Array.isArray(profile.fields) ? profile.fields.join(', ') : (profile.fields || '');
  $('profileKeywords').value = Array.isArray(profile.keywords) ? profile.keywords.join('\n') : (profile.keywords || '');
  $('profileDescription').value = profile.description || '';
  $('profileNegativeKeywords').value = Array.isArray(profile.negative_keywords)
    ? profile.negative_keywords.join('\n')
    : (profile.negative_keywords || '');
}

function resetProfileOptimization() {
  profileOptimizationOriginal = null;
  profileOptimizationDraft = null;
  profileOptimizationState = 'idle';
  $('profileOptimization').hidden = true;
  $('optimizeProfile').disabled = false;
}

function renderProfileOptimization(profile, notes, model) {
  profileOptimizationDraft = profile;
  profileOptimizationState = 'preview';
  $('optimizedProfileFields').textContent = (profile.fields || []).join(' · ') || '未调整';
  $('optimizedProfileKeywords').textContent = (profile.keywords || []).join(' · ');
  $('optimizedProfileDescription').textContent = profile.description || '';
  $('optimizedProfileNegativeKeywords').textContent = (profile.negative_keywords || []).join(' · ') || '无';
  $('optimizedProfileNotes').innerHTML = '';
  (notes || []).forEach((note) => {
    const item = document.createElement('li');
    item.textContent = note;
    $('optimizedProfileNotes').appendChild(item);
  });
  $('optimizedProfileNotesRow').hidden = !(notes || []).length;
  $('profileOptimizationTitle').textContent = 'AI 优化建议';
  $('profileOptimizationMeta').textContent = (model ? '由 ' + model + ' 生成。' : '') + '建议稿不会自动保存，请审查后再采用。';
  $('profileOptimizationStatus').textContent = '待审查';
  $('profileOptimizationStatus').className = 'status-pill info';
  $('applyProfileOptimization').hidden = false;
  $('dismissProfileOptimization').hidden = false;
  $('undoProfileOptimization').hidden = true;
  $('profileOptimization').classList.remove('applied');
  $('profileOptimization').hidden = false;
  refreshIcons();
}

async function optimizeProfile() {
  const source = readInlineProfile();
  if (!source.keywords && !source.description) {
    $('profileKeywords').focus();
    toast('请先填写关键词或研究问题，再让 AI 优化', 'warn');
    return;
  }

  const button = $('optimizeProfile');
  enterBusy(button, '优化画像');
  try {
    const data = await api('/api/profile/optimize', source);
    if (!data.ok) {
      toast(data.error || '画像优化失败', 'err');
      return;
    }
    profileOptimizationOriginal = source;
    renderProfileOptimization(data.profile || {}, data.notes || [], data.model || '');
    $('profileOptimization').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (error) {
    toast('画像优化失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

function applyProfileOptimization() {
  if (!profileOptimizationDraft || !profileOptimizationOriginal) return;
  writeInlineProfile(profileOptimizationDraft);
  profileOptimizationState = 'applied';
  $('profileOptimizationTitle').textContent = '已采用 AI 优化稿';
  $('profileOptimizationMeta').textContent = '优化内容已填入表单，保存前可撤销回你的原始画像。';
  $('profileOptimizationStatus').textContent = '已采用';
  $('profileOptimizationStatus').className = 'status-pill ok';
  $('applyProfileOptimization').hidden = true;
  $('dismissProfileOptimization').hidden = true;
  $('undoProfileOptimization').hidden = false;
  $('profileOptimization').classList.add('applied');
  $('optimizeProfile').disabled = true;
  refreshIcons();
  toast('已采用优化稿，请审查表单后保存', 'ok');
}

function undoProfileOptimization() {
  if (!profileOptimizationOriginal) return;
  writeInlineProfile(profileOptimizationOriginal);
  resetProfileOptimization();
  $('profileKeywords').focus();
  toast('已恢复你优化前的原始画像', 'info');
}

function updatePaperSourceFields() {
  $('fixtureField').hidden = $('paperSource').value !== 'fixture';
}

function hasReasoningCredential(tier) {
  const resolved = normalizeTier(tier || ($('queryDepth').value || $('depthSelect').value));
  const credentials = (statusCache && statusCache.credentials) || {};
  return Boolean(
    $(tierFieldId(resolved, 'ApiKey')).value.trim() ||
    credentials[resolved + '_api_key'] ||
    credentials.openai_api_key
  );
}

function hasEmbeddingCredential() {
  const credentials = (statusCache && statusCache.credentials) || {};
  const tier = normalizeTier($('queryDepth').value || $('depthSelect').value);
  return Boolean(
    $('embeddingApiKey').value.trim() ||
    $(tierFieldId(tier, 'ApiKey')).value.trim() ||
    credentials.embedding_api_key ||
    credentials.openai_api_key ||
    credentials[tier + '_api_key']
  );
}

function webSearchState() {
  const configured = (statusCache && statusCache.defaults && statusCache.defaults.web_search) || {};
  const provider = ($('webSearchProvider') && $('webSearchProvider').value) || configured.provider || 'duckduckgo';
  const credentials = (statusCache && statusCache.credentials) || {};
  const ready = provider === 'duckduckgo' ||
    (provider === 'serpapi' && Boolean(($('serpapiApiKey') && $('serpapiApiKey').value.trim()) || credentials.serpapi_api_key)) ||
    (provider === 'bing' && Boolean(($('bingApiKey') && $('bingApiKey').value.trim()) || credentials.bing_api_key)) ||
    (provider === 'google' && Boolean(($('googleApiKey') && $('googleApiKey').value.trim()) || credentials.google_api_key) &&
      Boolean(($('googleCseId') && $('googleCseId').value.trim()) || credentials.google_cse_id));
  return { provider, ready };
}

function updateWebSearchFields() {
  const state = webSearchState();
  const serpapi = state.provider === 'serpapi';
  const bing = state.provider === 'bing';
  const google = state.provider === 'google';
  $('serpapiKeyField').hidden = !serpapi;
  $('bingKeyField').hidden = !bing;
  $('googleKeyField').hidden = !google;
  $('googleCseField').hidden = !google;
  $('webSearchConfigHint').textContent = serpapi
    ? 'SerpAPI 需要 API Key；保存后仅写入本地工作台环境文件。'
    : bing
      ? 'Bing Web Search API 需要订阅密钥；主 provider 失败时仍可作为降级来源。'
      : google
        ? 'Google Programmable Search 需要 API Key 和 CSE ID。'
        : 'DuckDuckGo 无需 API Key；若不可用，系统会尝试已配置的备用 provider。';
  updateQueryReadiness();
  if (statusCache) renderCapabilities(statusCache.credentials || {});
}

function updateQueryReadiness() {
  const state = $('queryReadiness');
  if (!statusCache) return;
  const reasoning = hasReasoningCredential();
  const embedding = hasEmbeddingCredential();
  const search = webSearchState().ready;
  const button = $('runQuery');

  state.className = 'query-readiness';
  if (!reasoning) {
    state.classList.add('error');
    state.innerHTML = '<i data-lucide="circle-x" aria-hidden="true"></i><span>缺少推理模型凭证。请先在“模型与环境”中配置，研究任务暂不可执行。</span>';
    button.disabled = true;
  } else if (!embedding || !search) {
    const missing = [!embedding && '向量检索', !search && '网络搜索'].filter(Boolean).join('、');
    state.classList.add('warn');
    state.innerHTML = '<i data-lucide="triangle-alert" aria-hidden="true"></i><span>' + missing + '未配置，任务仍可运行，但会明确标记降级来源。</span>';
    button.disabled = false;
  } else {
    state.innerHTML = '<i data-lucide="circle-check" aria-hidden="true"></i><span>推理、向量检索和网络搜索均已就绪。</span>';
    button.disabled = false;
  }
  refreshIcons();
}

function capabilityRows(credentials) {
  const profilesReady = Boolean(statusCache && (statusCache.profiles || []).length);
  const search = webSearchState();
  return [
    { name: '分档推理模型', detail: '当前默认档位的规划、分析与核验', ready: hasReasoningCredential($('depthSelect').value), icon: 'brain-circuit', required: true },
    { name: '向量检索', detail: '检索本地论文和文档', ready: Boolean(credentials.embedding_api_key || credentials.openai_api_key), icon: 'database', required: false },
    { name: '网络搜索', detail: search.provider === 'serpapi' ? 'SerpAPI 外部证据' : search.provider === 'bing' ? 'Bing 外部证据' : search.provider === 'google' ? 'Google 外部证据' : 'DuckDuckGo + 可用备用来源', ready: search.ready, icon: 'globe-2', required: false },
    { name: '研究画像', detail: '指导论文搜索和评分', ready: profilesReady, icon: 'user-round-search', required: true }
  ];
}

function renderCapabilities(credentials) {
  const rows = capabilityRows(credentials || {});
  const html = rows.map((row) => {
    const className = row.ready ? 'ok' : 'warn';
    const state = row.ready ? '已就绪' : (row.required ? '需配置' : '可选');
    const stateIcon = row.ready ? 'check' : 'minus';
    return '<div class="capability-item ' + className + '">' +
      '<span class="capability-icon"><i data-lucide="' + row.icon + '" aria-hidden="true"></i></span>' +
      '<span><strong>' + escapeHtml(row.name) + '</strong><small>' + escapeHtml(row.detail) + '</small></span>' +
      '<span class="capability-state"><i data-lucide="' + stateIcon + '" aria-hidden="true"></i><span class="sr-only">' + state + '</span></span>' +
      '</div>';
  }).join('');
  $('keyStatus').innerHTML = html;
  $('settingsCapabilities').innerHTML = html;

  const requiredMissing = rows.filter((row) => row.required && !row.ready).length;
  const optionalMissing = rows.filter((row) => !row.required && !row.ready).length;
  $('sideHealthDot').className = 'health-indicator ' + (requiredMissing ? 'warn' : 'ok');
  $('sideHealthTitle').textContent = requiredMissing ? '环境需要配置' : '核心能力已就绪';
  $('sideHealthText').textContent = requiredMissing ? requiredMissing + ' 项核心能力缺失' : (optionalMissing ? optionalMissing + ' 项能力可选配置' : '全部研究能力可用');
  $('readinessSummary').textContent = requiredMissing ? '请先补齐核心能力，再执行完整研究。' : (optionalMissing ? '核心能力可用，部分来源将按需降级。' : '全部研究能力运行正常。');
  $('workflowStatus').textContent = requiredMissing ? '需要配置' : '准备就绪';
  $('workflowStatus').className = 'status-pill ' + (requiredMissing ? 'warn' : 'ok');
  updateQueryReadiness();
  refreshIcons();
}

function renderPaperIngestionAudit(audit) {
  const state = audit || {};
  $('fullTextIndexedCount').textContent = Number(state.full_text_indexed || 0);
  $('summaryIndexedCount').textContent = Number(state.summary_only || 0);
  const repairs = state.repairable || [];
  $('fullTextRepairCount').textContent = repairs.length;
  if (!state.available) {
    $('paperIngestionAuditDetail').textContent = '向量库状态不可用：' + (state.error || '未找到本地索引');
    return;
  }
  $('paperIngestionAuditDetail').textContent = repairs.length
    ? '待修复：' + repairs.map((item) => (item.paper_id || '') + (item.title ? ' · ' + item.title : '')).join('；')
    : '全文策略与本地向量索引已核对，没有发现假全文状态。';
}

function renderVectorCollections(vectorStore) {
  const state = vectorStore || {};
  const collections = state.collections || [];
  $('vectorIndexSummary').textContent = collections.length
    ? '当前索引：' + (state.active || '未设置') + '；共保留 ' + collections.length + ' 个 collection。'
    : '尚未发现本地向量 collection。';
  $('vectorCollections').innerHTML = collections.map((item) => {
    const meta = Number(item.count || 0) + ' 条' + (item.dimension ? ' · ' + item.dimension + ' 维' : '') + (item.model ? ' · ' + item.model : '');
    const action = item.active
      ? '<span class="status-pill ok">当前</span>'
      : '<button class="icon-button subtle delete-vector-collection" type="button" data-collection="' + escapeHtml(item.name) + '" aria-label="删除旧索引" title="删除旧索引"><i data-lucide="trash-2" aria-hidden="true"></i></button>';
    return '<div class="vector-collection-row"><span><strong>' + escapeHtml(item.name) + '</strong><small>' + escapeHtml(meta) + '</small></span>' + action + '</div>';
  }).join('') || '<div class="inline-empty">没有可管理的 collection</div>';
  document.querySelectorAll('.delete-vector-collection').forEach((button) => {
    button.addEventListener('click', () => deleteVectorCollection(button.dataset.collection || ''));
  });
  refreshIcons();
}

async function refreshStatus(options = {}) {
  try {
    const response = await authFetch('/api/status');
    if (!response.ok) throw new Error('状态接口返回 ' + response.status);
    const nextStatus = await response.json();
    statusCache = nextStatus;
    $('rootPath').textContent = nextStatus.project_root || '';

    const currentProfile = $('profilePath').value;
    $('profilePath').innerHTML = '';
    const profiles = nextStatus.profiles || [];
    profiles.forEach((profile) => {
      const option = document.createElement('option');
      option.value = profile.path;
      option.textContent = profile.display || profile.name || profile.path;
      option.selected = profile.path === (currentProfile || nextStatus.defaults.profile);
      $('profilePath').appendChild(option);
    });
    if (!profiles.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '没有可用画像，请临时创建';
      $('profilePath').appendChild(option);
    }

    if (!initialized || options.resetDefaults) {
      $('fixturePath').value = nextStatus.defaults.fixture || '';
      $('inboxOut').value = nextStatus.defaults.inbox_dir || '';
      $('promoteInbox').value = (nextStatus.defaults.inbox_dir || '') + '/paper_inbox.json';
      $('promoteOut').value = nextStatus.defaults.promote_dir || '';
      const tierModels = nextStatus.defaults.tier_models || {};
      MODEL_TIERS.forEach((tier) => {
        const model = tierModels[tier] || {};
        $(tierFieldId(tier, 'BaseUrl')).value = model.base_url || '';
        $(tierFieldId(tier, 'ModelName')).value = model.model || '';
        $(tierFieldId(tier, 'Temperature')).value = Number(model.temperature == null ? 0.2 : model.temperature);
        $(tierFieldId(tier, 'ApiKey')).value = '';
      });
      const featureModels = nextStatus.defaults.feature_models || {};
      FEATURE_MODELS.forEach((item) => {
        const model = featureModels[item.key] || {};
        $(item.prefix + 'BaseUrl').value = model.base_url || '';
        $(item.prefix + 'ModelName').value = model.model || '';
        $(item.prefix + 'Temperature').value = Number(model.temperature == null ? 0.2 : model.temperature);
        $(item.prefix + 'ApiKey').value = '';
      });
      $('embeddingBaseUrl').value = (nextStatus.defaults.embedding || {}).base_url || '';
      $('embeddingModel').value = (nextStatus.defaults.embedding || {}).model || '';
      $('webSearchProvider').value = (nextStatus.defaults.web_search || {}).provider || 'duckduckgo';
      $('serpapiApiKey').value = '';
      $('bingApiKey').value = '';
      $('googleApiKey').value = '';
      $('googleCseId').value = '';
      if (nextStatus.saved_depth) $('depthSelect').value = nextStatus.saved_depth;
    }

    updateWebSearchFields();
    renderPaperIngestionAudit(nextStatus.paper_ingestion_audit || {});
    renderVectorCollections((nextStatus.defaults || {}).vector_store || {});
    renderCapabilities(nextStatus.credentials || {});
    renderReports();
    initialized = true;
  } catch (error) {
    $('busyDot').className = 'busy-dot error';
    $('busyText').textContent = '状态不可用';
    toast('无法读取工作台状态：' + error.message, 'err');
  }
}

function projectHealthLabel(health) {
  return ({ ok: '状态正常', info: '需要关注', warning: '存在提醒', error: '需要处理' })[health] || '未知';
}

function projectHealthClass(health) {
  return ({ ok: 'ok', info: 'info', warning: 'warn', error: 'error' })[health] || 'neutral';
}

async function loadProjects(options = {}) {
  const refresh = Boolean(options.refresh);
  const button = refresh ? $('refreshProjects') : null;
  if (button) enterBusy(button, options.projectId ? '检查项目' : '检查全部');
  $('projectsError').hidden = true;
  try {
    if (refresh) {
      const ids = options.projectId
        ? [options.projectId]
        : (p3ProjectsCache || []).map((item) => item.id);
      for (const projectId of ids) {
        const result = await api('/api/v1/projects/' + encodeURIComponent(projectId) + '/refresh', {});
        if (!result.ok) throw new Error(result.error || '项目检查失败');
      }
    }
    const response = await authFetch('/api/v1/projects', { cache: 'no-store' });
    const data = await response.json().catch(() => ({}));
    if (!data.ok) throw new Error(data.error || '项目状态加载失败');
    p3ProjectsCache = data.projects || [];
    populateAssistantProjects();
    if (!p3ProjectsCache.some((item) => item.id === selectedProjectId)) {
      selectedProjectId = p3ProjectsCache[0] ? p3ProjectsCache[0].id : '';
    }
    projectRegistryDir = data.registry_dir || projectRegistryDir;
    renderP3ProjectList(data);
    if (refresh) toast(options.projectId ? '项目状态已检查' : '全部项目状态已检查', 'ok');
  } catch (error) {
    $('projectsErrorMessage').textContent = error.message;
    $('projectsError').hidden = false;
    $('projectSummaryState').textContent = '加载失败';
    $('projectSummaryState').className = 'status-pill error';
    $('projectSummaryText').textContent = '无法读取项目注册表';
    if (refresh) toast('项目检查失败：' + error.message, 'err');
  } finally {
    if (button) leaveBusy(button);
  }
}

function closeP3Sse() {
  if (p3Sse) {
    p3Sse.close();
    p3Sse = null;
  }
  p3SseProjectId = '';
  if (p3RefreshTimer) {
    window.clearTimeout(p3RefreshTimer);
    p3RefreshTimer = null;
  }
}

function openP3Sse(projectId) {
  if (p3Sse && p3SseProjectId === projectId) return;
  closeP3Sse();
  if (typeof EventSource === 'undefined') return;
  p3SseProjectId = projectId;
  p3Sse = new EventSource('/api/v1/projects/' + encodeURIComponent(projectId) + '/events');
  p3Sse.onmessage = () => {
    if (!p3RefreshTimer) {
      p3RefreshTimer = window.setTimeout(() => {
        p3RefreshTimer = null;
        if (selectedProjectId === p3SseProjectId) loadP3State();
      }, 400);
    }
  };
  // EventSource reconnects automatically with Last-Event-ID; no handler needed.
}

function renderP3ProjectList(data) {
  const projects = data.projects || [];
  const pendingTotal = projects.reduce((sum, item) => sum + (item.pending_reviews || 0), 0);
  $('projectNavCount').textContent = String(projects.length);
  $('projectCount').textContent = String(projects.length);
  $('projectRegistryPath').textContent = data.registry_dir || 'projects/';
  if (pendingTotal) {
    $('projectSummaryState').textContent = pendingTotal + ' 项待处理';
    $('projectSummaryState').className = 'status-pill warn';
  } else {
    $('projectSummaryState').textContent = projects.length ? '状态正常' : '等待登记';
    $('projectSummaryState').className = 'status-pill ' + (projects.length ? 'ok' : 'neutral');
  }
  $('projectSummaryText').textContent = projects.length
    ? '共 ' + projects.length + ' 个项目，状态来自本地物化快照'
    : '项目注册表为空';

  $('projectRegistryErrors').hidden = !(data.registry_errors || []).length;
  $('projectRegistryErrorList').innerHTML = (data.registry_errors || []).map((error) => '<p>' + escapeHtml(error) + '</p>').join('');
  $('projectsEmpty').hidden = projects.length > 0;
  $('projectList').innerHTML = projects.map((item) => {
    const revision = item.revision || 0;
    const branch = '';
    return '<button class="project-row" type="button" role="option" data-project-id="' + escapeHtml(item.id) + '" aria-selected="' + String(item.id === selectedProjectId) + '">' +
      '<span class="project-row-state ' + escapeHtml(item.health || '') + '" aria-hidden="true"></span>' +
      '<span class="project-row-copy"><strong>' + escapeHtml(item.name || item.id) + '</strong><small title="' + escapeHtml(item.path || '') + '">' + escapeHtml(item.path || '') + '</small></span>' +
      '<span class="project-row-meta"><span>' + (revision ? '快照 v' + revision : '尚未建立快照') + '</span><code>' + (item.documents_total || 0) + ' 份文档</code>' +
      (item.pending_reviews ? '<span class="project-row-alerts"><i data-lucide="inbox" aria-hidden="true"></i>' + item.pending_reviews + '</span>' : '') + '</span></button>';
  }).join('');
  document.querySelectorAll('.project-row').forEach((button) => button.addEventListener('click', () => {
    if (selectedProjectId !== button.dataset.projectId) {
      activeP3Tab = 'overview';
      closeP3Sse();
    }
    selectedProjectId = button.dataset.projectId;
    renderP3ProjectList(data);
  }));
  renderP3SelectedProject();
  refreshIcons();
}

function renderP3SelectedProject() {
  const pane = $('projectDetailP3');
  const has = Boolean(selectedProjectId);
  pane.hidden = !has;
  if (!has) return;
  loadP3State();
}

async function loadP3State() {
  const projectId = selectedProjectId;
  if (!projectId) return;
  try {
    const response = await authFetch('/api/v1/projects/' + encodeURIComponent(projectId) + '/state', { cache: 'no-store' });
    const data = await response.json().catch(() => ({}));
    if (!data.ok) throw new Error(data.error || '项目状态加载失败');
    if (selectedProjectId !== projectId) return;
    p3StateCache[projectId] = data;
    renderP3Header(data);
    renderP3Overview(data);
    renderP3WorkItems(data);
    renderP3Evidence(data);
    renderP3Activity(data);
    renderP3Inbox(data);
    renderP3Audit(data);
    refreshIcons();
    openP3Sse(projectId);
  } catch (error) {
    if (selectedProjectId === projectId) {
      $('p3ProjectName').textContent = '状态加载失败';
      $('p3ProjectHealth').textContent = error.message;
      $('p3ProjectHealth').className = 'status-pill error';
    }
  }
}

function selectP3Tab(tabName) {
  const tabs = Array.from(document.querySelectorAll('[data-p3-tab]'));
  if (!tabs.some((tab) => tab.dataset.p3Tab === tabName)) tabName = 'overview';
  activeP3Tab = tabName;
  tabs.forEach((tab) => {
    const active = tab.dataset.p3Tab === tabName;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-p3-panel]').forEach((panel) => {
    const active = panel.dataset.p3Panel === tabName;
    panel.classList.toggle('active', active);
    panel.hidden = !active;
  });
  if (tabName === 'tools') loadP3Tools();
}

function renderP3Header(data) {
  const project = data.project || {};
  const snapshot = data.snapshot || null;
  const pending = (data.reviews || []).filter((item) => item.status === 'pending');
  $('p3ProjectName').textContent = project.name || project.id || '-';
  $('p3ProjectHealth').textContent = snapshot ? (snapshot.health === 'ok' ? '正常' : snapshot.health === 'warning' ? '需关注' : snapshot.health) : '未知';
  $('p3ProjectHealth').className = 'status-pill ' + (snapshot ? projectHealthClass(snapshot.health) : 'neutral');
  $('p3SnapshotAge').textContent = snapshot ? ('数据更新 ' + fmtDate(snapshot.updated_at || snapshot.created_at)) : '尚未建立快照';
  $('p3SnapshotAge').className = 'status-pill ' + (snapshot ? 'neutral' : 'warn');
  $('p3ProjectDescription').textContent = project.description || '暂无项目说明';
  $('p3ProjectPath').textContent = project.path || '-';
  $('p3ReviewCount').textContent = String(pending.length);
  $('p3InboxTabCount').textContent = String(pending.length);
}

function p3DeclaredPill(status) {
  return '<span class="p3-status-pill declared">' + escapeHtml(P3_DECLARED_LABELS[status] || status) + '</span>';
}

function p3ObservedPill(status) {
  const cls = status === 'verified' ? 'verified' : status === 'failed' ? 'failed' : '';
  return '<span class="p3-status-pill observed ' + cls + '">' + escapeHtml(P3_OBSERVED_LABELS[status] || status) + '</span>';
}

function p3InferredPill(status) {
  return '<span class="p3-status-pill inferred ' + escapeHtml(status || '') + '">' + escapeHtml(P3_INFERRED_LABELS[status] || status) + '</span>';
}

function renderP3Overview(data) {
  const snapshot = data.snapshot || null;
  const summary = (snapshot && snapshot.summary) || {};
  const focus = $('p3Focus');
  if (summary.focus) {
    const kindLabel = P3_KIND_LABELS[summary.focus_kind] || '工作项';
    focus.innerHTML =
      '<div class="focus-icon" aria-hidden="true"><i data-lucide="target"></i></div>' +
      '<div><strong>' + escapeHtml(summary.focus) + '</strong>' +
      '<small>' + escapeHtml(kindLabel) + ' · 快照 v' + (snapshot.revision || 0) + ' · ' + (summary.pending_review_count ? summary.pending_review_count + ' 项待处理' : '无待处理项') + '</small></div>';
  } else {
    focus.innerHTML =
      '<div class="focus-icon" aria-hidden="true"><i data-lucide="target"></i></div>' +
      '<div><strong>尚未定义研究计划</strong><small>在设置中登记总体目标、里程碑或后续行动，或运行一次“检查状态”。</small></div>';
  }

  const needs = [];
  (summary.blocked || []).forEach((title) => {
    needs.push('<div class="audit-item risk"><span class="audit-item-icon"><i data-lucide="triangle-alert" aria-hidden="true"></i></span><div><p>受阻：' + escapeHtml(title) + '</p></div></div>');
  });
  const pending = (data.reviews || []).filter((item) => item.status === 'pending').slice(0, 3);
  pending.forEach((review) => {
    needs.push(
      '<div class="audit-item action"><span class="audit-item-icon"><i data-lucide="inbox" aria-hidden="true"></i></span>' +
      '<div><p>' + escapeHtml(review.summary) + '</p><button class="p3-btn-goto" type="button" data-p3-goto="inbox">前往待处理</button></div></div>'
    );
  });
  $('p3NeedsCount').textContent = String(needs.length ? (summary.blocked || []).length + pending.length : 0);
  $('p3NeedsAction').innerHTML = needs.join('') || '<div class="p3-inbox-empty-row">当前没有阻塞或待处理项。</div>';

  const activity = data.activity || {};
  const progressEvents = [];
  (activity.events || []).forEach((event) => {
    const kind = String(event.kind || '');
    if (!['research_query.completed', 'evidence.source_changed', 'work_item.confirmed', 'review.resolved'].includes(kind)) return;
    progressEvents.push(event);
  });
  $('p3RecentProgress').innerHTML = progressEvents.slice(0, 5).map((event) => {
    const kind = String(event.kind || '');
    const icon = kind === 'research_query.completed' ? 'flask-conical' : kind === 'evidence.source_changed' ? 'file-warning' : 'check';
    return '<div class="audit-item progress"><span class="audit-item-icon"><i data-lucide="' + icon + '" aria-hidden="true"></i></span>' +
      '<div><p>' + escapeHtml(kind) + '</p><div class="audit-evidence"><code>' + escapeHtml(fmtDate(event.created_at)) + '</code></div></div></div>';
  }).join('') || '<div class="p3-inbox-empty-row">暂无验证进展。测试、运行与证据变化会以事件形式记录在这里。</div>';

  const running = (activity.jobs || []).filter((job) => ['pending', 'running'].includes(job.status));
  $('p3Running').innerHTML = running.map((job) =>
    '<div class="audit-item action"><span class="audit-item-icon"><i data-lucide="loader" aria-hidden="true"></i></span>' +
    '<div><p>' + escapeHtml(job.query || job.run_id) + '</p><div class="audit-evidence"><code>' + escapeHtml(job.status) + '</code></div></div></div>'
  ).join('') || '<div class="p3-inbox-empty-row">当前没有运行中的任务。</div>';

  const git = (snapshot && snapshot.git_state) || {};
  $('p3RepoBranch').textContent = git.is_repository ? (git.branch || 'detached') : '非 Git 目录';
  $('p3RepoHead').textContent = git.head ? git.head.slice(0, 8) : '-';
  $('p3DirtyFiles').textContent = git.dirty_files ? String(git.dirty_files) : '0';

  $('p3FocusMeta').textContent = snapshot ? ('快照 v' + snapshot.revision) : '-';
  document.querySelectorAll('[data-p3-goto="inbox"]').forEach((button) => button.addEventListener('click', () => selectP3Tab('inbox')));
}

// ── P3.5 周期审计与摘要 ──────────────────────────────────────────────

const P3_AUDIT_STATUS_LABELS = {
  created: '首次基线',
  compared: '对比基线',
  unchanged: '与基线相同',
  legacy: '旧基线（仅 Git 头）',
  incomparable: '旧基线不可比较'
};

const P3_AUDIT_STATUS_CLASS = {
  created: 'neutral',
  compared: 'progress',
  unchanged: 'neutral',
  legacy: 'warn',
  incomparable: 'risk'
};

let p3AuditDraft = null;

function renderP3Audit(data) {
  const body = $('p3AuditBody');
  if (!body) return;
  const audit = data.audit || null;
  if (p3AuditDraft && p3AuditDraft.project_id === selectedProjectId) {
    renderP3AuditDraft(p3AuditDraft);
    return;
  }
  if (!audit) {
    body.innerHTML = '<div class="p3-inbox-empty-row">尚无已确认的周期摘要。运行一次检查状态后点击“生成周期摘要”建立首个基线。</div>';
    return;
  }
  const period = audit.period || ('v' + audit.baseline_revision + ' → v' + audit.current_revision);
  body.innerHTML =
    '<div class="audit-item progress"><span class="audit-item-icon"><i data-lucide="history" aria-hidden="true"></i></span>' +
    '<div><p>上一已确认周期：' + escapeHtml(period) + '</p>' +
    '<div class="audit-evidence"><code>进展 ' + audit.real_progress + ' · 失败 ' + audit.failed_experiments +
    ' · 风险 ' + audit.risks + ' · 下一周期候选 ' + audit.next_cycle_candidates + '</code></div></div></div>';
  refreshIcons();
}

function renderP3AuditDraft(draft) {
  const body = $('p3AuditBody');
  if (!body) return;
  if (!draft.ok) {
    body.innerHTML = '<div class="audit-item risk"><span class="audit-item-icon"><i data-lucide="triangle-alert" aria-hidden="true"></i></span>' +
      '<div><p>' + escapeHtml(draft.error || '周期摘要生成失败') + '</p></div></div>';
    refreshIcons();
    return;
  }
  const statusLabel = P3_AUDIT_STATUS_LABELS[draft.baseline_status] || draft.baseline_status;
  const statusClass = P3_AUDIT_STATUS_CLASS[draft.baseline_status] || 'neutral';
  const rows = [];
  rows.push('<div class="audit-item progress"><span class="audit-item-icon"><i data-lucide="scale" aria-hidden="true"></i></span>' +
    '<div><p>基线 <code>v' + (draft.baseline.revision || 0) + '</code> → 当前 <code>v' + (draft.current.revision || 0) + '</code> · ' + escapeHtml(draft.period) + '</p>' +
    '<div class="audit-evidence"><code>' + escapeHtml(statusLabel) + '</code><span class="status-pill ' + statusClass + '" style="margin-left:6px">' + escapeHtml(statusLabel) + '</span></div></div></div>');
  (draft.real_progress || []).forEach((claim) => {
    const icons = { work_item: 'check', commit: 'git-commit', test: 'flask-conical', experiment: 'beaker', paper: 'book-open', evidence: 'file-warning' };
    rows.push('<div class="audit-item progress"><span class="audit-item-icon"><i data-lucide="' + (icons[claim.category] || 'check') + '" aria-hidden="true"></i></span>' +
      '<div><p>' + escapeHtml(claim.summary) + '</p>' +
      '<div class="audit-evidence">' + (claim.evidence_refs || []).map((ref) => '<code>' + escapeHtml(ref) + '</code>').join(' ') + '</div>' +
      ((claim.acceptance_criteria && claim.acceptance_criteria.length) ? '<div class="audit-evidence"><small>验收标准：' + escapeHtml(claim.acceptance_criteria.join('；')) + '</small></div>' : '') +
      '</div></div>');
  });
  if (!(draft.real_progress || []).length) {
    rows.push('<div class="p3-inbox-empty-row">本周期尚无可验证的真实进展。</div>');
  }
  (draft.failed_experiments || []).forEach((entry) => {
    rows.push('<div class="audit-item risk"><span class="audit-item-icon"><i data-lucide="circle-x" aria-hidden="true"></i></span>' +
      '<div><p>失败实验：' + escapeHtml(entry.summary) + '</p></div></div>');
  });
  (draft.risks || []).slice(0, 3).forEach((risk) => {
    rows.push('<div class="audit-item risk"><span class="audit-item-icon"><i data-lucide="triangle-alert" aria-hidden="true"></i></span>' +
      '<div><p>' + escapeHtml(risk) + '</p></div></div>');
  });
  (draft.next_cycle_candidates || []).slice(0, 3).forEach((candidate) => {
    rows.push('<div class="audit-item action"><span class="audit-item-icon"><i data-lucide="arrow-right" aria-hidden="true"></i></span>' +
      '<div><p>下一周期：' + escapeHtml(candidate.summary) + '</p></div></div>');
  });
  if (!draft.confirmed && draft.baseline_status !== 'unchanged') {
    rows.push('<div class="project-section-actions" style="margin-top:8px">' +
      '<button id="p3ConfirmAudit" class="button primary compact" type="button"><i data-lucide="stamp" aria-hidden="true"></i><span>确认本期摘要为新基线</span></button>' +
      '</div>');
  }
  body.innerHTML = rows.join('');
  const confirmButton = $('p3ConfirmAudit');
  if (confirmButton) confirmButton.addEventListener('click', () => confirmP3Audit());
  refreshIcons();
}

async function runP3Audit() {
  const projectId = selectedProjectId;
  const button = $('p3RunAudit');
  if (!projectId || !button) return;
  enterBusy(button, '生成中');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(projectId) + '/audit', {});
    if (!data.ok) throw new Error(data.error || '生成失败');
    p3AuditDraft = data.draft;
    renderP3AuditDraft(p3AuditDraft);
    loadP3State();
  } catch (error) {
    toast('周期摘要生成失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function confirmP3Audit() {
  const projectId = selectedProjectId;
  if (!projectId || !p3AuditDraft) return;
  const button = $('p3ConfirmAudit');
  if (button) enterBusy(button, '确认中');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(projectId) + '/audit/confirm', {
      baseline_revision: p3AuditDraft.baseline ? p3AuditDraft.baseline.revision : null,
      current_revision: p3AuditDraft.current ? p3AuditDraft.current.revision : null
    });
    if (!data.ok) throw new Error(data.error || '确认失败');
    p3AuditDraft = null;
    toast('周期摘要已确认，新基线为 v' + (data.current ? data.current.revision : '?'));
    loadP3State();
  } catch (error) {
    toast('确认失败：' + error.message, 'err');
  } finally {
    if (button) leaveBusy(button);
  }
}

function renderP3WorkItems(data) {
  const snapshot = data.snapshot || null;
  const items = (snapshot && snapshot.work_items) || [];
  const body = $('p3WorkItemsBody');
  $('p3WorkItemsEmpty').hidden = items.length > 0;
  $('p3WorkItemsTable').style.display = items.length ? '' : 'none';
  body.innerHTML = items.map((item) => {
    const kind = item.kind || 'action';
    const editable = kind === 'milestone' || kind === 'action';
    const evidence = item.evidence_refs || [];
    const negative = evidence.filter((ref) => ref.includes(':contradicts:') || ref.includes(':insufficient:')).length;
    const runs = item.linked_run_ids || [];
    const papers = item.linked_paper_keys || [];
    const links = [];
    if (evidence.length) {
      links.push('<span class="p3-kind-tag ' + (negative ? 'risk' : '') + '">证据 ' + evidence.length + (negative ? '（' + negative + ' 不支持）' : '') + '</span>');
    }
    if (runs.length) links.push('<span class="p3-kind-tag">运行 ' + runs.length + '</span>');
    if (papers.length) links.push('<span class="p3-kind-tag plan">论文 ' + papers.length + '</span>');
    if (item.linked_branch) links.push('<span class="p3-kind-tag plan">分支 ' + escapeHtml(item.linked_branch) + '</span>');
    const actions = [];
    actions.push('<button class="button secondary compact p3-item-research" type="button" data-wi-id="' + escapeHtml(item.work_item_id) + '" data-title="' + escapeHtml(item.title) + '"><i data-lucide="flask-conical" aria-hidden="true"></i><span>发起研究</span></button>');
    actions.push('<button class="button secondary compact p3-item-radar" type="button" data-wi-id="' + escapeHtml(item.work_item_id) + '" data-title="' + escapeHtml(item.title) + '"><i data-lucide="radar" aria-hidden="true"></i><span>雷达</span></button>');
    if (editable) {
      actions.push('<button class="button secondary compact" type="button" data-p3-status-edit="' + escapeHtml(item.work_item_id) + '"><i data-lucide="pencil" aria-hidden="true"></i><span>变更状态</span></button>');
    }
    return '<tr>' +
      '<td><div class="p3-workitem-title">' + escapeHtml(item.title) + '</div>' +
      (item.acceptance_criteria && item.acceptance_criteria.length
        ? '<div class="p3-workitem-criteria">' + escapeHtml(item.acceptance_criteria.join('；')) + '</div>' : '') + '</td>' +
      '<td><span class="p3-kind-tag ' + (kind === 'milestone' ? 'plan' : '') + '">' + escapeHtml(P3_KIND_LABELS[kind] || kind) + '</span></td>' +
      '<td>' + p3DeclaredPill(item.declared_status) + '</td>' +
      '<td>' + p3ObservedPill(item.observed_status) + '</td>' +
      '<td>' + p3InferredPill(item.inferred_status) + '</td>' +
      '<td><div class="p3-workitem-actions" style="flex-wrap:wrap">' + (links.join(' ') || '<span class="field-hint">无</span>') + '</div></td>' +
      '<td><div class="p3-workitem-actions">' + actions.join(' ') + '</div></td>' +
      '</tr>';
  }).join('');
  document.querySelectorAll('[data-p3-status-edit]').forEach((button) => button.addEventListener('click', () => {
    openP3Confirm(button.dataset.p3StatusEdit);
  }));
  document.querySelectorAll('.p3-item-research').forEach((button) => button.addEventListener('click', () => {
    const item = items.find((candidate) => candidate.work_item_id === button.dataset.wiId);
    startResearchForItem(button.dataset.wiId, button.dataset.title, (item && item.acceptance_criteria) || []);
  }));
  document.querySelectorAll('.p3-item-radar').forEach((button) => button.addEventListener('click', () => {
    runP3RadarForItem(button.dataset.wiId, button.dataset.title, button);
  }));

  const radar = data.radar || {};
  $('p3RadarStatus').textContent = radar.status === 'not_run' ? '未运行' : (radar.usable ? '可用' : '需复核');
  $('p3RadarStatus').className = 'status-pill ' + (radar.status === 'not_run' ? 'neutral' : radar.usable ? 'ok' : 'warn');
  $('p3RadarIntents').textContent = radar.intents != null ? String(radar.intents) : '-';
  $('p3RadarCandidates').textContent = radar.candidates != null ? String(radar.candidates) : '-';
  $('p3RadarShortlisted').textContent = radar.shortlisted != null ? String(radar.shortlisted) : '-';
  $('p3RadarSaved').textContent = radar.saved != null ? String(radar.saved) : '-';
  $('p3RadarEmpty').hidden = radar.status !== 'not_run';
}

function p3AllDocuments(documents) {
  if (!documents) return [];
  const byAuthority = documents.by_authority || {};
  return ['confirmed', 'candidate', 'excluded'].flatMap((authority) =>
    (byAuthority[authority] || []).map((doc) => Object.assign({}, doc, { authority }))
  );
}

function p3DocRow(doc) {
  const kindLabel = { charter: '纲领', plan: '计划', decision: '决策', experiment: '实验', report: '报告', paper_note: '论文笔记', code_doc: '代码文档', other: '其他' }[doc.kind] || doc.kind;
  const failed = doc.parse_status === 'failed';
  let actions = '';
  if (doc.authority === 'candidate') {
    actions += '<button class="button primary compact p3-doc-authority" type="button" data-doc-id="' + escapeHtml(doc.document_id) + '" data-authority="confirmed"><i data-lucide="check" aria-hidden="true"></i><span>确权</span></button>';
    actions += '<button class="button secondary compact p3-doc-authority" type="button" data-doc-id="' + escapeHtml(doc.document_id) + '" data-authority="excluded"><i data-lucide="x" aria-hidden="true"></i><span>排除</span></button>';
  } else if (doc.authority === 'confirmed') {
    actions += '<button class="button secondary compact p3-doc-authority" type="button" data-doc-id="' + escapeHtml(doc.document_id) + '" data-authority="excluded"><i data-lucide="x" aria-hidden="true"></i><span>排除</span></button>';
  } else if (doc.authority === 'excluded') {
    actions += '<button class="button secondary compact p3-doc-authority" type="button" data-doc-id="' + escapeHtml(doc.document_id) + '" data-authority="candidate"><i data-lucide="undo-2" aria-hidden="true"></i><span>恢复候选</span></button>';
  }
  const ragStatus = doc.rag_status || '';
  const ragLabel = ragStatus === 'indexed' ? ' · 已索引' : ragStatus === 'stale' ? ' · 索引过期' : '';
  return '<div class="p3-doc-row">' +
    '<span class="p3-kind-tag ' + (doc.kind === 'charter' || doc.kind === 'plan' ? 'plan' : '') + '">' + escapeHtml(kindLabel) + '</span>' +
    '<span class="doc-main"><span class="doc-path">' + escapeHtml(doc.path) + '</span><span class="doc-meta">' + escapeHtml((doc.title || '无标题') + (failed ? ' · 解析失败' : '') + ragLabel) + '</span></span>' +
    '<span class="p3-doc-actions">' + actions + '</span></div>';
}

function renderP3Evidence(data) {
  const documents = data.documents || null;
  const all = p3AllDocuments(documents);
  const snapshot = data.snapshot || null;
  const knowledge = (snapshot && snapshot.knowledge_state) || {};
  const rag = knowledge.rag || null;
  if (rag && rag.by_document) {
    all.forEach((doc) => { doc.rag_status = rag.by_document[doc.path] || ''; });
  }
  const stats = { confirmed: 0, candidate: 0, excluded: 0, failed: 0 };
  all.forEach((doc) => {
    stats[doc.authority] = (stats[doc.authority] || 0) + 1;
    if (doc.parse_status === 'failed') stats.failed += 1;
  });
  $('p3DocStats').textContent = all.length ? (all.length + ' 份文档') : '尚未发现文档';
  $('p3DocsConfirmed').innerHTML = all.filter((doc) => doc.authority === 'confirmed').map(p3DocRow).join('') || '<div class="p3-inbox-empty-row">没有已确权文档。确权后文档才作为计划分析依据。</div>';
  $('p3DocsCandidates').innerHTML = all.filter((doc) => doc.authority === 'candidate' && doc.parse_status !== 'failed').map(p3DocRow).join('') || '<div class="p3-inbox-empty-row">没有待确权文档。运行“检查状态”以自动发现文档。</div>';
  $('p3DocsFailed').innerHTML = all.filter((doc) => doc.parse_status === 'failed').map(p3DocRow).join('') || '<div class="p3-inbox-empty-row">没有解析失败的文档。</div>';
  $('p3DocsExcluded').innerHTML = all.filter((doc) => doc.authority === 'excluded').map(p3DocRow).join('') || '<div class="p3-inbox-empty-row">没有排除的文档。</div>';
  document.querySelectorAll('.p3-doc-authority').forEach((button) => button.addEventListener('click', () => {
    setP3DocumentAuthority(button.dataset.docId, button.dataset.authority, button);
  }));

  const knowledgeDocs = knowledge.documents || {};
  $('p3KnowledgeDocs').textContent = knowledgeDocs.total != null ? String(knowledgeDocs.total) : '-';
  $('p3RagIndexed').textContent = rag && rag.indexed != null ? String(rag.indexed) : '-';
  $('p3RagStale').textContent = rag && rag.stale != null ? String(rag.stale) : '-';
  $('p3RagMissing').textContent = rag && rag.missing != null ? String(rag.missing) : '-';
  if (rag && rag.collection) {
    $('p3RagModel').textContent = 'Collection: ' + rag.collection + (rag.model ? ' · ' + rag.model : '') + (rag.error ? ' · ' + rag.error : '');
  } else if (rag && rag.error) {
    $('p3RagModel').textContent = '无法读取知识库：' + rag.error;
  } else {
    $('p3RagModel').textContent = '尚未计算覆盖状态（点击“检查状态”）';
  }

  const sources = (snapshot && snapshot.evidence_state && snapshot.evidence_state.sources) || [];
  const evidenceReviews = (data.reviews || []).filter((item) => item.kind === 'evidence_change');
  $('p3EvidenceSources').innerHTML = sources.map((source) =>
    '<div class="audit-item"><span class="audit-item-icon"><i data-lucide="file-warning" aria-hidden="true"></i></span>' +
    '<div><p>' + escapeHtml(source.source_id || '未知来源') + '</p><div class="audit-evidence"><code>' + escapeHtml(source.status || '') + '</code></div></div></div>'
  ).join('') || '<div class="p3-inbox-empty-row">' + (evidenceReviews.length ? '有 ' + evidenceReviews.length + ' 项证据变化在待处理队列中。' : '暂无记录的证据来源变化。') + '</div>';
}

function renderP3Activity(data) {
  const activity = data.activity || {};
  const rows = [];
  (activity.jobs || []).forEach((job) => {
    const elapsed = job.started_at && job.ended_at
      ? Math.max(1, Math.round((Number(job.ended_at) - Number(job.started_at)) / 1000)) + ' 秒'
      : '-';
    const cancellable = ['pending', 'running'].includes(job.status);
    rows.push('<tr>' +
      '<td><div class="p3-workitem-title">研究查询 ' + escapeHtml(job.run_id) + '</div><div class="p3-workitem-criteria">' + escapeHtml(job.query || '') + '</div></td>' +
      '<td><span class="status-pill ' + (job.status === 'failed' || job.status === 'cancelled' ? 'error' : job.status === 'completed' ? 'ok' : job.status === 'running' || job.status === 'pending' ? 'warn' : 'neutral') + '">' + escapeHtml(P3_JOB_STATUS_LABELS[job.status] || job.status) + '</span></td>' +
      '<td>' + escapeHtml(elapsed) + '</td>' +
      '<td>' + (cancellable ? '<button class="button secondary compact p3-job-cancel" type="button" data-run-id="' + escapeHtml(job.run_id) + '"><i data-lucide="square" aria-hidden="true"></i><span>取消</span></button>' : '<span class="field-hint">—</span>') + '</td>' +
      '</tr>');
  });
  if (activity.radar_job) {
    rows.push('<tr>' +
      '<td><div class="p3-workitem-title">论文雷达</div></td>' +
      '<td><span class="status-pill neutral">' + escapeHtml(activity.radar_job.status || '') + '</span></td>' +
      '<td>-</td><td><span class="field-hint">—</span></td></tr>');
  }
  $('p3ActivityBody').innerHTML = rows.join('');
  $('p3ActivityEmpty').hidden = rows.length > 0;
  $('p3ActivityTable').style.display = rows.length ? '' : 'none';
  document.querySelectorAll('.p3-job-cancel').forEach((button) => button.addEventListener('click', () => {
    requestQueryCancellation(button.dataset.runId).then(() => loadP3State()).catch(() => {});
  }));

  $('p3EventLog').innerHTML = (activity.events || []).slice(0, 10).map((event) =>
    '<div class="p3-event-row"><code>' + escapeHtml(event.kind || '') + '</code><span class="event-detail">' + escapeHtml((event.payload && event.payload.path) || (event.payload && event.payload.title) || '') + '</span><time>' + escapeHtml(fmtDate(event.created_at)) + '</time></div>'
  ).join('') || '<div class="p3-inbox-empty-row">暂无事件。运行“检查状态”后开始记录。</div>';
}

function p3ReviewRow(review) {
  const kindLabel = P3_REVIEW_KIND_LABELS[review.kind] || review.kind;
  const sourceLabel = review.source === 'evidence_ledger' ? '证据台账' : '项目状态';
  const workItemNames = (review.work_items || []).map((item) => item.title).join('、');
  return '<div class="p3-inbox-row" data-review-id="' + escapeHtml(review.review_id) + '">' +
    '<div class="p3-inbox-main">' +
    '<span class="p3-kind-tag ' + (review.kind === 'run_failure' || review.kind === 'plan_drift' ? 'risk' : '') + '">' + escapeHtml(kindLabel) + '</span>' +
    '<div><strong>' + escapeHtml(review.summary) + '</strong>' +
    '<small>' + escapeHtml(review.proposed_action || '') + ' · ' + escapeHtml(sourceLabel) + (review.priority ? ' · 优先级 ' + review.priority : '') + (workItemNames ? ' · 影响工作项：' + escapeHtml(workItemNames) : '') + '</small></div></div>' +
    '<div class="p3-inbox-actions">' +
    '<button class="button secondary compact p3-review-action" type="button" data-status="dismissed"><i data-lucide="x" aria-hidden="true"></i><span>忽略</span></button>' +
    '<button class="button primary compact p3-review-action" type="button" data-status="confirmed"><i data-lucide="check" aria-hidden="true"></i><span>确认</span></button>' +
    '</div></div>';
}

function renderP3Inbox(data) {
  const reviews = data.reviews || [];
  const pending = reviews.filter((item) => item.status === 'pending');
  const history = reviews.filter((item) => item.status !== 'pending');
  $('p3InboxSummary').textContent = pending.length + ' 项待处理';
  $('p3InboxSummary').className = 'status-pill ' + (pending.length ? 'warn' : 'ok');
  $('p3InboxList').innerHTML = pending.map(p3ReviewRow).join('');
  $('p3InboxEmpty').hidden = pending.length > 0;
  $('p3InboxHistoryWrap').hidden = history.length === 0;
  $('p3InboxHistory').innerHTML = history.map(p3ReviewRow).join('');
  document.querySelectorAll('.p3-review-action').forEach((button) => button.addEventListener('click', () => {
    const row = button.closest('.p3-inbox-row');
    resolveP3Review(row.dataset.reviewId, button.dataset.status, button);
  }));
  $('p3ReviewCount').textContent = String(pending.length);
  $('p3InboxTabCount').textContent = String(pending.length);
}

async function refreshP3SelectedProject() {
  const projectId = selectedProjectId;
  if (!projectId) return;
  const button = $('p3RefreshProject');
  enterBusy(button, '检查中');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(projectId) + '/refresh', {});
    toast('状态已检查：新增事件 ' + data.new_events + '，发现文档 ' + data.discovery.parsed + ' 份', 'ok');
  } catch (error) {
    toast('检查失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
  loadProjects({});
}

async function setP3DocumentAuthority(documentId, authority, button) {
  if (!selectedProjectId) return;
  if (button) enterBusy(button, '处理中');
  try {
    await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/documents/' + encodeURIComponent(documentId) + '/authority', { authority });
    toast(authority === 'confirmed' ? '文档已确权' : authority === 'excluded' ? '文档已排除' : '已恢复候选', 'ok');
  } catch (error) {
    toast('文档操作失败：' + error.message, 'err');
    if (button) leaveBusy(button);
    return;
  }
  await loadP3State();
}

async function resolveP3Review(reviewId, status, button) {
  if (!selectedProjectId) return;
  if (button) enterBusy(button, '处理中');
  try {
    await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/reviews/' + encodeURIComponent(reviewId) + '/resolve', { status });
    toast(status === 'confirmed' ? '已确认该复核项' : '已忽略该复核项', 'ok');
  } catch (error) {
    toast('处理失败：' + error.message, 'err');
    if (button) leaveBusy(button);
    return;
  }
  await loadP3State();
}

function openP3Confirm(workItemId) {
  const state = p3StateCache[selectedProjectId];
  if (!state || !state.snapshot) return;
  const item = (state.snapshot.work_items || []).find((candidate) => candidate.work_item_id === workItemId);
  if (!item) return;
  p3ConfirmTarget = { work_item_id: workItemId, kind: item.kind, title: item.title };
  $('p3ConfirmTitle').textContent = item.kind === 'action' ? '完成后续行动' : '变更人工状态';
  $('p3ConfirmText').textContent = (item.kind === 'action'
    ? '确认后将把该行动标记为完成并从项目 YAML 的后续计划中移除：'
    : '该状态写入项目 YAML（人工计划的权威来源），不会自动推断：') + ' “' + item.title + '”';
  $('p3ConfirmField').hidden = item.kind === 'action';
  $('p3ConfirmStatus').value = ['planned', 'in_progress', 'completed', 'blocked'].includes(item.declared_status) ? item.declared_status : 'planned';
  $('p3ConfirmError').hidden = true;
  const dialog = $('p3ConfirmDialog');
  if (!dialog.open) dialog.showModal();
}

async function runP3Confirm(event) {
  event.preventDefault();
  const target = p3ConfirmTarget;
  if (!target || !selectedProjectId) return;
  const status = target.kind === 'action' ? 'completed' : ($('p3ConfirmStatus').value || 'planned');
  const button = $('p3ConfirmOk');
  enterBusy(button, '写入中');
  $('p3ConfirmError').hidden = true;
  try {
    await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/work-items/' + encodeURIComponent(target.work_item_id) + '/confirm', { declared_status: status });
    p3ConfirmTarget = null;
    $('p3ConfirmDialog').close();
    toast('人工状态已写入项目 YAML', 'ok');
  } catch (error) {
    $('p3ConfirmError').textContent = error.message;
    $('p3ConfirmError').hidden = false;
  } finally {
    leaveBusy(button);
  }
  await loadP3State();
}

function openP3Settings() {
  const state = p3StateCache[selectedProjectId];
  const project = (state && state.project) || {};
  $('p3cfgName').value = project.name || '';
  $('p3cfgPath').value = project.path || '';
  $('p3cfgDescription').value = project.description || '';
  $('p3cfgTestCommand').value = project.test_command || '';
  $('p3cfgDocumentDirs').value = ((project.documents && project.documents.directories) || []).join('\n');
  $('p3cfgDocumentFiles').value = ((project.documents && project.documents.root_files) || []).join('\n');
  $('p3cfgResultDirs').value = ((project.artifacts && project.artifacts.directories) || []).join('\n');
  $('p3cfgReportDirs').value = ((project.reports && project.reports.directories) || []).join('\n');
  $('p3SettingsMessage').textContent = '';
  $('p3SettingsMessage').className = 'form-message';
  const dialog = $('p3SettingsDialog');
  if (!dialog.open) dialog.showModal();
}

async function saveP3Settings(event) {
  event.preventDefault();
  if (!selectedProjectId) return;
  const name = $('p3cfgName').value.trim();
  const path = $('p3cfgPath').value.trim();
  if (!name || !path) {
    const target = name ? $('p3cfgPath') : $('p3cfgName');
    target.focus();
    $('p3SettingsMessage').textContent = '项目名称和本地目录不能为空';
    $('p3SettingsMessage').className = 'form-message error';
    return;
  }
  const button = $('p3SettingsSave');
  enterBusy(button, '保存设置');
  $('p3SettingsMessage').textContent = '';
  try {
    await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/settings', {
      project_id: selectedProjectId,
      name,
      path,
      description: $('p3cfgDescription').value.trim(),
      test_command: $('p3cfgTestCommand').value.trim(),
      document_dirs: $('p3cfgDocumentDirs').value,
      document_files: $('p3cfgDocumentFiles').value,
      result_dirs: $('p3cfgResultDirs').value,
      report_dirs: $('p3cfgReportDirs').value
    });
    $('p3SettingsDialog').close();
    toast('项目设置已保存', 'ok');
  } catch (error) {
    $('p3SettingsMessage').textContent = error.message;
    $('p3SettingsMessage').className = 'form-message error';
    toast('项目设置保存失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
  await loadP3State();
  loadProjects({});
}

function startResearchFromP3() {
  const state = p3StateCache[selectedProjectId];
  const summary = state && state.snapshot && state.snapshot.summary;
  queryProjectContext = { project_id: selectedProjectId, focus: (summary && summary.focus) || '' };
  if (summary && summary.focus) {
    $('queryText').value = '围绕当前研究重点“' + summary.focus + '”，找出证据缺口和下一步实验机会';
  }
  nav('query', { focus: true });
}

function startResearchForItem(workItemId, title, criteria) {
  queryProjectContext = { project_id: selectedProjectId, work_item_id: workItemId, focus: title };
  const gapText = criteria && criteria.length
    ? '验收标准：' + criteria.join('；')
    : '找出该工作的证据缺口和验证方式';
  $('queryText').value = '围绕研究重点“' + title + '”，' + gapText;
  nav('query', { focus: true });
}

async function runP3RadarForItem(workItemId, title, button) {
  if (!selectedProjectId) return;
  if (button) enterBusy(button, '雷达中');
  try {
    const data = await api('/api/projects/research/run', {
      project_id: selectedProjectId,
      work_item_id: workItemId,
      gap_source: title
    });
    if (data.ok && data.job_id) {
      await waitForProjectRadarJob(data.job_id, selectedProjectId);
      toast('论文雷达已运行，关联按搜索意图确定性匹配', 'ok');
    }
  } catch (error) {
    toast('雷达运行失败：' + error.message, 'err');
  } finally {
    if (button) leaveBusy(button);
  }
  loadP3State();
}

async function runP3Radar() {
  const button = $('p3RunRadar');
  enterBusy(button, '运行中');
  try {
    await runProjectRadar();
  } finally {
    leaveBusy(button);
  }
  loadP3State();
}

async function indexP3KnowledgeDocs() {
  if (!selectedProjectId) return;
  const button = $('p3IndexDocs');
  enterBusy(button, '索引中');
  $('p3IndexDocsState').textContent = '';
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/knowledge/index', {});
    if (data.ok) {
      const failedCount = (data.failed || []).length;
      $('p3IndexDocsState').textContent = '已索引 ' + data.indexed + ' 块 / ' + data.documents + ' 份文档' + (failedCount ? '，失败 ' + failedCount : '');
      toast('项目文档已加入知识库', 'ok');
    } else {
      $('p3IndexDocsState').textContent = data.error || '';
      toast('索引失败：' + (data.error || '未知错误'), 'err');
    }
  } catch (error) {
    $('p3IndexDocsState').textContent = error.message;
    toast('索引失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
  loadP3State();
}

function bindP3Events() {
  document.querySelectorAll('[data-p3-tab]').forEach((button) => button.addEventListener('click', () => {
    selectP3Tab(button.dataset.p3Tab);
  }));
  $('p3OpenInbox').addEventListener('click', () => selectP3Tab('inbox'));
  $('p3RefreshProject').addEventListener('click', () => refreshP3SelectedProject());
  $('p3OpenSettings').addEventListener('click', () => openP3Settings());
  $('p3StartResearch').addEventListener('click', () => startResearchFromP3());
  $('p3RunRadar').addEventListener('click', () => runP3Radar());
  $('p3IndexDocs').addEventListener('click', () => indexP3KnowledgeDocs());
  $('p3RunAudit').addEventListener('click', () => runP3Audit());
  $('p3ExperimentForm').addEventListener('submit', registerP3Experiment);
  $('p3ScanExperiments').addEventListener('click', scanP3Experiments);
  $('p3LoadMentor').addEventListener('click', loadP3MentorReport);
  $('p3ConfirmMentor').addEventListener('click', confirmP3MentorReport);
  $('p3IndexCode').addEventListener('click', indexP3Code);
  $('p3CodeForm').addEventListener('submit', queryP3Code);
  $('p3SettingsForm').addEventListener('submit', saveP3Settings);
  $('p3SettingsCancel').addEventListener('click', () => $('p3SettingsDialog').close());
  $('p3ConfirmForm').addEventListener('submit', runP3Confirm);
  $('p3ConfirmCancel').addEventListener('click', () => {
    p3ConfirmTarget = null;
    $('p3ConfirmDialog').close();
  });
}

function runProjectRadar() {
  const projectId = selectedProjectId;
  return api('/api/projects/research/run', { project_id: projectId })
    .then((data) => {
      if (!data.ok || !data.job_id) {
        throw new Error(data.error || '雷达启动失败');
      }
      return waitForProjectRadarJob(data.job_id, projectId);
    })
    .catch((err) => {
      toast('论文雷达运行失败：' + err.message, 'err');
    });
}

function waitForProjectRadarJob(jobId, projectId) {
  return new Promise((resolve) => {
    const poll = () => {
      fetch('/api/projects/research/jobs/' + encodeURIComponent(jobId), { cache: 'no-store' })
        .then((response) => response.json())
        .then((job) => {
          if (job.status === 'pending' || job.status === 'running') {
            window.setTimeout(poll, 1000);
            return;
          }
          resolve(job);
        })
        .catch(() => resolve(null));
    };
    poll();
  });
}

async function saveRegisteredProject() {
  const button = $('saveRegisteredProject');
  const name = $('registeredProjectName').value.trim();
  const path = $('registeredProjectPath').value.trim();
  if (!name || !path) {
    toast('请填写项目名称和本地目录', 'warn');
    (name ? $('registeredProjectPath') : $('registeredProjectName')).focus();
    return;
  }
  enterBusy(button, '保存项目');
  $('projectRegisterError').hidden = true;
  try {
    const milestone = $('registeredProjectMilestone').value.trim();
    const data = await api('/api/projects/save', {
      id: $('registeredProjectId').value.trim(),
      name,
      path,
      description: $('registeredProjectDescription').value.trim(),
      overall_goal: $('registeredProjectGoal').value.trim(),
      milestones: milestone ? [{ id: 'current-stage', title: milestone, status: 'in_progress' }] : [],
      next_actions: $('registeredProjectNextActions').value.trim(),
      test_command: $('registeredProjectTest').value.trim(),
      document_dirs: $('registeredDocumentDirs').value.trim(),
      result_dirs: $('registeredResultDirs').value.trim(),
      report_dirs: $('registeredReportDirs').value.trim()
    });
    if (!data.ok) throw new Error(data.error || '项目保存失败');
    selectedProjectId = data.project_id || (data.project && data.project.project && data.project.project.id) || '';
    $('projectRegisterPanel').open = false;
    $('projectRegisterForm').hidden = true;
    await loadProjects();
    toast('项目已登记，首次快照已建立（发现 ' + ((data.p3.discovery || {}).new || 0) + ' 份文档）', 'ok');
  } catch (error) {
    $('projectRegisterErrorMessage').textContent = error.message;
    $('projectRegisterError').hidden = false;
  } finally {
    leaveBusy(button);
  }
}

function renderPapers(papers) {
  if (!papers || !papers.length) {
    $('papersTable').innerHTML = '';
    $('inboxEmpty').hidden = false;
    return;
  }
  $('inboxEmpty').hidden = true;
  const sorted = papers.slice().sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const hasLlm = papers.some((paper) => paper.llm_score != null);
  const rows = sorted.map((paper) => {
    const level = paper.reading_level || 'skip';
    const levelLabel = { deep: '精读', skim: '浏览', skip: '跳过' }[level] || level;
    const reviewPending = paper.review_status === 'unreviewed' || paper.candidate_status === 'needs_deeper_review';
    const reviewNotice = reviewPending
      ? '<br><span class="status-pill warn">' + (paper.candidate_status === 'needs_deeper_review' ? '深度语义评审未完成' : '语义评审未完成') + '</span>' +
        (paper.review_error_code ? '<br><small>错误码：' + escapeHtml(paper.review_error_code) + '</small>' : '') +
        (paper.review_error ? '<br><small>' + escapeHtml(paper.review_error) + '</small>' : '') +
        '<br><small>' + escapeHtml(paper.review_next_action || '可重试或人工复核') + '</small>'
      : '';
    return '<tr><td><span class="reading-badge ' + escapeHtml(level) + '">' + escapeHtml(levelLabel) + '</span></td>' +
      '<td><strong>' + Number(paper.score || 0).toFixed(3) + '</strong></td>' +
      (hasLlm ? '<td>' + Number(paper.keyword_score || 0).toFixed(3) + '</td>' +
        '<td>' + (paper.llm_score != null ? Number(paper.llm_score).toFixed(0) : '-') + '</td>' : '') +
      '<td><strong>' + escapeHtml(paper.title) + '</strong><br><small>' + escapeHtml(paper.id) + '</small>' +
      (paper.llm_reason ? '<br><small>' + escapeHtml(paper.llm_reason) + '</small>' : '') + reviewNotice + '</td>' +
      '<td>' + escapeHtml((paper.reasons || []).join('；')) + '</td></tr>';
  }).join('');
  $('papersTable').innerHTML = '<thead><tr><th>建议</th><th>综合分</th>' +
    (hasLlm ? '<th>关键词分</th><th>AI 分</th>' : '') +
    '<th>论文</th><th>匹配依据</th></tr></thead><tbody>' + rows + '</tbody>';
}

const reportIconMap = { '.md': 'file-text', '.html': 'file-code-2', '.json': 'braces', '.jsonl': 'list-tree', '.yaml': 'file-cog', '.yml': 'file-cog', '.csv': 'table-2' };

function allReports() {
  if (!statusCache) return [];
  const merged = statusCache.reports || [];
  const unique = new Map();
  merged.forEach((item) => unique.set(item.path, item));
  return Array.from(unique.values());
}

function reportExtension(item) {
  const name = String(item.name || item.path || '').toLowerCase();
  const index = name.lastIndexOf('.');
  return index >= 0 ? name.slice(index) : '';
}

function renderReports() {
  if (!statusCache) return;
  const all = allReports();
  const filter = $('reportFilter').value || 'all';
  const query = $('reportSearch').value.trim().toLowerCase();
  const sortBy = $('reportSort').value || 'time-desc';
  let rows = all.filter((item) => {
    const path = String(item.path || '').toLowerCase();
    return (filter === 'all' || path.endsWith(filter)) && (!query || path.includes(query));
  });
  rows.sort((a, b) => {
    if (sortBy === 'time-asc') return Number(a.modified || 0) - Number(b.modified || 0);
    if (sortBy === 'name-asc') return String(a.path || '').localeCompare(String(b.path || ''), 'zh-CN');
    if (sortBy === 'size-desc') return Number(b.size || 0) - Number(a.size || 0);
    return Number(b.modified || 0) - Number(a.modified || 0);
  });

  $('reportNavCount').textContent = String(all.length);
  $('reportSummary').textContent = rows.length === all.length ? '共 ' + all.length + ' 份研究产物' : '找到 ' + rows.length + ' / ' + all.length + ' 份研究产物';
  $('reportsEmpty').hidden = rows.length > 0;
  $('reportsCards').innerHTML = rows.map((item) => {
    const path = String(item.path || '');
    const parts = path.replace(/\\/g, '/').split('/');
    const name = parts.pop() || path;
    const parent = parts.join('/') || '项目根目录';
    const ext = reportExtension(item);
    const icon = reportIconMap[ext] || 'file';
    const selected = selectedReportPath === path;
    return '<button type="button" class="report-row" role="option" aria-selected="' + selected + '" data-open="' + escapeHtml(path) + '" aria-label="打开 ' + escapeHtml(name) + '">' +
      '<span class="report-type-icon"><i data-lucide="' + icon + '" aria-hidden="true"></i></span>' +
      '<span class="report-row-copy"><span class="report-row-name">' + escapeHtml(name) + '</span><span class="report-row-path">' + escapeHtml(parent) + '</span></span>' +
      '<span class="report-row-meta"><span>' + fmtDate(item.modified) + '</span><span>' + fmtSize(item.size) + '</span></span>' +
      '</button>';
  }).join('');
  $('reportsCards').querySelectorAll('[data-open]').forEach((button) => button.addEventListener('click', () => openFile(button.dataset.open)));
  refreshIcons();
}

async function openFile(path) {
  selectedReportPath = path;
  document.querySelectorAll('.report-row').forEach((row) => row.setAttribute('aria-selected', String(row.dataset.open === path)));
  const parts = path.replace(/\\/g, '/').split('/');
  $('previewTitle').textContent = parts[parts.length - 1] || '成果预览';
  $('previewPath').textContent = path;
  $('previewEmpty').hidden = true;
  const url = '/api/file?path=' + encodeURIComponent(path);
  const lowerPath = path.toLowerCase();
  if (lowerPath.endsWith('.html') || lowerPath.endsWith('.md') || lowerPath.endsWith('.markdown')) {
    $('preview').hidden = false;
    $('fileText').hidden = true;
    $('preview').src = lowerPath.endsWith('.html') ? url : '/api/markdown?path=' + encodeURIComponent(path);
    return;
  }
  $('preview').hidden = true;
  $('preview').removeAttribute('src');
  $('fileText').hidden = false;
  $('fileText').textContent = '正在读取...';
  try {
    const response = await authFetch(url);
    if (!response.ok) throw new Error('文件读取失败（HTTP ' + response.status + '）');
    $('fileText').textContent = await response.text();
  } catch (error) {
    $('fileText').textContent = error.message;
    toast(error.message, 'err');
  }
}

function modelPayload(tier) {
  const selection = tier || $('testModelSelect').value;
  const model = MODEL_TIERS.includes(selection) ? tierModelPayload(selection) : featureModelPayload(selection);
  return Object.assign(model, {
    model_preset: selection,
    prompt: $('probePrompt').value
  });
}

async function runModelTest() {
  const button = $('testModel');
  enterBusy(button, '测试连接');
  $('modelOutput').hidden = true;
  $('modelResultCard').hidden = true;
  $('modelEmpty').hidden = true;
  try {
    const data = await api('/api/model/test', modelPayload());
    if (data.ok) {
      $('modelResultCard').hidden = false;
      $('modelResultCard').innerHTML =
        '<div class="rc-row"><span class="rc-label">模型</span><span class="rc-val">' + escapeHtml(data.model || '') + '</span></div>' +
        '<div class="rc-row"><span class="rc-label">耗时</span><span class="rc-val">' + Number(data.elapsed_ms || 0) + ' ms</span></div>' +
        '<div class="rc-row"><span class="rc-label">Token</span><span class="rc-val">输入 ' + Number((data.usage || {}).prompt_tokens || 0) + ' / 输出 ' + Number((data.usage || {}).completion_tokens || 0) + '</span></div>' +
        '<div class="rc-content">' + escapeHtml(data.content || '') + '</div>';
      toast('模型连接正常', 'ok');
    } else {
      $('modelOutput').hidden = false;
      $('modelOutput').textContent = JSON.stringify(data, null, 2);
      toast(data.error || '模型连接失败，请检查地址、模型与凭证', 'err');
    }
  } catch (error) {
    $('modelOutput').hidden = false;
    $('modelOutput').textContent = error.message;
    toast('网络错误：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function saveModel() {
  const button = $('saveModel');
  enterBusy(button, '保存配置');
  try {
    const data = await api('/api/model/save', {
      tier_models: allTierModelsPayload(),
      feature_models: allFeatureModelsPayload(),
      embedding_base_url: $('embeddingBaseUrl').value,
      embedding_api_key: $('embeddingApiKey').value,
      embedding_model: $('embeddingModel').value,
      web_search_provider: $('webSearchProvider').value,
      serpapi_api_key: $('serpapiApiKey').value,
      bing_api_key: $('bingApiKey').value,
      google_api_key: $('googleApiKey').value,
      google_cse_id: $('googleCseId').value,
      depth: $('depthSelect').value
    });
    if (data.ok) {
      toast('配置已保存到本地（' + Number(data.saved || 0) + ' 项）', 'ok');
      await refreshStatus();
    } else {
      toast(data.error || '保存失败', 'err');
    }
  } catch (error) {
    toast('保存出错：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

function paperSearchFailureMessage(data) {
  const detail = String(data && data.error ? data.error : '');
  if (/\b429\b|rate[ -]?limit|too many requests/i.test(detail)) {
    return '搜索过于频繁，已被限流，建议稍后再试。';
  }
  if (/\b401\b|\b403\b|unauthorized|forbidden/i.test(detail)) {
    return '数据源拒绝了访问，请检查对应的 API 密钥或访问权限。';
  }
  if (/timeout|timed out|超时/i.test(detail)) {
    return '数据源响应超时，请检查网络后重试。';
  }
  if (/没有新的论文|没有结果/.test(detail)) return detail;
  return detail || '论文发现失败，请检查数据源和研究画像后重试。';
}

function hideInboxError() {
  $('inboxError').hidden = true;
  $('inboxErrorDetails').open = false;
  $('inboxOutput').textContent = '';
}

function showInboxError(data) {
  const message = paperSearchFailureMessage(data);
  $('inboxErrorMessage').textContent = message;
  $('inboxOutput').textContent = JSON.stringify(data, null, 2);
  $('inboxError').hidden = false;
  $('inboxStats').textContent = '发现失败';
  $('inboxStats').className = 'status-pill error';
  toast(message, 'err');
}

async function runInbox() {
  const button = $('runInbox');
  const mode = document.querySelector('input[name="profileMode"]:checked').value;
  if (mode === 'file' && !$('profilePath').value) {
    toast('请选择研究画像，或临时创建一个画像', 'warn');
    return;
  }
  enterBusy(button, '发现论文');
  hideInboxError();
  $('inboxEmpty').hidden = true;
  $('papersTable').innerHTML = '';
  $('inboxStats').textContent = '正在发现论文…';
  $('inboxStats').className = 'status-pill warn';
  const started = Date.now();
  const progressTimer = window.setInterval(() => {
    $('inboxStats').textContent = '发现中 · ' + Math.max(1, Math.round((Date.now() - started) / 1000)) + ' 秒';
  }, 1000);
  try {
    const payload = {
      profile_mode: mode,
      source: $('paperSource').value,
      fixture: $('fixturePath').value,
      out_dir: $('inboxOut').value,
      max_results: Number($('maxResults').value || 50),
      review_limit: 40,
      use_llm_scoring: $('useLlm').checked
    };
    if (mode === 'file') payload.profile = $('profilePath').value;
    else Object.assign(payload, {
      profile_name: $('profileName').value || '临时画像',
      fields: $('profileFields').value,
      keywords: $('profileKeywords').value,
      description: $('profileDescription').value,
      negative_keywords: $('profileNegativeKeywords').value
    });
    const data = await api('/api/papers/inbox', payload);
    if (data.ok) {
      hideInboxError();
      const seenText = Number(data.stats.previously_seen || 0) ? ' · 排除重复 ' + Number(data.stats.previously_seen) : '';
      $('inboxStats').textContent = '精读 ' + data.stats.deep + ' · 浏览 ' + data.stats.skim + ' · 跳过 ' + data.stats.skip + seenText;
      if (data.review_status === 'unreviewed') {
        $('inboxStats').textContent += ' · 语义评审未完成';
        $('inboxStats').className = 'status-pill warn';
        toast(data.review_next_action || '语义评审未完成，请配置模型后重试。', 'warn');
      } else {
        $('inboxStats').className = 'status-pill ok';
      }
      $('promoteInbox').value = data.json_path;
      renderPapers(data.papers || []);
      await Promise.all([refreshStatus(), renderDashboard()]);
      toast(data.message || ('论文收件箱已更新，共 ' + (data.papers || []).length + ' 篇'), 'ok');
    } else {
      showInboxError(data);
    }
  } catch (error) {
    showInboxError({ ok: false, error: error.message });
  } finally {
    window.clearInterval(progressTimer);
    leaveBusy(button);
  }
}

async function saveProfile() {
  const button = $('saveProfile');
  const name = $('profileName').value.trim();
  if (!name) {
    $('profileName').focus();
    toast('请先填写画像名称', 'warn');
    return;
  }
  enterBusy(button, '保存画像');
  try {
    const data = await api('/api/profile/save', {
      profile_name: name,
      fields: $('profileFields').value,
      keywords: $('profileKeywords').value,
      description: $('profileDescription').value,
      negative_keywords: $('profileNegativeKeywords').value
    });
    if (data.ok) {
      toast('研究画像已保存：' + data.name, 'ok');
      resetProfileOptimization();
      await refreshStatus();
    } else toast(data.error || '画像保存失败', 'err');
  } catch (error) {
    toast('画像保存失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function runPromotion() {
  const button = $('runPromote');
  if (!$('promoteInbox').value.trim()) {
    $('promoteInbox').focus();
    toast('请先选择论文收件箱文件', 'warn');
    return;
  }
  if ($('indexDocs').checked && !hasEmbeddingCredential()) {
    toast('写入向量索引需要 Embedding 凭证，请先完成配置', 'warn');
    nav('model');
    return;
  }
  enterBusy(button, '写入知识库');
  $('promotionOutput').hidden = true;
  $('promotionEmpty').hidden = true;
  $('promotionStage').textContent = '入库中';
  $('promotionStage').className = 'status-pill warn';
  $('promotionOutput').hidden = false;
  $('promotionOutput').textContent = '=== 入库进展 ===\n正在读取收件箱并准备写入…';
  try {
    const defaultModel = tierModelPayload($('depthSelect').value);
    const data = await api('/api/papers/promote', {
      inbox: $('promoteInbox').value,
      out_dir: $('promoteOut').value,
      pdf_dir: $('pdfDir').value,
      full_text: $('fullText').checked,
      download_pdfs: $('downloadPdfs').checked,
      index: $('indexDocs').checked,
      pin: $('pinIds').value,
      embedding_base_url: $('embeddingBaseUrl').value || defaultModel.base_url,
      embedding_api_key: $('embeddingApiKey').value || defaultModel.api_key,
      embedding_model: $('embeddingModel').value
    });
    $('promotionOutput').hidden = false;
    $('promotionOutput').textContent = JSON.stringify(data, null, 2);
    if (data.ok) {
      $('promotionStage').textContent = '已完成';
      $('promotionStage').className = 'status-pill ok';
      await Promise.all([refreshStatus(), renderDashboard()]);
      toast('知识库已更新：' + Number(data.papers || 0) + ' 篇论文，' + Number(data.indexed || 0) + ' 条索引；已生成中文入库总结', 'ok');
    } else {
      $('promotionStage').textContent = '执行失败';
      $('promotionStage').className = 'status-pill error';
      toast(data.reason || data.error || '知识入库失败', 'err');
    }
  } catch (error) {
    $('promotionOutput').hidden = false;
    $('promotionOutput').textContent = error.message;
    $('promotionStage').textContent = '执行失败';
    $('promotionStage').className = 'status-pill error';
    toast('知识入库失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function rebuildVectorIndex() {
  const button = $('rebuildVectorIndex');
  enterBusy(button, '重建索引');
  try {
    const data = await api('/api/knowledge/index/rebuild', {
      source_dir: $('rebuildSourceDir').value,
      collection_name: $('rebuildCollectionName').value,
      embedding_base_url: $('embeddingBaseUrl').value,
      embedding_api_key: $('embeddingApiKey').value,
      embedding_model: $('embeddingModel').value
    });
    if (!data.ok) {
      toast(data.error || '索引重建失败', 'err');
      return;
    }
    $('rebuildCollectionName').value = '';
    await refreshStatus();
    toast('已重建 ' + Number(data.indexed || 0) + ' 条向量；旧索引仍保留。', 'ok');
  } catch (error) {
    toast('索引重建失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function deleteVectorCollection(collectionName) {
  if (!collectionName || !window.confirm('确认删除旧索引 “' + collectionName + '”？此操作不会删除知识文档。')) return;
  try {
    const data = await api('/api/knowledge/index/delete', { collection_name: collectionName });
    if (!data.ok) {
      toast(data.error || '删除索引失败', 'err');
      return;
    }
    await refreshStatus();
    toast('旧索引已删除：' + collectionName, 'ok');
  } catch (error) {
    toast('删除索引失败：' + error.message, 'err');
  }
}

function resetQueryControls() {
  const cancelButton = $('cancelQuery');
  if (cancelButton) {
    cancelButton.hidden = true;
    cancelButton.disabled = false;
    if (cancelButton.dataset.previousHtml) {
      cancelButton.innerHTML = cancelButton.dataset.previousHtml;
      delete cancelButton.dataset.previousHtml;
    }
  }
  $('runQuery').hidden = false;
  refreshIcons();
}

function markCancelRequested(message) {
  const button = $('cancelQuery');
  if (!button) return;
  if (!button.dataset.previousHtml) button.dataset.previousHtml = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<span class="spin" aria-hidden="true"></span><span>' + escapeHtml(message) + '</span>';
  refreshIcons();
}

async function requestQueryCancellation(runId, reason = 'user') {
  const response = await authFetch('/api/query/jobs/' + runId + '/cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 409) {
    throw new Error(data.error || '取消请求失败');
  }
  return data;
}

function submitIdempotencyKey(bodyText) {
  // Stable key for one user action: an identical retry (e.g. after a lost response)
  // reuses the same run via server-side replay instead of creating a duplicate.
  let h1 = 5381, h2 = 52711;
  for (let i = 0; i < bodyText.length; i++) {
    const c = bodyText.charCodeAt(i);
    h1 = ((h1 * 33) ^ c) >>> 0;
    h2 = ((h2 * 31) ^ c) >>> 0;
  }
  return 'wb-' + h1.toString(16) + h2.toString(16);
}

async function runQuery() {
  const button = $('runQuery');
  const query = $('queryText').value.trim();
  if (!query) {
    $('queryText').focus();
    toast('请输入需要研究的问题', 'warn');
    return;
  }
  if (!hasReasoningCredential()) {
    toast('请先配置推理模型凭证', 'warn');
    nav('model');
    return;
  }

  enterBusy(button, '提交任务');
  $('queryOutput').hidden = true;
  $('queryOutput').textContent = '';
  $('queryReportPreview').hidden = true;
  $('queryReportPreview').removeAttribute('src');
  $('queryResultMeta').hidden = true;
  $('queryResultMeta').textContent = '';
  $('queryEmpty').hidden = true;
  $('queryStage').textContent = '提交研究任务...';
  $('queryStage').className = 'status-pill warn';

  let runId = '';
  const queryDepth = normalizeTier($('queryDepth').value || $('depthSelect').value);
  let runTimeoutSeconds = 300;
  const projectContext = queryProjectContext;
  try {
    const bodyText = JSON.stringify(Object.assign(modelPayload(queryDepth), {
      query,
      output_dir: $('queryOut').value,
      embedding_base_url: $('embeddingBaseUrl').value,
      embedding_api_key: $('embeddingApiKey').value,
      embedding_model: $('embeddingModel').value,
      depth: queryDepth,
      project_id: projectContext ? (projectContext.project_id || '') : '',
      work_item_id: projectContext ? (projectContext.work_item_id || '') : ''
    }));
    const submitRes = await authFetch('/api/query/jobs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Idempotency-Key': submitIdempotencyKey(bodyText)
      },
      body: bodyText
    });
    const submitData = await submitRes.json().catch(() => ({}));
    if (!submitRes.ok) {
      const err = submitData.error;
      let message;
      if (err && typeof err === 'object') {
        message = err.message || '提交失败';
        if (err.action) message += '。' + err.action;
        if (err.code) message += '（' + err.code + '）';
      } else {
        message = err || ('提交失败（HTTP ' + submitRes.status + '）');
      }
      if (submitRes.status === 429) {
        const retryAfter = submitRes.headers.get('Retry-After');
        if (retryAfter) message += '。建议 ' + retryAfter + ' 秒后重试';
      }
      throw new Error(message);
    }
    runId = submitData.run_id;
    runTimeoutSeconds = Math.max(1, Number(submitData.timeout_seconds || 300));
    queryProjectContext = null;
    $('queryResultBand').dataset.activeRun = runId;
    activeQuery = { runId, cancelRequested: false, timedOut: false, timeoutSeconds: runTimeoutSeconds };
    // The result panel owns the running state; the submit button is not a progress indicator.
    leaveBusy(button);
  } catch (error) {
    $('queryStage').textContent = '提交失败';
    $('queryStage').className = 'status-pill error';
    toast('任务提交失败：' + error.message, 'err');
    leaveBusy(button);
    return;
  }

  const started = Date.now();
  const elapsedTimer = window.setInterval(() => {
    const elapsed = Math.max(1, Math.round((Date.now() - started) / 1000));
    const timingOut = activeQuery && activeQuery.runId === runId && activeQuery.timedOut;
    $('queryStage').textContent = timingOut ? '已到档位时限 · 正在提交报告 · ' + elapsed + ' 秒' : '已运行 ' + elapsed + ' 秒';
  }, 1000);

  const nodeStates = {};
  const nodeDetails = {};
  const nodeLabels = {
    research_plan:'研究计划', rag_agent:'RAG 检索', web_agent:'Web 搜索',
    model_agent:'模型分析', evidence_merge:'证据合并', arbitration:'冲突仲裁',
    synthesize:'报告合成', verify_revise:'核验修订', gap_research:'缺口补证',
    factcheck:'复核完成', deep_research:'深化研究', report_draft:'报告初稿',
    verification_round:'第一轮核验', targeted_gap_research:'针对性补证',
    reanalysis:'重新分析', final_commit:'最终提交'
  };
  const updateNodeDisplay = () => {
    const order = ['research_plan', 'rag_agent', 'web_agent', 'model_agent', 'evidence_merge', 'arbitration', 'synthesize', 'report_draft', 'verification_round', 'verify_revise', 'targeted_gap_research', 'gap_research', 'reanalysis', 'factcheck', 'deep_research', 'final_commit'];
    const labels = Object.assign({}, nodeLabels);
    Object.keys(nodeDetails).forEach(function(k){ if (labels[k]) labels[k] += ' · ' + nodeDetails[k]; });
    const lines = order.filter(function(k){ return nodeStates[k]; }).map(function(k){ return (nodeStates[k]==='completed'?'\u2705':nodeStates[k]==='failed'?'\u274c':(nodeStates[k]==='unreviewed'||nodeStates[k]==='fallback')?'\u26a0\ufe0f':'\u23f3') + ' ' + labels[k]; });
    if (lines.length) {
      $('queryOutput').textContent = '=== 节点状态 ===\n' + lines.join('\n');
      $('queryOutput').hidden = false;
    }
  };

  const es = new EventSource('/api/query/jobs/' + runId + '/events');
  es.addEventListener('done', function(){ es.close(); });
  es.onmessage = function(event) {
    try {
      const evt = JSON.parse(event.data);
      if (evt.stage && evt.status) {
        nodeStates[evt.stage] = evt.status;
        const metadata = evt.metadata || {};
        if (metadata.kept_count != null || metadata.result_count != null) {
          const kept = metadata.kept_count != null ? metadata.kept_count : '-';
          const total = metadata.result_count != null ? metadata.result_count : '-';
          nodeDetails[evt.stage] = '有效 ' + kept + ' / 召回 ' + total;
        } else if (Array.isArray(metadata.provider_trace) && metadata.provider_trace.length) {
          nodeDetails[evt.stage] = metadata.provider_trace.map((item) => item.provider + ':' + item.status).join(', ');
        } else if (metadata.round != null) {
          nodeDetails[evt.stage] = '第 ' + metadata.round + ' 轮';
        }
        updateNodeDisplay();
        $('queryStage').textContent = (nodeLabels[evt.stage] || evt.stage || '').replace(/_/g, ' ') + ' · ' + Math.round((Date.now() - started) / 1000) + ' 秒';
      }
    } catch (e) { /* ignore parse errors */ }
  };
  let sseErrors = 0;
  es.onerror = function() {
    if (es.readyState === EventSource.CLOSED) {
      sseErrors++;
      if (sseErrors <= 1) {
        // Browser may auto-reconnect once; only toast on permanent close
      }
      es.close();
    }
  };

  let finalResult = null;
  const pollInterval = window.setInterval(async function() {
    try {
      const res = await authFetch('/api/query/jobs/' + runId);
      if (!res.ok) return;
      const job = await res.json();
      const terminalStatuses = ['completed', 'completed_with_warnings', 'completed_diagnostic', 'timed_out_with_report', 'timed_out', 'cancelled', 'failed'];
      if (terminalStatuses.includes(job.status)) {
        window.clearInterval(pollInterval);
        window.clearInterval(elapsedTimer);
        window.clearTimeout(queryTimeout);
        es.close();
        finalResult = job;
        $('queryOutput').hidden = false;
        const reportPath = job.report_md_path || ((job.artifacts || {}).markdown_path || '');
        const hasReport = Boolean(job.has_report && (reportPath || job.final_answer));
        const warningStatus = job.status === 'completed_with_warnings' || job.status === 'timed_out_with_report';
        if (job.status === 'completed_diagnostic') {
          $('queryStage').textContent = '完成（仅诊断） · ' + Math.round((Date.now() - started) / 1000) + ' 秒';
          $('queryStage').className = 'status-pill warn';
          const diagnosticPath = ((job.artifacts || {}).diagnostic_markdown_path || '');
          if (diagnosticPath) {
            $('queryOutput').hidden = true;
            $('queryReportPreview').src = '/api/markdown?path=' + encodeURIComponent(diagnosticPath);
            $('queryReportPreview').hidden = false;
          } else {
            $('queryOutput').textContent = job.final_answer || '运行未通过交付门禁。';
          }
          $('queryResultMeta').textContent = '交付状态：diagnostic_only\n' + (job.error || job.warning || '结果已保留为诊断产物，不进入正式报告列表。');
          $('queryResultMeta').hidden = false;
          toast('运行未通过交付门禁，已保留诊断产物', 'warn');
        } else if (hasReport || job.status === 'completed' || job.status === 'completed_with_warnings') {
          const stageLabels = {
            completed:'完成', completed_with_warnings:'完成（有警告）',
            timed_out_with_report:'超时（报告已保留）', failed:'失败（报告已保留）',
            cancelled:'已取消（报告已保留）'
          };
          $('queryStage').textContent = (stageLabels[job.status] || '报告已保留') + ' · ' + Math.round((Date.now() - started) / 1000) + ' 秒';
          $('queryStage').className = 'status-pill ' + (warningStatus || !['completed'].includes(job.status) ? 'warn' : 'ok');
          if (reportPath) {
            $('queryOutput').hidden = true;
            $('queryReportPreview').src = '/api/markdown?path=' + encodeURIComponent(reportPath);
            $('queryReportPreview').hidden = false;
          } else {
            $('queryOutput').textContent = job.final_answer || '任务已完成，但没有生成可显示的报告。';
            $('queryOutput').hidden = false;
          }
          const meta = [
            '研究管线：' + (job.pipeline || 'unknown'),
            '来源状态：' + JSON.stringify(job.source_statuses || {}),
            '交付完整性：' + ({deliverable:'完整', limited:'部分完成', diagnostic_only:'仅诊断'}[job.delivery_status] || '未记录'),
            '引用核验：' + (job.factcheck_status || '未记录'),
            (job.quality || {}).sections_failed ? '未完成扩展问题：' + job.quality.sections_failed + '/' + job.quality.total_sections : '',
            job.warning ? '警告：' + job.warning : '',
            job.error && job.status !== 'completed' ? '终止原因：' + job.error : ''
          ].filter(Boolean);
          $('queryResultMeta').textContent = meta.join('\n');
          $('queryResultMeta').hidden = false;
          toast(warningStatus || job.status !== 'completed' ? '报告已保留，请查看警告' : '研究任务已完成', warningStatus || job.status !== 'completed' ? 'warn' : 'ok');
        } else {
          $('queryStage').textContent = job.status === 'failed' ? '执行失败' : job.status === 'timed_out' ? '执行超时' : '已取消';
          $('queryStage').className = 'status-pill error';
          const progress = $('queryOutput').textContent || '=== 节点状态 ===\n未收到节点事件';
          $('queryOutput').textContent = progress + '\n\n=== 执行结果 ===\n' + (job.error || JSON.stringify(job, null, 2));
          toast(job.error || '任务未完成', 'err');
        }
        await Promise.all([refreshStatus(), renderDashboard()]);
        leaveBusy(button);
        $('queryResultBand').removeAttribute('data-active-run');
        if (activeQuery && activeQuery.runId === runId) activeQuery = null;
        resetQueryControls();
      }
    } catch (e) { /* ignore poll errors */ }
  }, 1000);

  const queryTimeout = window.setTimeout(function() {
    if (finalResult || !activeQuery || activeQuery.runId !== runId) return;
    activeQuery.timedOut = true;
    $('queryStage').textContent = '已到档位时限 · 后端正在保存报告与 trace';
    $('queryStage').className = 'status-pill warn';
    toast('已到当前档位时限，等待后端提交已生成结果', 'warn');
  }, runTimeoutSeconds * 1000);

  // Show cancel button, hide run button
  if ($('cancelQuery')) { $('cancelQuery').hidden = false; }
  if ($('runQuery')) { $('runQuery').hidden = true; }
}

async function cancelQuery() {
  const button = $('cancelQuery');
  if (!button || button.disabled) return;
  const runId = activeQuery ? activeQuery.runId : '';
  if (!runId) {
    toast('没有可取消的任务', 'warn');
    return;
  }
  const queryContext = activeQuery;
  queryContext.cancelRequested = true;
  markCancelRequested('正在取消');
  try {
    const data = await requestQueryCancellation(runId);
    if (activeQuery !== queryContext) return;
    if (data.cancel_requested) {
      queryContext.cancelRequested = true;
      $('queryStage').textContent = '已请求取消 · 等待当前步骤结束';
      $('queryStage').className = 'status-pill warn';
      toast('已请求取消任务', 'ok');
    } else {
      toast(data.error || '任务已经结束，正在读取最终状态', 'info');
    }
  } catch (e) {
    queryContext.cancelRequested = false;
    button.disabled = false;
    if (button.dataset.previousHtml) button.innerHTML = button.dataset.previousHtml;
    toast('取消请求失败：' + e.message, 'err');
    refreshIcons();
  }
}

async function renderDashboard() {
  try {
    const response = await authFetch('/api/knowledge/stats');
    if (!response.ok) throw new Error('统计接口返回 ' + response.status);
    const stats = await response.json();
    const totals = stats.totals || {};
    const corpus = stats.corpus || {};
    const vectorStore = stats.vector_store || {};
    const reports = stats.reports || {};

    $('dashDocCount').textContent = Number(totals.documents || 0);
    $('dashChunkCount').textContent = Number(totals.vector_chunks || 0).toLocaleString('zh-CN');
    $('dashPaperCount').textContent = Number(totals.papers || 0);
    $('dashReportCount').textContent = Number(totals.reports || 0);
    $('dashTotalSize').textContent = fmtSize(Number(totals.total_size_kb || 0) * 1024);
    $('workflowPaperMeta').textContent = Number(totals.papers || 0) ? totals.papers + ' 篇论文' : '等待开始';
    $('workflowKnowledgeMeta').textContent = Number(totals.documents || 0) ? totals.documents + ' 份文档' : '等待开始';
    $('workflowReportMeta').textContent = Number(totals.reports || 0) ? totals.reports + ' 份成果' : '暂无报告';

    const categories = corpus.categories || {};
    const categoryLabels = corpus.category_labels || {};
    const categoryNames = Object.keys(categories);
    const categoryMax = Math.max(1, ...categoryNames.map((name) => Number((categories[name] || {}).count || 0)));
    $('dashCategories').innerHTML = categoryNames.length ? categoryNames.map((name) => {
      const info = categories[name] || {};
      const ratio = Math.max(0, Math.min(1, Number(info.count || 0) / categoryMax));
      return '<div class="category-item"><strong>' + escapeHtml(categoryLabels[name] || name) + '</strong><span class="category-meta">' + Number(info.count || 0) + ' 篇</span>' +
        '<span class="micro-bar" aria-hidden="true"><span style="transform:scaleX(' + ratio + ')"></span></span></div>';
    }).join('') : '<div class="inline-empty">暂无分类数据</div>';

    const formats = corpus.format_labels || {};
    const formatKeys = Object.keys(formats);
    $('dashFormats').innerHTML = formatKeys.length ? formatKeys.map((extension) => {
      const info = formats[extension] || {};
      const ratio = Math.max(0, Math.min(1, Number(info.pct || 0) / 100));
      return '<div class="format-row"><strong>' + escapeHtml(info.label || extension) + '</strong><span class="format-meta">' + Number(info.count || 0) + ' · ' + Number(info.pct || 0) + '%</span>' +
        '<span class="micro-bar" aria-hidden="true"><span style="transform:scaleX(' + ratio + ')"></span></span></div>';
    }).join('') : '<div class="inline-empty">暂无格式数据</div>';

    $('dashVStoreDetail').innerHTML =
      '<div class="stat-row"><span>向量集合</span><strong>' + Number(vectorStore.collections || 0) + '</strong></div>' +
      '<div class="stat-row"><span>估算向量块</span><strong>' + Number(vectorStore.estimated_chunks || 0).toLocaleString('zh-CN') + '</strong></div>' +
      '<div class="stat-row"><span>数据库</span><strong>' + fmtSize(Number(vectorStore.sqlite_size_kb || 0) * 1024) + '</strong></div>';

    const recent = reports.recent || [];
    $('dashRecentReports').innerHTML = recent.map((report) => '<tr><td title="' + escapeHtml(report.path) + '">' + escapeHtml(report.path) + '</td><td>' + fmtSize(Number(report.size_kb || 0) * 1024) + '</td><td>' + fmtDate(report.modified) + '</td></tr>').join('');
    $('dashReportsEmpty').hidden = recent.length > 0;
    $('dashLoading').hidden = true;
    $('dashboardContent').hidden = false;
    refreshIcons();
  } catch (error) {
    $('dashLoading').innerHTML = '<div class="empty-state"><i data-lucide="circle-alert" aria-hidden="true"></i><strong>无法加载知识统计</strong><p>' + escapeHtml(error.message) + '</p></div>';
    refreshIcons();
  }
}

function sendQuickQuery() {
  const value = $('quickQueryText').value.trim();
  nav('query');
  if (value) $('queryText').value = value;
  $('queryText').focus();
}

function selectAssistantTab(tabName) {
  const tabs = Array.from(document.querySelectorAll('[data-assistant-tab]'));
  if (!tabs.some((tab) => tab.dataset.assistantTab === tabName)) tabName = 'chat';
  activeAssistantTab = tabName;
  tabs.forEach((tab) => {
    const active = tab.dataset.assistantTab === tabName;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-assistant-panel]').forEach((panel) => {
    const active = panel.dataset.assistantPanel === tabName;
    panel.classList.toggle('active', active);
    panel.hidden = !active;
  });
  if (tabName === 'notes') loadNotes();
  if (tabName === 'memory') Promise.all([loadMemories(), loadSkills()]);
  refreshIcons();
}

function populateAssistantProjects() {
  const select = $('chatProject');
  if (!select) return;
  const previous = select.value;
  select.innerHTML = '<option value="">不指定项目</option>' + (p3ProjectsCache || []).map((project) =>
    '<option value="' + escapeHtml(project.id) + '">' + escapeHtml(project.name || project.id) + '</option>'
  ).join('');
  if ((p3ProjectsCache || []).some((project) => project.id === previous)) select.value = previous;
}

function appendChatMessage(role, text, meta = '') {
  const messages = $('chatMessages');
  const row = document.createElement('div');
  row.className = 'chat-message ' + role;
  row.innerHTML = '<span class="chat-avatar"><i data-lucide="' + (role === 'user' ? 'user' : 'sparkles') + '" aria-hidden="true"></i></span>' +
    '<div><strong>' + (role === 'user' ? '你' : 'Conflux') + '</strong><p></p>' +
    (meta ? '<small>' + escapeHtml(meta) + '</small>' : '') + '</div>';
  row.querySelector('p').textContent = text;
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  refreshIcons();
}

async function sendChatMessage(event) {
  event.preventDefault();
  const message = $('chatMessage').value.trim();
  if (!message) return;
  const button = $('sendChat');
  appendChatMessage('user', message);
  $('chatMessage').value = '';
  enterBusy(button, '助手处理中');
  try {
    const data = await api('/api/chat/messages', {
      message,
      project_id: $('chatProject').value || null,
      depth: 'standard'
    });
    if (data.error) throw new Error(data.error);
    const meta = data.run_id ? '任务 ' + data.run_id : data.requires_approval ? '等待确认 ' + data.approval_id : '';
    appendChatMessage('assistant', data.reply || '操作已处理。', meta);
    await loadApprovals();
  } catch (error) {
    appendChatMessage('assistant', '请求失败：' + error.message);
  } finally {
    leaveBusy(button);
  }
}

async function loadApprovals() {
  try {
    const response = await authFetch('/api/chat/approvals', { cache: 'no-store' });
    const data = await response.json();
    const approvals = data.pending || [];
    $('approvalCount').textContent = String(approvals.length);
    $('assistantApprovalCount').textContent = String(approvals.length);
    $('approvalCount').className = 'status-pill ' + (approvals.length ? 'warn' : 'neutral');
    $('approvalList').innerHTML = approvals.map((item) =>
      '<div class="approval-row" data-approval-id="' + escapeHtml(item.approval_id) + '">' +
      '<div><strong>' + escapeHtml(item.operation) + '</strong><small>' + escapeHtml(JSON.stringify(item.diff || {})) + '</small></div>' +
      '<span class="status-pill ' + (item.risk === 'high' ? 'error' : item.risk === 'medium' ? 'warn' : 'neutral') + '">' + escapeHtml(item.risk) + '</span>' +
      '<div class="approval-actions"><button class="button secondary compact approval-decision" type="button" data-decision="rejected"><i data-lucide="x" aria-hidden="true"></i><span>拒绝</span></button>' +
      '<button class="button primary compact approval-decision" type="button" data-decision="approved"><i data-lucide="check" aria-hidden="true"></i><span>确认</span></button></div></div>'
    ).join('');
    $('approvalEmpty').hidden = approvals.length > 0;
    document.querySelectorAll('.approval-decision').forEach((button) => button.addEventListener('click', () => decideApproval(button)));
    refreshIcons();
  } catch (error) {
    toast('审批列表加载失败：' + error.message, 'err');
  }
}

async function decideApproval(button) {
  const row = button.closest('.approval-row');
  enterBusy(button, '处理中');
  try {
    const data = await api('/api/chat/approvals/' + encodeURIComponent(row.dataset.approvalId), { decision: button.dataset.decision });
    if (!data.ok) throw new Error(data.error || '审批失败');
    toast(button.dataset.decision === 'approved' ? '操作已确认执行' : '操作已拒绝', 'ok');
    await loadApprovals();
    if (selectedProjectId) loadP3Tools();
  } catch (error) {
    toast('审批处理失败：' + error.message, 'err');
    leaveBusy(button);
  }
}

async function loadNotes() {
  try {
    const response = await authFetch('/api/v1/notes?status=active', { cache: 'no-store' });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '笔记加载失败');
    assistantNotes = data.notes || [];
    $('notesSummary').textContent = assistantNotes.length + ' 条 active 笔记';
    $('notesEmpty').hidden = assistantNotes.length > 0;
    $('notesList').innerHTML = assistantNotes.map((note) => {
      const fields = note.fields || {};
      return '<article class="note-row"><div><strong>' + escapeHtml(note.title || note.note_id) + '</strong><small>' + escapeHtml(note.paper_key || '') + ' · ' + escapeHtml(note.note_id || '') + '</small>' +
        '<p>' + escapeHtml(fields['结论'] || fields['目标'] || note.note_text || '未填写摘要') + '</p></div>' +
        '<div class="note-actions"><button class="icon-button subtle note-bibtex" type="button" data-paper-key="' + escapeHtml(note.paper_key || '') + '" aria-label="导出 BibTeX" title="导出 BibTeX"><i data-lucide="quote" aria-hidden="true"></i></button></div></article>';
    }).join('');
    $('noteAuditSelect').innerHTML = '<option value="">选择笔记</option>' + assistantNotes.map((note) => '<option value="' + escapeHtml(note.note_id) + '">' + escapeHtml(note.title || note.note_id) + '</option>').join('');
    document.querySelectorAll('.note-bibtex').forEach((button) => button.addEventListener('click', () => loadBibtex(button.dataset.paperKey)));
    refreshIcons();
  } catch (error) {
    toast('文献笔记加载失败：' + error.message, 'err');
  }
}

async function saveNote(event) {
  event.preventDefault();
  const button = $('saveNote');
  enterBusy(button, '保存笔记');
  const refs = $('notePage').value.trim() || $('noteSegment').value.trim()
    ? [{ page: $('notePage').value.trim(), segment: $('noteSegment').value.trim() }] : [];
  try {
    const data = await api('/api/v1/notes', {
      paper_key: $('notePaperKey').value.trim(),
      title: $('noteTitle').value.trim(),
      note_text: $('noteText').value.trim(),
      fields: {
        '目标': $('noteGoal').value.trim(), '方法': $('noteMethod').value.trim(),
        '结论': $('noteConclusion').value.trim(), '局限': $('noteLimitations').value.trim(),
        '与我的项目关系': $('noteRelevance').value.trim()
      },
      source_refs: refs,
      status: 'active'
    });
    if (!data.ok) throw new Error(data.error || '保存失败');
    $('noteForm').reset();
    toast('文献笔记已保存', 'ok');
    await loadNotes();
  } catch (error) {
    toast('笔记保存失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function runNoteAudit() {
  const note = assistantNotes.find((item) => item.note_id === $('noteAuditSelect').value);
  const source = $('noteAuditSource').value.trim();
  if (!note || !source) {
    toast('请选择笔记并填写原文片段', 'warn');
    return;
  }
  const button = $('runNoteAudit');
  enterBusy(button, '审计中');
  try {
    const data = await api('/api/v1/notes/audit', { note, source });
    $('noteAuditResult').hidden = false;
    $('noteAuditResult').textContent = data.ok
      ? '审计通过 · 检查 ' + data.checked + ' 个字段 · 无支撑比例 ' + Math.round(Number(data.unsupported_ratio || 0) * 100) + '%'
      : '审计未通过 · ' + (data.issues || []).map((item) => item.field + '：' + item.text).join('\n');
  } catch (error) {
    toast('笔记审计失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function loadBibtex(paperKey) {
  try {
    const response = await authFetch('/api/v1/notes/bibtex?paper_key=' + encodeURIComponent(paperKey));
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || 'BibTeX 导出失败');
    $('relatedWorkOutput').hidden = false;
    $('relatedWorkOutput').textContent = data.bibtex;
  } catch (error) {
    toast('BibTeX 导出失败：' + error.message, 'err');
  }
}

async function generateRelatedWork() {
  const button = $('generateRelatedWork');
  enterBusy(button, '生成草稿');
  try {
    const data = await api('/api/v1/notes/related-work', { note_ids: assistantNotes.map((note) => note.note_id) });
    if (!data.ok) throw new Error(data.error || (data.problems || []).join('；') || '生成失败');
    $('relatedWorkOutput').hidden = false;
    $('relatedWorkOutput').textContent = data.draft;
  } catch (error) {
    toast('Related Work 生成失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function loadMemories() {
  try {
    const response = await authFetch('/api/v1/memory', { cache: 'no-store' });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '记忆加载失败');
    const entries = data.entries || [];
    $('memoryCount').textContent = entries.length + ' / ' + (data.capacity || 500);
    $('memoryEmpty').hidden = entries.length > 0;
    $('memoryList').innerHTML = entries.map((entry) =>
      '<div class="memory-row"><span class="p3-kind-tag">' + escapeHtml(entry.kind) + '</span><div><strong>' + escapeHtml(entry.description) + '</strong><small>' + escapeHtml(entry.status) + (entry.project_id ? ' · ' + entry.project_id : '') + '</small></div>' +
      (entry.status === 'pending' ? '<div class="memory-actions"><button class="icon-button subtle memory-decision" type="button" data-id="' + escapeHtml(entry.id) + '" data-decision="reject" aria-label="拒绝记忆" title="拒绝"><i data-lucide="x"></i></button><button class="icon-button subtle memory-decision" type="button" data-id="' + escapeHtml(entry.id) + '" data-decision="confirm" aria-label="确认记忆" title="确认"><i data-lucide="check"></i></button></div>' : '') + '</div>'
    ).join('');
    document.querySelectorAll('.memory-decision').forEach((button) => button.addEventListener('click', () => decideMemory(button)));
    refreshIcons();
  } catch (error) {
    toast('用户记忆加载失败：' + error.message, 'err');
  }
}

async function saveMemory(event) {
  event.preventDefault();
  const button = $('saveMemory');
  enterBusy(button, '保存记忆');
  try {
    const data = await api('/api/v1/memory', {
      kind: $('memoryKind').value,
      description: $('memoryDescription').value.trim(),
      content: { text: $('memoryContent').value.trim() },
      project_id: $('chatProject').value || '',
      status: 'active'
    });
    if (!data.ok) throw new Error(data.error || '保存失败');
    $('memoryForm').reset();
    toast('用户记忆已保存', 'ok');
    await loadMemories();
  } catch (error) {
    toast('记忆保存失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function decideMemory(button) {
  const decision = button.dataset.decision;
  const data = await api('/api/v1/memory/' + encodeURIComponent(button.dataset.id) + '/' + decision, {});
  if (!data.ok) toast(data.error || '记忆处理失败', 'err');
  else await loadMemories();
}

async function loadSkills() {
  try {
    const response = await authFetch('/api/v1/skills', { cache: 'no-store' });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '技能加载失败');
    const skills = data.skills || [];
    $('skillsCount').textContent = String(skills.length);
    $('skillsList').innerHTML = skills.map((skill) =>
      '<div class="skill-row"><i data-lucide="workflow" aria-hidden="true"></i><div><strong>' + escapeHtml(skill.name) + '</strong><p>' + escapeHtml(skill.description || '') + '</p><small>' + escapeHtml((skill.tools || []).join(' · ')) + '</small></div><span class="status-pill ok">v' + escapeHtml(skill.version || '') + '</span></div>'
    ).join('');
    $('skillsProblems').hidden = !(data.problems || []).length;
    $('skillsProblems').textContent = (data.problems || []).join('\n');
    refreshIcons();
  } catch (error) {
    toast('技能库加载失败：' + error.message, 'err');
  }
}

async function loadAssistantData() {
  populateAssistantProjects();
  await loadApprovals();
  if (activeAssistantTab === 'notes') await loadNotes();
  if (activeAssistantTab === 'memory') await Promise.all([loadMemories(), loadSkills()]);
}

function parseJsonField(id) {
  const raw = $(id).value.trim();
  if (!raw) return {};
  const parsed = JSON.parse(raw);
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('JSON 必须是对象');
  return parsed;
}

function renderP3Experiments(experiments) {
  $('p3ExperimentsBody').innerHTML = (experiments || []).map((item) =>
    '<tr><td><strong>' + escapeHtml(item.name || item.id) + '</strong><small class="table-subtext">' + escapeHtml(item.hypothesis || item.id) + '</small></td>' +
    '<td><span class="status-pill ' + (item.status === 'failed' ? 'error' : item.status === 'done' ? 'ok' : item.status === 'running' ? 'warn' : 'neutral') + '">' + escapeHtml(item.status) + '</span></td>' +
    '<td><code>' + escapeHtml(JSON.stringify(item.metrics || {})) + '</code></td><td><code>' + escapeHtml(item.commit_hash || '-') + '</code></td><td>' + escapeHtml(fmtDate(item.updated_at)) + '</td></tr>'
  ).join('');
  $('p3ExperimentsEmpty').hidden = Boolean((experiments || []).length);
  $('p3ExperimentsTable').style.display = (experiments || []).length ? '' : 'none';
}

async function loadP3Tools() {
  if (!selectedProjectId) return;
  try {
    const response = await authFetch('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/experiments', { cache: 'no-store' });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '实验列表加载失败');
    renderP3Experiments(data.experiments || []);
  } catch (error) {
    toast('研究工具加载失败：' + error.message, 'err');
  }
}

async function registerP3Experiment(event) {
  event.preventDefault();
  if (!selectedProjectId) return;
  const button = $('p3RegisterExperiment');
  enterBusy(button, '登记实验');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/experiments', {
      name: $('p3ExperimentName').value.trim(),
      status: $('p3ExperimentStatus').value,
      commit_hash: $('p3ExperimentCommit').value.trim(),
      hypothesis: $('p3ExperimentHypothesis').value.trim(),
      params: parseJsonField('p3ExperimentParams'),
      metrics: parseJsonField('p3ExperimentMetrics')
    });
    if (!data.ok) throw new Error(data.error || '登记失败');
    $('p3ExperimentForm').reset();
    toast('实验已登记并进入项目证据链', 'ok');
    await loadP3Tools();
  } catch (error) {
    toast('实验登记失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function scanP3Experiments() {
  if (!selectedProjectId) return;
  const button = $('p3ScanExperiments');
  enterBusy(button, '扫描结果');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/experiments/scan', {});
    if (!data.ok) throw new Error(data.error || '扫描失败');
    renderP3Experiments(data.experiments || []);
    toast('结果文件扫描完成，新增 ' + (data.registered || []).length + ' 条', 'ok');
  } catch (error) {
    toast('实验结果扫描失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function loadP3MentorReport() {
  if (!selectedProjectId) return;
  const button = $('p3LoadMentor');
  enterBusy(button, '整理周报');
  try {
    const response = await authFetch('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/mentor-report', { cache: 'no-store' });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || '周报数据加载失败');
    $('p3MentorOutput').textContent = data.data_block || '当前周期没有可用数据。';
  } catch (error) {
    toast('周报数据加载失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function confirmP3MentorReport() {
  if (!selectedProjectId) return;
  const button = $('p3ConfirmMentor');
  enterBusy(button, '生成周报');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/mentor-report/confirm', { report: '' });
    if (!data.ok) throw new Error(data.error || (data.failures || []).join('；') || '周报导出失败');
    $('p3MentorOutput').textContent = data.report || '';
    toast('导师周报已校验并导出', 'ok');
  } catch (error) {
    toast('导师周报生成失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function indexP3Code() {
  if (!selectedProjectId) return;
  const button = $('p3IndexCode');
  enterBusy(button, '索引代码');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/code/index', {});
    if (!data.ok) throw new Error(data.error || '代码索引失败');
    toast('代码索引已更新：' + (data.indexed || data.symbols || 0) + ' 个条目', 'ok');
  } catch (error) {
    toast('代码索引失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

async function queryP3Code(event) {
  event.preventDefault();
  if (!selectedProjectId) return;
  const button = $('p3AskCode');
  enterBusy(button, '查询代码');
  try {
    const data = await api('/api/v1/projects/' + encodeURIComponent(selectedProjectId) + '/code/query', { query: $('p3CodeQuestion').value.trim() });
    if (!data.ok) throw new Error(data.error || '代码查询失败');
    $('p3CodeOutput').hidden = false;
    $('p3CodeOutput').textContent = data.answer || ((data.refs || []).join('\n')) || '未找到匹配代码。';
  } catch (error) {
    toast('代码查询失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
  }
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach((button) => button.addEventListener('click', () => nav(button.dataset.target)));
  document.querySelectorAll('[data-nav-target]').forEach((button) => button.addEventListener('click', () => nav(button.dataset.navTarget)));
  document.querySelectorAll('input[name="profileMode"]').forEach((input) => input.addEventListener('change', toggleProfileMode));
  document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => {
    $('quickQueryText').value = button.dataset.prompt;
    $('quickQueryText').focus();
  }));

  $('menuButton').addEventListener('click', () => {
    const open = !$('sidebar').classList.contains('open');
    $('sidebar').classList.toggle('open', open);
    $('sidebarBackdrop').classList.toggle('open', open);
    $('menuButton').setAttribute('aria-expanded', String(open));
  });
  $('sidebarClose').addEventListener('click', closeSidebar);
  $('sidebarBackdrop').addEventListener('click', closeSidebar);
  $('quickQueryBtn').addEventListener('click', sendQuickQuery);
  document.querySelectorAll('[data-assistant-tab]').forEach((button) => button.addEventListener('click', () => selectAssistantTab(button.dataset.assistantTab)));
  $('chatForm').addEventListener('submit', sendChatMessage);
  $('refreshApprovals').addEventListener('click', loadApprovals);
  $('noteForm').addEventListener('submit', saveNote);
  $('runNoteAudit').addEventListener('click', runNoteAudit);
  $('generateRelatedWork').addEventListener('click', generateRelatedWork);
  $('memoryForm').addEventListener('submit', saveMemory);
  $('paperSource').addEventListener('change', updatePaperSourceFields);
  $('projectRegisterPanel').addEventListener('toggle', () => {
    $('projectRegisterForm').hidden = !$('projectRegisterPanel').open;
    if ($('projectRegisterPanel').open) window.setTimeout(() => $('registeredProjectName').focus(), 0);
  });
  $('closeProjectRegister').addEventListener('click', () => {
    $('projectRegisterPanel').open = false;
    $('projectRegisterForm').hidden = true;
  });
  $('saveRegisteredProject').addEventListener('click', saveRegisteredProject);
  $('refreshProjects').addEventListener('click', () => loadProjects({ refresh: true }));
  bindP3Events();
  $('registeredProjectPath').addEventListener('blur', () => {
    if ($('registeredProjectName').value.trim()) return;
    const parts = $('registeredProjectPath').value.trim().replace(/[\\\/]+$/, '').split(/[\\\/]/);
    $('registeredProjectName').value = parts[parts.length - 1] || '';
  });
  $('reportFilter').addEventListener('change', renderReports);
  $('reportSort').addEventListener('change', renderReports);
  $('reportSearch').addEventListener('input', renderReports);
  $('reloadReports').addEventListener('click', () => refreshStatus());
  $('refreshBtn').addEventListener('click', async () => {
    enterBusy($('refreshBtn'), '刷新');
    await Promise.all([refreshStatus(), renderDashboard(), loadProjects()]);
    leaveBusy($('refreshBtn'));
    toast('工作台已刷新', 'ok');
  });
  $('testModel').addEventListener('click', runModelTest);
  $('saveModel').addEventListener('click', saveModel);
  $('webSearchProvider').addEventListener('change', updateWebSearchFields);
  $('serpapiApiKey').addEventListener('input', updateQueryReadiness);
  $('bingApiKey').addEventListener('input', updateQueryReadiness);
  $('googleApiKey').addEventListener('input', updateQueryReadiness);
  $('googleCseId').addEventListener('input', updateQueryReadiness);
  $('runInbox').addEventListener('click', runInbox);
  $('optimizeProfile').addEventListener('click', optimizeProfile);
  $('applyProfileOptimization').addEventListener('click', applyProfileOptimization);
  $('dismissProfileOptimization').addEventListener('click', resetProfileOptimization);
  $('undoProfileOptimization').addEventListener('click', undoProfileOptimization);
  $('saveProfile').addEventListener('click', saveProfile);
  $('runPromote').addEventListener('click', runPromotion);
  $('rebuildVectorIndex').addEventListener('click', rebuildVectorIndex);
  $('runQuery').addEventListener('click', runQuery);
  if ($('cancelQuery')) { $('cancelQuery').addEventListener('click', cancelQuery); }
  MODEL_TIERS.forEach((tier) => {
    $(tierFieldId(tier, 'ApiKey')).addEventListener('input', updateQueryReadiness);
  });
  $('depthSelect').addEventListener('change', updateQueryReadiness);
  $('queryDepth').addEventListener('change', updateQueryReadiness);
  $('embeddingApiKey').addEventListener('input', updateQueryReadiness);
  ['profileFields', 'profileKeywords', 'profileDescription', 'profileNegativeKeywords'].forEach((id) => {
    $(id).addEventListener('input', () => {
      if (profileOptimizationState === 'preview') resetProfileOptimization();
    });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeSidebar();
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      const active = document.querySelector('.view.active');
      if (active && active.id === 'dashboard') sendQuickQuery();
      if (active && active.id === 'query' && !$('runQuery').disabled) runQuery();
    }
  });
}

function bindAuthEvents() {
  $('authForm').addEventListener('submit', login);
  $('authDialog').addEventListener('cancel', (event) => event.preventDefault());
}

async function startWorkbench() {
  if (appStarted) return;
  appStarted = true;
  refreshIcons();
  bindEvents();
  toggleProfileMode();
  updatePaperSourceFields();
  const initialTarget = window.location.hash.slice(1);
  nav($(initialTarget) ? initialTarget : 'dashboard');
  // refreshStatus first: the P3 feature flag gates which project page loads.
  await refreshStatus({ resetDefaults: true });
  await Promise.all([renderDashboard(), loadProjects()]);
}

async function init() {
  refreshIcons();
  bindAuthEvents();
  if (await ensureAuthenticated()) await startWorkbench();
}

init();
