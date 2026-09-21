/**
 * Legal Contract Analyzer - ChatGPT Dark Theme Controller
 */

const state = {
  contracts: [],
  activeContract: null,
  activeClauses: [],
  selectedClause: null,
  activeCategoryFilter: 'ALL',
  searchQuery: '',
  systemConfig: null,
  currentView: 'chat',
  activeRagVersion: 'v1',
  chatHistory: []
};

// DOM References
const elements = {
  sidebar: document.getElementById('sidebar'),
  btnToggleSidebar: document.getElementById('btnToggleSidebar'),
  btnOpenSidebarMobile: document.getElementById('btnOpenSidebarMobile'),
  btnNewChat: document.getElementById('btnNewChat'),
  sidebarNavItems: document.querySelectorAll('.sidebar-nav-item'),
  sidebarContractsList: document.getElementById('sidebarContractsList'),
  btnSidebarLoadSamples: document.getElementById('btnSidebarLoadSamples'),
  btnSidebarUpload: document.getElementById('btnSidebarUpload'),
  btnSidebarSettings: document.getElementById('btnSidebarSettings'),

  // Header
  activeContractPill: document.getElementById('activeContractPill'),
  activeContractLabel: document.getElementById('activeContractLabel'),
  btnQuickUpload: document.getElementById('btnQuickUpload'),

  // Views
  viewPanels: document.querySelectorAll('.view-panel'),
  chatHeroLanding: document.getElementById('chatHeroLanding'),
  conversationFeed: document.getElementById('conversationFeed'),
  chatScrollArea: document.getElementById('chatScrollArea'),

  // Floating Input
  chatForm: document.getElementById('chatForm'),
  chatInput: document.getElementById('chatInput'),
  btnSendChat: document.getElementById('btnSendChat'),
  btnAttachFile: document.getElementById('btnAttachFile'),
  suggestionChips: document.querySelectorAll('.suggestion-chip'),

  // Clause Explorer
  clauseSearchInput: document.getElementById('clauseSearchInput'),
  categoryFilters: document.getElementById('categoryFilters'),
  clauseListContainer: document.getElementById('clauseListContainer'),
  clauseDetailPanel: document.getElementById('clauseDetailPanel'),

  // Risk Scanner
  btnTriggerRiskScan: document.getElementById('btnTriggerRiskScan'),
  riskScoreVal: document.getElementById('riskScoreVal'),
  riskScoreLabel: document.getElementById('riskScoreLabel'),
  highRiskCount: document.getElementById('highRiskCount'),
  medRiskCount: document.getElementById('medRiskCount'),
  totalClausesCount: document.getElementById('totalClausesCount'),
  riskExecutiveSummaryCard: document.getElementById('riskExecutiveSummaryCard'),
  riskExecutiveSummaryText: document.getElementById('riskExecutiveSummaryText'),
  flaggedClausesList: document.getElementById('flaggedClausesList'),

  // Compare
  compareContractA: document.getElementById('compareContractA'),
  compareContractB: document.getElementById('compareContractB'),
  btnRunComparison: document.getElementById('btnRunComparison'),
  compareSummaryCard: document.getElementById('compareSummaryCard'),
  compareSummaryText: document.getElementById('compareSummaryText'),
  compareResultsGrid: document.getElementById('compareResultsGrid'),

  // Modals
  uploadModal: document.getElementById('uploadModal'),
  btnCloseUploadModal: document.getElementById('btnCloseUploadModal'),
  btnCancelUpload: document.getElementById('btnCancelUpload'),
  btnTriggerUpload: document.getElementById('btnTriggerUpload'),
  dropZone: document.getElementById('dropZone'),
  pdfFileInput: document.getElementById('pdfFileInput'),
  uploadProgressContainer: document.getElementById('uploadProgressContainer'),
  uploadProgressBar: document.getElementById('uploadProgressBar'),
  uploadProgressLabel: document.getElementById('uploadProgressLabel'),

  settingsModal: document.getElementById('settingsModal'),
  btnCloseSettingsModal: document.getElementById('btnCloseSettingsModal'),
  btnCloseSettings: document.getElementById('btnCloseSettings'),
  inputApiKey: document.getElementById('inputApiKey'),
  btnToggleKeyVisibility: document.getElementById('btnToggleKeyVisibility'),
  btnSaveApiKey: document.getElementById('btnSaveApiKey'),
  configStatusLabel: document.getElementById('configStatusLabel'),

  // Toast
  toast: document.getElementById('toastNotification'),
  toastIcon: document.getElementById('toastIcon'),
  toastMsg: document.getElementById('toastMsg')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchSystemConfig();
  fetchContracts();
});

