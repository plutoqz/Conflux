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
    button.dataset.previousHtml = button.innerHTML;
    button.innerHTML = '<span class="spin" aria-hidden="true"></span><span>' + escapeHtml(label) + '</span>';
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
    if (button.dataset.previousHtml) button.innerHTML = button.dataset.previousHtml;
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
    const data = await api('/api/profile/optimize', Object.assign({}, source, {
      base_url: $('baseUrl').value.trim(),
      model: $('modelName').value.trim(),
      api_key: $('apiKey').value
    }));
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

function hasReasoningCredential() {
  const credentials = (statusCache && statusCache.credentials) || {};
  return Boolean($('apiKey').value.trim() || credentials.openai_api_key || credentials.reasoning_api_key);
}

function hasEmbeddingCredential() {
  const credentials = (statusCache && statusCache.credentials) || {};
  return Boolean($('embeddingApiKey').value.trim() || $('apiKey').value.trim() || credentials.embedding_api_key || credentials.openai_api_key);
}

function updateQueryReadiness() {
  const state = $('queryReadiness');
  if (!statusCache) return;
  const credentials = statusCache.credentials || {};
  const reasoning = hasReasoningCredential();
  const embedding = hasEmbeddingCredential();
  const search = Boolean(credentials.serpapi_api_key);
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
  return [
    { name: '推理模型', detail: '生成、仲裁与事实核查', ready: Boolean(credentials.openai_api_key || credentials.reasoning_api_key), icon: 'brain-circuit', required: true },
    { name: '向量检索', detail: '检索本地论文和文档', ready: Boolean(credentials.embedding_api_key || credentials.openai_api_key), icon: 'database', required: false },
    { name: '网络搜索', detail: '获取外部最新证据', ready: Boolean(credentials.serpapi_api_key), icon: 'globe-2', required: false },
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
      $('baseUrl').value = (nextStatus.defaults.reasoning || {}).base_url || '';
      $('modelName').value = (nextStatus.defaults.reasoning || {}).model || '';
      $('embeddingBaseUrl').value = (nextStatus.defaults.embedding || {}).base_url || '';
      $('embeddingModel').value = (nextStatus.defaults.embedding || {}).model || '';
      if (nextStatus.saved_depth) $('depthSelect').value = nextStatus.saved_depth;
    }

    renderCapabilities(nextStatus.credentials || {});
    renderReports();
    initialized = true;
  } catch (error) {
    $('busyDot').className = 'busy-dot error';
    $('busyText').textContent = '状态不可用';
    toast('无法读取工作台状态：' + error.message, 'err');
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
    return '<tr><td><span class="reading-badge ' + escapeHtml(level) + '">' + escapeHtml(levelLabel) + '</span></td>' +
      '<td><strong>' + Number(paper.score || 0).toFixed(3) + '</strong></td>' +
      (hasLlm ? '<td>' + Number(paper.keyword_score || 0).toFixed(3) + '</td>' +
        '<td>' + (paper.llm_score != null ? Number(paper.llm_score).toFixed(0) : '-') + '</td>' : '') +
      '<td><strong>' + escapeHtml(paper.title) + '</strong><br><small>' + escapeHtml(paper.id) + '</small>' +
      (paper.llm_reason ? '<br><small>' + escapeHtml(paper.llm_reason) + '</small>' : '') + '</td>' +
      '<td>' + escapeHtml((paper.reasons || []).join('；')) + '</td></tr>';
  }).join('');
  $('papersTable').innerHTML = '<thead><tr><th>建议</th><th>综合分</th>' +
    (hasLlm ? '<th>关键词分</th><th>AI 分</th>' : '') +
    '<th>论文</th><th>匹配依据</th></tr></thead><tbody>' + rows + '</tbody>';
}

const reportIconMap = { '.md': 'file-text', '.html': 'file-code-2', '.json': 'braces', '.jsonl': 'list-tree', '.yaml': 'file-cog', '.yml': 'file-cog', '.csv': 'table-2' };