function setupEventListeners() {
  // Sidebar Toggle
  elements.btnToggleSidebar.addEventListener('click', () => {
    elements.sidebar.classList.toggle('collapsed');
  });
  if (elements.btnOpenSidebarMobile) {
    elements.btnOpenSidebarMobile.addEventListener('click', () => {
      elements.sidebar.classList.toggle('collapsed');
    });
  }

  // New Chat
  elements.btnNewChat.addEventListener('click', resetChatSession);

  // Navigation Items
  elements.sidebarNavItems.forEach(item => {
    item.addEventListener('click', () => {
      const view = item.getAttribute('data-view');
      switchView(view);
    });
  });

  // Load Samples
  elements.btnSidebarLoadSamples.addEventListener('click', handleLoadSamples);

  // Floating Input Chat
  elements.chatInput.addEventListener('input', () => {
    elements.chatInput.style.height = 'auto';
    elements.chatInput.style.height = Math.min(elements.chatInput.scrollHeight, 160) + 'px';
    const hasText = elements.chatInput.value.trim().length > 0;
    elements.btnSendChat.disabled = !hasText;
  });

  elements.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!elements.btnSendChat.disabled) {
        handleSendChat();
      }
    }
  });

  elements.chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!elements.btnSendChat.disabled) {
      handleSendChat();
    }
  });

  // Suggestion Chips
  elements.suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      elements.chatInput.value = query;
      elements.btnSendChat.disabled = false;
      handleSendChat();
    });
  });

  // Clause Search
  elements.clauseSearchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.toLowerCase();
    renderClauseList();
  });

  // Risk Scan
  elements.btnTriggerRiskScan.addEventListener('click', handleRunRiskScan);

  // Compare
  elements.btnRunComparison.addEventListener('click', handleRunComparison);

  // Upload modal triggers
  elements.btnAttachFile.addEventListener('click', () => openModal(elements.uploadModal));
  elements.btnQuickUpload.addEventListener('click', () => openModal(elements.uploadModal));
  elements.btnSidebarUpload.addEventListener('click', () => openModal(elements.uploadModal));
  elements.btnCloseUploadModal.addEventListener('click', () => closeModal(elements.uploadModal));
  elements.btnCancelUpload.addEventListener('click', () => closeModal(elements.uploadModal));
  elements.dropZone.addEventListener('click', () => elements.pdfFileInput.click());

  elements.dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.dropZone.classList.add('dragover');
  });
  elements.dropZone.addEventListener('dragleave', () => elements.dropZone.classList.remove('dragover'));
  elements.dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      elements.pdfFileInput.files = e.dataTransfer.files;
      onFileSelected();
    }
  });
  elements.pdfFileInput.addEventListener('change', onFileSelected);
  elements.btnTriggerUpload.addEventListener('click', handleUploadFile);

  // Settings
  elements.btnSidebarSettings.addEventListener('click', () => openModal(elements.settingsModal));
  elements.btnCloseSettingsModal.addEventListener('click', () => closeModal(elements.settingsModal));
  elements.btnCloseSettings.addEventListener('click', () => closeModal(elements.settingsModal));
  elements.btnSaveApiKey.addEventListener('click', handleSaveApiKey);
  elements.btnToggleKeyVisibility.addEventListener('click', () => {
    elements.inputApiKey.type = elements.inputApiKey.type === 'password' ? 'text' : 'password';
  });

  // RAG Pipeline Architecture Chips
  document.querySelectorAll('.pipeline-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.pipeline-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.activeRagVersion = chip.getAttribute('data-v') || 'v1';
      showToast(`Active Architecture: ${chip.textContent}`, '⚡');
    });
  });

  // Benchmark reload button
  const btnRefreshBench = document.getElementById('btnRefreshBenchmark');
  if (btnRefreshBench) {
    btnRefreshBench.addEventListener('click', loadBenchmarkResults);
  }
}

function switchView(viewName) {
  state.currentView = viewName;
  elements.sidebarNavItems.forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-view') === viewName);
  });
  elements.viewPanels.forEach(p => {
    p.classList.toggle('active', p.id === `view-${viewName}`);
  });

  if (viewName === 'clauses' && state.activeClauses.length === 0 && state.activeContract) {
    loadActiveContractClauses();
  }
  if (viewName === 'benchmark') {
    loadBenchmarkResults();
  }
}

function resetChatSession() {
  state.chatHistory = [];
  elements.conversationFeed.innerHTML = '';
  elements.chatHeroLanding.style.display = 'flex';
  elements.chatInput.value = '';
  elements.btnSendChat.disabled = true;
  switchView('chat');
}

// Config & Contracts API
async function fetchSystemConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    state.systemConfig = data;
    elements.configStatusLabel.textContent = data.has_gemini_key ? 'Active (Gemini 3.7 Flash)' : 'Demo Heuristic Mode';
  } catch (err) {
    console.warn(err);
  }
}

async function handleSaveApiKey() {
  const key = elements.inputApiKey.value.trim();
  if (!key) return;
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gemini_api_key: key })
    });
    const data = await res.json();
    showToast('Gemini API Key updated successfully!', '✅');
    closeModal(elements.settingsModal);
    fetchSystemConfig();
  } catch (err) {
    showToast('Error saving key: ' + err.message, '❌');
  }
}

async function fetchContracts() {
  try {
    const res = await fetch('/api/contracts');
    const data = await res.json();
    state.contracts = data.contracts || [];

    renderSidebarContracts();
    updateCompareDropdowns();

    if (state.contracts.length > 0) {
      if (!state.activeContract || !state.contracts.some(c => c.name === state.activeContract)) {
        setActiveContract(state.contracts[0].name);
      }
    } else {
      elements.activeContractLabel.textContent = 'No contracts loaded';
    }
  } catch (err) {
    console.error('Contracts error:', err);
  }
}

function renderSidebarContracts() {
  if (state.contracts.length === 0) {
    elements.sidebarContractsList.innerHTML = `
      <div style="padding: 10px; font-size: 12px; color: var(--text-muted);">
        No contracts indexed. Click "Load Samples" or "Upload PDF".
      </div>
    `;
    return;
  }

  elements.sidebarContractsList.innerHTML = state.contracts.map(c => `
    <div class="sidebar-contract-item ${c.name === state.activeContract ? 'active' : ''}" data-name="${escapeHtml(c.name)}">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      </svg>
      <span>${escapeHtml(c.name)}</span>
    </div>
  `).join('');

  elements.sidebarContractsList.querySelectorAll('.sidebar-contract-item').forEach(item => {
    item.addEventListener('click', () => {
      const name = item.getAttribute('data-name');
      setActiveContract(name);
    });
  });
}

function updateCompareDropdowns() {
  const options = state.contracts.map(c => `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>`).join('');
  elements.compareContractA.innerHTML = options;
  elements.compareContractB.innerHTML = options;

  if (state.contracts.length > 1) {
    elements.compareContractA.selectedIndex = 0;
    elements.compareContractB.selectedIndex = 1;
  }
}

function setActiveContract(name) {
  state.activeContract = name;
  elements.activeContractLabel.textContent = name;
  renderSidebarContracts();
  loadActiveContractClauses();
  resetRiskTab();
}

async function loadActiveContractClauses() {
  if (!state.activeContract) return;
  try {
    const res = await fetch(`/api/contracts/${encodeURIComponent(state.activeContract)}/clauses`);
    const data = await res.json();
    state.activeClauses = data.clauses || [];
    renderCategoryFilters();
    renderClauseList();
  } catch (err) {
    console.error('Error fetching clauses:', err);
  }
}