function allReports() {
  if (!statusCache) return [];
  const merged = (statusCache.reports || []).concat(statusCache.paper_outputs || []);
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
  if (path.toLowerCase().endsWith('.html')) {
    $('preview').hidden = false;
    $('fileText').hidden = true;
    $('preview').src = url;
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

function modelPayload() {
  return {
    base_url: $('baseUrl').value.trim(),
    model: $('modelName').value.trim(),
    api_key: $('apiKey').value,
    prompt: $('probePrompt').value,
    temperature: Number($('temperature').value || 0.2),
    depth: $('depthSelect').value
  };
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
      base_url: $('baseUrl').value,
      api_key: $('apiKey').value,
      model: $('modelName').value,
      embedding_base_url: $('embeddingBaseUrl').value,
      embedding_api_key: $('embeddingApiKey').value,
      embedding_model: $('embeddingModel').value,
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

async function runInbox() {
  const button = $('runInbox');
  const mode = document.querySelector('input[name="profileMode"]:checked').value;
  if (mode === 'file' && !$('profilePath').value) {
    toast('请选择研究画像，或临时创建一个画像', 'warn');
    return;
  }
  enterBusy(button, '发现论文');
  $('inboxOutput').hidden = true;
  $('inboxEmpty').hidden = true;
  try {
    const payload = {
      profile_mode: mode,
      source: $('paperSource').value,
      fixture: $('fixturePath').value,
      out_dir: $('inboxOut').value,
      max_results: Number($('maxResults').value || 10),
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
      const seenText = Number(data.stats.previously_seen || 0) ? ' · 排除重复 ' + Number(data.stats.previously_seen) : '';
      $('inboxStats').textContent = '精读 ' + data.stats.deep + ' · 浏览 ' + data.stats.skim + ' · 跳过 ' + data.stats.skip + seenText;
      $('inboxStats').className = 'status-pill ok';
      $('promoteInbox').value = data.json_path;
      renderPapers(data.papers || []);
      await Promise.all([refreshStatus(), renderDashboard()]);
      toast('论文收件箱已更新，共 ' + (data.papers || []).length + ' 篇', 'ok');
    } else {
      $('inboxOutput').hidden = false;
      $('inboxOutput').textContent = JSON.stringify(data, null, 2);
      toast(data.error || '论文发现失败，请检查数据源和画像', 'err');
    }
  } catch (error) {
    $('inboxOutput').hidden = false;
    $('inboxOutput').textContent = error.message;
    toast('论文发现失败：' + error.message, 'err');
  } finally {
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
  try {
    const data = await api('/api/papers/promote', {
      inbox: $('promoteInbox').value,
      out_dir: $('promoteOut').value,
      pdf_dir: $('pdfDir').value,
      full_text: $('fullText').checked,
      download_pdfs: $('downloadPdfs').checked,
      index: $('indexDocs').checked,
      pin: $('pinIds').value,
      embedding_base_url: $('embeddingBaseUrl').value || $('baseUrl').value,
      embedding_api_key: $('embeddingApiKey').value || $('apiKey').value,
      embedding_model: $('embeddingModel').value
    });
    $('promotionOutput').hidden = false;
    $('promotionOutput').textContent = JSON.stringify(data, null, 2);
    if (data.ok) {
      await Promise.all([refreshStatus(), renderDashboard()]);
      toast('知识库已更新：' + Number(data.documents || 0) + ' 篇文档，' + Number(data.indexed || 0) + ' 条索引', 'ok');
    } else toast(data.error || '知识入库失败', 'err');
  } catch (error) {
    $('promotionOutput').hidden = false;
    $('promotionOutput').textContent = error.message;
    toast('知识入库失败：' + error.message, 'err');
  } finally {
    leaveBusy(button);
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

async function requestQueryCancellation(runId) {
  const response = await authFetch('/api/query/jobs/' + runId + '/cancel', { method: 'POST' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 409) {
    throw new Error(data.error || '取消请求失败');
  }
  return data;
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
  $('queryEmpty').hidden = true;
  $('queryStage').textContent = '提交研究任务...';
  $('queryStage').className = 'status-pill warn';

  let runId = '';
  try {
    const submitRes = await authFetch('/api/query/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign(modelPayload(), {
        query,
        output_dir: $('queryOut').value,
        embedding_base_url: $('embeddingBaseUrl').value,
        embedding_api_key: $('embeddingApiKey').value,
        embedding_model: $('embeddingModel').value,
        depth: $('queryDepth').value || $('depthSelect').value
      }))
    });
    const submitData = await submitRes.json();
    if (!submitRes.ok) {
      throw new Error(submitData.error || '提交失败（HTTP ' + submitRes.status + '）');
    }
    runId = submitData.run_id;
    $('queryResultBand').dataset.activeRun = runId;
    activeQuery = { runId, cancelRequested: false, timedOut: false };
    // Keep button busy — re-enabled when job completes
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
    const timingOut = activeQuery && activeQuery.runId === runId && (activeQuery.timedOut || activeQuery.cancelRequested);
    $('queryStage').textContent = timingOut ? '取消处理中 · ' + elapsed + ' 秒' : '已运行 ' + elapsed + ' 秒';
  }, 1000);

  const nodeStates = {};
  const updateNodeDisplay = () => {
    const order = ['rag_agent', 'web_agent', 'model_agent', 'evidence_merge', 'arbitration', 'synthesize', 'factcheck', 'deep_research'];
    const labels = { rag_agent:'RAG 检索', web_agent:'Web 搜索', model_agent:'模型推理', evidence_merge:'证据合并', arbitration:'三源仲裁', synthesize:'报告合成', factcheck:'事实核查', deep_research:'深化研究' };
    const lines = order.filter(function(k){ return nodeStates[k]; }).map(function(k){ return (nodeStates[k]==='completed'?'\u2705':nodeStates[k]==='failed'?'\u274c':'\u23f3') + ' ' + labels[k]; });
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
        updateNodeDisplay();
        $('queryStage').textContent = (evt.stage || '').replace(/_/g, ' ') + ' · ' + Math.round((Date.now() - started) / 1000) + ' 秒';
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
      if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        window.clearInterval(pollInterval);
        window.clearInterval(elapsedTimer);
        window.clearTimeout(queryTimeout);
        es.close();
        finalResult = job;
        $('queryOutput').hidden = false;
        if (job.status === 'completed') {
          $('queryStage').textContent = '完成 · ' + Math.round((Date.now() - started) / 1000) + ' 秒';
          $('queryStage').className = 'status-pill ok';
          var out = '=== 最终答案 ===\n' + (job.final_answer || '') + '\n\n';
          if (job.final_answer_truncated) {
            out += '\u26a0\ufe0f 答案已截断（显示前 4000 / ' + job.final_answer_total_length + ' 字符），完整内容请搜索对应 .md 报告。\n';
          }
          out += '\n=== 来源状态 ===\n' + JSON.stringify(job.source_statuses || {}, null, 2) + '\n';
          if (job.factcheck_status) out += '\nFactCheck: ' + job.factcheck_status;
          $('queryOutput').textContent = out;
          toast('研究任务已完成', 'ok');
        } else {
          $('queryStage').textContent = job.status === 'failed' ? '执行失败' : '已取消';
          $('queryStage').className = 'status-pill error';
          $('queryOutput').textContent = job.error || JSON.stringify(job, null, 2);
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

  const queryTimeout = window.setTimeout(async function() {
    if (finalResult || !activeQuery || activeQuery.runId !== runId) return;
    const queryContext = activeQuery;
    queryContext.timedOut = true;
    $('queryStage').textContent = '已超时 · 正在请求取消';
    $('queryStage').className = 'status-pill warn';
    markCancelRequested('正在取消');
    try {
      const data = await requestQueryCancellation(runId);
      if (activeQuery !== queryContext) return;
      queryContext.cancelRequested = Boolean(data.cancel_requested);
      toast(data.cancel_requested ? '任务运行超过 5 分钟，已请求安全取消' : '任务已结束，正在读取最终状态', 'warn');
    } catch (error) {
      if (activeQuery !== queryContext) return;
      queryContext.cancelRequested = false;
      const cancelButton = $('cancelQuery');
      cancelButton.disabled = false;
      if (cancelButton.dataset.previousHtml) cancelButton.innerHTML = cancelButton.dataset.previousHtml;
      toast('自动取消失败：' + error.message, 'err');
      refreshIcons();
    }
  }, 300000);

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
  $('paperSource').addEventListener('change', updatePaperSourceFields);
  $('reportFilter').addEventListener('change', renderReports);
  $('reportSort').addEventListener('change', renderReports);
  $('reportSearch').addEventListener('input', renderReports);
  $('reloadReports').addEventListener('click', () => refreshStatus());
  $('refreshBtn').addEventListener('click', async () => {
    enterBusy($('refreshBtn'), '刷新');
    await Promise.all([refreshStatus(), renderDashboard()]);
    leaveBusy($('refreshBtn'));
    toast('工作台已刷新', 'ok');
  });
  $('testModel').addEventListener('click', runModelTest);
  $('saveModel').addEventListener('click', saveModel);
  $('runInbox').addEventListener('click', runInbox);
  $('optimizeProfile').addEventListener('click', optimizeProfile);
  $('applyProfileOptimization').addEventListener('click', applyProfileOptimization);
  $('dismissProfileOptimization').addEventListener('click', resetProfileOptimization);
  $('undoProfileOptimization').addEventListener('click', undoProfileOptimization);
  $('saveProfile').addEventListener('click', saveProfile);
  $('runPromote').addEventListener('click', runPromotion);
  $('runQuery').addEventListener('click', runQuery);
  if ($('cancelQuery')) { $('cancelQuery').addEventListener('click', cancelQuery); }
  $('apiKey').addEventListener('input', updateQueryReadiness);
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
  await Promise.all([refreshStatus({ resetDefaults: true }), renderDashboard()]);
}

async function init() {
  refreshIcons();
  bindAuthEvents();
  if (await ensureAuthenticated()) await startWorkbench();
}

init();