// Chat Flow
async function handleSendChat() {
  const question = elements.chatInput.value.trim();
  if (!question) return;

  if (!state.activeContract) {
    showToast('Please select or upload a contract first.', '⚠️');
    return;
  }

  // Hide hero landing
  elements.chatHeroLanding.style.display = 'none';

  // Add User turn
  appendUserMessage(question);
  elements.chatInput.value = '';
  elements.chatInput.style.height = 'auto';
  elements.btnSendChat.disabled = true;

  // Add Assistant turn placeholder
  const assistantBubble = appendAssistantLoading();

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        contract_name: state.activeContract,
        version: state.activeRagVersion
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Analysis failed');
    }

    const data = await res.json();
    updateAssistantMessage(assistantBubble, data);
  } catch (err) {
    assistantBubble.querySelector('.chat-assistant-content').innerHTML = `
      <p style="color: var(--accent-red);">Error analyzing query: ${err.message}</p>
    `;
  }
}

function appendUserMessage(text) {
  const turn = document.createElement('div');
  turn.className = 'chat-turn';
  turn.innerHTML = `
    <div class="chat-user-row">
      <div class="chat-user-bubble">${escapeHtml(text)}</div>
    </div>
  `;
  elements.conversationFeed.appendChild(turn);
  scrollToBottom();
}

function appendAssistantLoading() {
  const turn = document.createElement('div');
  turn.className = 'chat-turn';
  turn.innerHTML = `
    <div class="chat-assistant-row">
      <div class="assistant-avatar-icon">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="chat-assistant-content">
        <p style="color: var(--text-muted);"><em>Searching clauses in ChromaDB & analyzing with Gemini 3.7 Flash...</em></p>
      </div>
    </div>
  `;
  elements.conversationFeed.appendChild(turn);
  scrollToBottom();
  return turn;
}

function updateAssistantMessage(turnElement, data) {
  const markdown = data.answer || '';
  const clauses = data.clauses_referenced || [];
  const version = (data.version || 'v1').toUpperCase();
  const retrieval = data.retrieval || {};
  const system = data.system || {};
  const trace = data.agent_trace || null;
  const verification = data.verification || null;

  const html = renderMarkdown(markdown);

  // Citations
  let citationsHtml = '';
  if (clauses && clauses.length > 0) {
    citationsHtml = `
      <div class="citation-chips-box">
        <span style="font-size: 11px; color: var(--text-muted); font-weight: 600;">CITATIONS:</span>
        ${clauses.map(c => `<span class="citation-pill">📑 ${escapeHtml(c)}</span>`).join('')}
      </div>
    `;
  }

  // Verification Badge
  let verifHtml = '';
  if (verification) {
    const isV = verification.is_verified;
    const prec = Math.round((verification.citation_precision || 1.0) * 100);
    verifHtml = `
      <span class="status-badge ${isV ? 'badge-low' : 'badge-high'}" style="font-size: 11px;">
        ${isV ? '✅ Citations Grounded' : '⚠️ Unverified Citation'} (${prec}%)
      </span>
    `;
  }

  // Retrieval & Trace Inspector Box
  const retResults = retrieval.results || [];
  const latencyMs = system.total_latency ? Math.round(system.total_latency * 1000) : (retrieval.retrieval_latency ? Math.round(retrieval.retrieval_latency * 1000) : null);

  let inspectorHtml = `
    <div class="retrieval-metadata-box">
      <div class="retrieval-meta-header" onclick="this.nextElementSibling.classList.toggle('hidden');">
        <div class="retrieval-meta-tags">
          <span class="retrieval-method-tag">${escapeHtml(version)} • ${escapeHtml(retrieval.method || 'retrieval')}</span>
          ${verifHtml}
        </div>
        <div style="color: var(--text-muted); font-size: 11px; font-family: var(--font-mono);">
          ${latencyMs ? `${latencyMs}ms` : ''} ▾
        </div>
      </div>
      <div class="retrieval-meta-body">
  `;

  if (trace && trace.tool_calls && trace.tool_calls.length > 0) {
    inspectorHtml += `
      <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Agent Tool Trace (${trace.total_steps} steps):</div>
      <div class="agent-steps-timeline">
        ${trace.tool_calls.map(tc => `
          <div class="agent-step-item">
            <span class="agent-step-num">${tc.step}</span>
            <span style="font-family: var(--font-mono); color: var(--accent-blue);">${escapeHtml(tc.tool_name)}</span>
            <span style="color: var(--text-muted);">(${escapeHtml(tc.output_summary)})</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  if (retResults.length > 0) {
    inspectorHtml += `
      <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-top: 6px;">Retrieved Evidence (${retResults.length} clauses):</div>
      ${retResults.slice(0, 4).map(r => `
        <div class="evidence-clause-pill">
          <div style="font-weight: 600; color: #FFFFFF;">Clause ${r.clause_number || '?'}: ${escapeHtml(r.title || '')}</div>
          <div class="evidence-scores-row">
            <span>Score: ${r.retrieval_score != null ? r.retrieval_score.toFixed(3) : '--'}</span>
            ${r.rerank_score != null ? `<span style="color: var(--accent-green);">Rerank: ${r.rerank_score.toFixed(3)}</span>` : ''}
            <span>Page: ~${r.page || 1}</span>
          </div>
        </div>
      `).join('')}
    `;
  }

  inspectorHtml += `
      </div>
    </div>
  `;

  turnElement.querySelector('.chat-assistant-content').innerHTML = `
    <div class="markdown-body">${html}</div>
    ${citationsHtml}
    ${inspectorHtml}
  `;
  scrollToBottom();
}

async function loadBenchmarkResults() {
  const wrapper = document.getElementById('benchmarkTableWrapper');
  const badge = document.getElementById('benchmarkStatusBadge');
  if (!wrapper) return;

  wrapper.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted);">Fetching evaluation data...</div>';

  try {
    const res = await fetch('/api/benchmark/results');
    const data = await res.json();

    if (!data.has_results || !data.summary) {
      if (badge) {
        badge.className = 'status-badge badge-neutral';
        badge.textContent = 'Not Evaluated';
      }
      wrapper.innerHTML = `
        <div style="padding: 30px; text-align: center; color: var(--text-muted);">
          <p style="margin-bottom: 8px; font-size: 14px;"><strong>No evaluation run recorded yet.</strong></p>
          <p style="font-size: 12px;">Run the benchmark runner script to evaluate all 5 systems on the synthetic dataset:</p>
          <code style="background: var(--bg-main); padding: 6px 12px; border-radius: 4px; display: inline-block; margin-top: 10px; font-family: var(--font-mono);">
            python scripts/run_evaluation.py
          </code>
        </div>
      `;
      return;
    }

    if (badge) {
      badge.className = 'status-badge badge-low';
      badge.textContent = `Evaluated (${data.timestamp || 'Recent'})`;
    }

    const summary = data.summary;
    let tableRows = '';

    for (const [sysName, m] of Object.entries(summary)) {
      tableRows += `
        <tr>
          <td class="sys-name">${escapeHtml(sysName)}</td>
          <td>${m.recall_at_4 != null ? m.recall_at_4.toFixed(4) : '--'}</td>
          <td>${m.recall_at_8 != null ? m.recall_at_8.toFixed(4) : '--'}</td>
          <td>${m.precision_at_4 != null ? m.precision_at_4.toFixed(4) : '--'}</td>
          <td>${m.mrr != null ? m.mrr.toFixed(4) : '--'}</td>
          <td>${m.ndcg_at_4 != null ? m.ndcg_at_4.toFixed(4) : '--'}</td>
          <td>${m.avg_latency_ms != null ? m.avg_latency_ms.toFixed(1) : '--'} ms</td>
          <td>${m.avg_tool_calls != null ? m.avg_tool_calls.toFixed(1) : '0.0'}</td>
        </tr>
      `;
    }

    wrapper.innerHTML = `
      <table class="benchmark-table">
        <thead>
          <tr>
            <th>Architecture</th>
            <th>Recall@4</th>
            <th>Recall@8</th>
            <th>Precision@4</th>
            <th>MRR</th>
            <th>nDCG@4</th>
            <th>Latency (ms)</th>
            <th>Avg Tool Calls</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
    `;
  } catch (err) {
    wrapper.innerHTML = `<div style="padding: 20px; color: var(--accent-red);">Error loading benchmark results: ${err.message}</div>`;
  }
}

function scrollToBottom() {
  elements.chatScrollArea.scrollTop = elements.chatScrollArea.scrollHeight;
}

// Clause Explorer
function renderCategoryFilters() {
  const categories = ['ALL', ...new Set(state.activeClauses.map(c => c.category))];
  elements.categoryFilters.innerHTML = categories.map(cat => `
    <button class="filter-chip ${cat === state.activeCategoryFilter ? 'active' : ''}" data-cat="${cat}">
      ${cat}
    </button>
  `).join('');

  elements.categoryFilters.querySelectorAll('.filter-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      state.activeCategoryFilter = btn.getAttribute('data-cat');
      renderCategoryFilters();
      renderClauseList();
    });
  });
}

function renderClauseList() {
  const filtered = state.activeClauses.filter(c => {
    const matchesCat = state.activeCategoryFilter === 'ALL' || c.category === state.activeCategoryFilter;
    const matchesQuery = !state.searchQuery ||
      c.title.toLowerCase().includes(state.searchQuery) ||
      c.text.toLowerCase().includes(state.searchQuery);
    return matchesCat && matchesQuery;
  });

  if (filtered.length === 0) {
    elements.clauseListContainer.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">
        No clauses match your filter.
      </div>
    `;
    return;
  }

  elements.clauseListContainer.innerHTML = filtered.map(c => `
    <div class="clause-card-item ${state.selectedClause && state.selectedClause.clause_number === c.clause_number ? 'selected' : ''}" data-num="${c.clause_number}">
      <div class="clause-card-header">
        <span>Clause ${c.clause_number}</span>
        <span>${escapeHtml(c.category)}</span>
      </div>
      <div class="clause-card-title">${escapeHtml(c.title)}</div>
      <div class="clause-card-snippet">${escapeHtml(c.text)}</div>
    </div>
  `).join('');

  elements.clauseListContainer.querySelectorAll('.clause-card-item').forEach(card => {
    card.addEventListener('click', () => {
      const num = parseInt(card.getAttribute('data-num'), 10);
      const clause = state.activeClauses.find(x => x.clause_number === num);
      if (clause) selectClause(clause);
    });
  });
}

async function selectClause(clause) {
  state.selectedClause = clause;
  renderClauseList();

  elements.clauseDetailPanel.innerHTML = `
    <div style="margin-bottom: 14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
        <span style="font-size: 12px; color: var(--accent-blue); font-family: var(--font-mono);">Clause ${clause.clause_number} (Page ~${clause.page})</span>
        <span class="status-badge badge-neutral">${clause.category}</span>
      </div>
      <h3 style="font-size: 16px; font-weight: 600; color: #FFFFFF;">${escapeHtml(clause.title)}</h3>
    </div>

    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600; margin-bottom: 6px;">Plain English Translation</div>
    <div id="clauseExplanationWrap" style="background: rgba(16, 163, 127, 0.08); border: 1px solid rgba(16, 163, 127, 0.25); border-radius: var(--radius-md); padding: 14px; margin-bottom: 16px; font-size: 13px;">
      <span style="color: var(--text-secondary);">Translating clause into plain English...</span>
    </div>

    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600; margin-bottom: 6px;">Original Legal Text</div>
    <div style="background: var(--bg-main); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap;">${escapeHtml(clause.text)}</div>
  `;

  try {
    const res = await fetch('/api/contracts/explain-clause', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contract_name: state.activeContract,
        clause_number: clause.clause_number,
        clause_text: clause.text
      })
    });
    const data = await res.json();
    const wrap = document.getElementById('clauseExplanationWrap');
    if (wrap) {
      wrap.innerHTML = `
        <div class="markdown-body">${renderMarkdown(data.explanation)}</div>
        <div style="margin-top: 10px; display: flex; align-items: center; gap: 8px;">
          <span class="status-badge badge-${data.severity.toLowerCase()}">${data.severity} RISK</span>
          ${data.flags && data.flags.length ? `<span style="font-size: 12px; color: var(--accent-red);">⚠️ ${escapeHtml(data.flags[0])}</span>` : ''}
        </div>
      `;
    }
  } catch (err) {
    console.error(err);
  }
}

// Risk Scanner
function resetRiskTab() {
  elements.riskScoreVal.textContent = '--';
  elements.riskScoreLabel.textContent = 'Awaiting scan';
  elements.riskScoreLabel.className = 'status-badge badge-neutral';
  elements.highRiskCount.textContent = '0';
  elements.medRiskCount.textContent = '0';
  elements.totalClausesCount.textContent = state.activeClauses.length.toString();
  elements.riskExecutiveSummaryCard.style.display = 'none';
  elements.flaggedClausesList.innerHTML = '';
}

async function handleRunRiskScan() {
  if (!state.activeContract) {
    showToast('Select a contract first.', '⚠️');
    return;
  }

  elements.btnTriggerRiskScan.disabled = true;
  elements.btnTriggerRiskScan.innerHTML = 'Scanning contract...';

  try {
    const res = await fetch('/api/scan-risks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contract_name: state.activeContract })
    });

    const data = await res.json();
    elements.riskScoreVal.textContent = data.risk_score;
    elements.highRiskCount.textContent = data.high_count;
    elements.medRiskCount.textContent = data.medium_count;
    elements.totalClausesCount.textContent = data.total_clauses;

    if (data.risk_score > 60) {
      elements.riskScoreLabel.className = 'status-badge badge-high';
      elements.riskScoreLabel.textContent = 'High Contract Risk';
    } else if (data.risk_score > 30) {
      elements.riskScoreLabel.className = 'status-badge badge-med';
      elements.riskScoreLabel.textContent = 'Moderate Commercial Risk';
    } else {
      elements.riskScoreLabel.className = 'status-badge badge-low';
      elements.riskScoreLabel.textContent = 'Standard / Balanced';
    }

    elements.riskExecutiveSummaryCard.style.display = 'block';
    elements.riskExecutiveSummaryText.innerHTML = renderMarkdown(data.summary);

    if (data.flagged_clauses && data.flagged_clauses.length > 0) {
      elements.flaggedClausesList.innerHTML = data.flagged_clauses.map(item => `
        <div class="flagged-item severity-${item.severity}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; color:var(--accent-blue); font-family:var(--font-mono);">Clause ${item.clause_number}</span>
            <span class="status-badge badge-${item.severity.toLowerCase()}">${item.severity}</span>
          </div>
          <div style="font-size:14px; font-weight:600; color:#FFFFFF;">${escapeHtml(item.title)}</div>
          <div style="font-size:12px; color:var(--accent-red); background:rgba(248,113,113,0.08); padding:8px 10px; border-radius:var(--radius-sm);">
            ${item.concerns.map(c => `• ${escapeHtml(c)}`).join('<br>')}
          </div>
          <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono); max-height:60px; overflow:hidden;">
            "${escapeHtml(item.text)}"
          </div>
        </div>
      `).join('');
    }
    showToast('Risk audit completed!', '🛡️');
  } catch (err) {
    showToast('Risk scan error: ' + err.message, '❌');
  } finally {
    elements.btnTriggerRiskScan.disabled = false;
    elements.btnTriggerRiskScan.innerHTML = 'Scan Contract Now';
  }
}

// Compare
async function handleRunComparison() {
  const contractA = elements.compareContractA.value;
  const contractB = elements.compareContractB.value;

  if (!contractA || !contractB || contractA === contractB) {
    showToast('Select two different contracts.', '⚠️');
    return;
  }

  elements.btnRunComparison.disabled = true;
  elements.btnRunComparison.innerHTML = 'Comparing...';

  try {
    const res = await fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contract_a: contractA, contract_b: contractB })
    });

    const data = await res.json();
    elements.compareSummaryCard.style.display = 'block';
    elements.compareSummaryText.innerHTML = renderMarkdown(data.executive_comparison);

    elements.compareResultsGrid.innerHTML = data.comparisons.map(comp => `
      <div class="comp-card">
        <div class="comp-header">
          <span style="font-weight:600; color:var(--accent-blue); font-size:14px;">${escapeHtml(comp.category)}</span>
          <span class="status-badge badge-neutral">${escapeHtml(comp.verdict)}</span>
        </div>
        <div class="comp-panes">
          <div class="comp-pane">
            <div style="font-weight:600; color:#FFFFFF; margin-bottom:4px;">${escapeHtml(contractA)} ${comp.contract_a_clause ? `(Clause ${comp.contract_a_clause})` : ''}</div>
            <div>${escapeHtml(comp.contract_a_text)}</div>
          </div>
          <div class="comp-pane">
            <div style="font-weight:600; color:#FFFFFF; margin-bottom:4px;">${escapeHtml(contractB)} ${comp.contract_b_clause ? `(Clause ${comp.contract_b_clause})` : ''}</div>
            <div>${escapeHtml(comp.contract_b_text)}</div>
          </div>
        </div>
      </div>
    `).join('');

    showToast('Comparison ready!', '⚖️');
  } catch (err) {
    showToast('Comparison error: ' + err.message, '❌');
  } finally {
    elements.btnRunComparison.disabled = false;
    elements.btnRunComparison.innerHTML = 'Compare Side-by-Side';
  }
}

// Samples & Upload
async function handleLoadSamples() {
  elements.btnSidebarLoadSamples.textContent = 'Loading...';
  try {
    const res = await fetch('/api/load-samples', { method: 'POST' });
    const data = await res.json();
    showToast('Sample contracts loaded and indexed!', '⚡');
    await fetchContracts();
    switchView('chat');
  } catch (err) {
    showToast('Error: ' + err.message, '❌');
  } finally {
    elements.btnSidebarLoadSamples.textContent = 'Load Samples';
  }
}

function onFileSelected() {
  const file = elements.pdfFileInput.files[0];
  if (file) {
    elements.dropZone.querySelector('.upload-title').textContent = file.name;
    elements.dropZone.querySelector('.upload-sub').textContent = `${(file.size / 1024).toFixed(1)} KB (Ready to index)`;
    elements.btnTriggerUpload.disabled = false;
  }
}

async function handleUploadFile() {
  const file = elements.pdfFileInput.files[0];
  if (!file) return;

  elements.btnTriggerUpload.disabled = true;
  elements.uploadProgressContainer.style.display = 'block';
  elements.uploadProgressBar.style.width = '50%';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/contracts/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) throw new Error('Upload failed');
    const data = await res.json();
    elements.uploadProgressBar.style.width = '100%';

    showToast(`Indexed ${data.contract} (${data.total_clauses} clauses)!`, '📄');
    closeModal(elements.uploadModal);

    await fetchContracts();
    setActiveContract(data.contract);
    switchView('chat');
  } catch (err) {
    showToast('Upload error: ' + err.message, '❌');
  } finally {
    elements.btnTriggerUpload.disabled = false;
    elements.uploadProgressContainer.style.display = 'none';
    elements.uploadProgressBar.style.width = '0%';
  }
}

// Modal Helpers
function openModal(m) { m.classList.add('show'); }
function closeModal(m) { m.classList.remove('show'); }

// Toast Helper
let toastTimer = null;
function showToast(msg, icon = 'ℹ️') {
  elements.toastIcon.textContent = icon;
  elements.toastMsg.textContent = msg;
  elements.toast.classList.add('show');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elements.toast.classList.remove('show'), 3500);
}

// Markdown & String Utilities
function escapeHtml(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function renderMarkdown(md) {
  if (!md) return '';
  let html = escapeHtml(md);
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');
  html = html.replace(/^\s*• (.*$)/gim, '<li>$1</li>');
  html = html.replace(/^\s*- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');
  html = html.replace(/\n\n/g, '<p></p>');
  return html;
}
