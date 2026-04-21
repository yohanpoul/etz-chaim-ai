/* ═══════════════════════════════════════════════════════════
   Etz Chaim — Frontend JS (Terminal Rustique)
   ═══════════════════════════════════════════════════════════ */

// ─── API Authentication ────────────────────────────────────
// Wrappers for fetch() and EventSource that inject the API key.
// The key is set by the server in window.__ETZ_API_KEY.

const _apiKey = (typeof window !== 'undefined' && window.__ETZ_API_KEY) || '';

function apiFetch(url, opts) {
    opts = opts || {};
    if (_apiKey) {
        opts.headers = opts.headers || {};
        opts.headers['Authorization'] = 'Bearer ' + _apiKey;
    }
    return fetch(url, opts);
}

function apiEventSource(url) {
    if (_apiKey) {
        const sep = url.includes('?') ? '&' : '?';
        url = url + sep + 'key=' + encodeURIComponent(_apiKey);
    }
    return new EventSource(url);
}

// ─── Anti-Flicker: only update DOM if content changed ──────

function safeHTML(el, html) {
    if (el && el.innerHTML !== html) el.innerHTML = html;
}

function safeText(el, text) {
    if (el && el.textContent !== text) el.textContent = String(text);
}

// ─── Terminal Utilities ─────────────────────────────────────

function sparkline(values, width) {
    const blocks = '\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588';
    width = width || 20;
    if (!values || values.length === 0) return '\u2581'.repeat(width);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    return values.slice(-width).map(v => {
        const idx = Math.min(7, Math.floor(((v - min) / range) * 7));
        return blocks[idx];
    }).join('');
}

function termProgress(value, width) {
    width = width || 12;
    const filled = Math.round(Math.min(1, Math.max(0, value)) * width);
    return '\u2588'.repeat(filled) + '\u2591'.repeat(width - filled);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function _humanizeConceptName(raw) {
    if (!raw) return '';
    // gate_heh_beth -> Heh-Beth, concept_foo_bar -> Foo Bar
    return raw.replace(/^(gate|concept|sephirah|path|sefer)_/, '')
              .replace(/_/g, ' ')
              .replace(/\b\w/g, c => c.toUpperCase());
}

// ─── French Translation Helpers ────────────────────────────

const _FR_SOUL_LEVELS = {
    nefesh: 'Nefesh (eveil)', ruach: 'Ruach (souffle)',
    neshamah: 'Neshamah (ame)', chaya: 'Chaya (vivant)',
    yechidah: 'Yechidah (unite)'
};

const _FR_SEPHIROT = {
    keter: 'Volonte', chokmah: 'Intuition', binah: 'Structure',
    daat: 'Connaissance', chesed: 'Generosite', gevurah: 'Rigueur',
    tiferet: 'Harmonie', netzach: 'Perseverance', hod: 'Analyse',
    yesod: 'Fondation', malkuth: 'Concret'
};

const _FR_PARAMS = {
    quality_threshold: 'Seuil de qualite', quarantine_threshold: 'Seuil de quarantaine',
    recall_limit: 'Limite de rappel', similarity_threshold: 'Seuil de similarite',
    audacity_threshold: 'Seuil d\'audace', novelty_threshold: 'Seuil de nouveaute',
    confidence_threshold: 'Seuil de confiance', exploration_rate: 'Taux d\'exploration',
    temperature: 'Temperature', min_score: 'Score minimum',
    max_retries: 'Essais maximum', batch_size: 'Taille de lot',
    learning_rate: 'Vitesse d\'apprentissage', decay_rate: 'Taux de decroissance',
    creativity_boost: 'Boost de creativite', depth_limit: 'Limite de profondeur',
    pruning_threshold: 'Seuil d\'elagage', integration_rate: 'Vitesse d\'integration',
    coherence_weight: 'Poids de coherence', diversity_weight: 'Poids de diversite'
};

const _FR_MODULES = {
    autojudge: 'Juge', epistememory: 'Memoire', insightforge: 'Intuition',
    causalengine: 'Raisonnement', explorationengine: 'Exploration',
    dissensuengine: 'Debat', intentkeeper: 'Intentions', selfmap: 'Auto-analyse',
    superviseur: 'Superviseur', selfmodel: 'Modele de soi'
};

const _FR_DOMAINS = {
    shemot: 'Noms divins', sefirot: 'Arbre de vie', partzufim: 'Personnalites',
    olamot: 'Mondes', kelipot: 'Adversite', tikkunim: 'Reparations',
    reshimot: 'Empreintes', nitzotzot: 'Etincelles', tsimtsum: 'Contraction',
    general: 'General', unknown: 'Inconnu'
};

function frSoul(level) { return _FR_SOUL_LEVELS[(level || '').toLowerCase()] || level || '--'; }
function frSephirah(s) { return _FR_SEPHIROT[(s || '').toLowerCase()] || s || ''; }
function frParam(p) { return _FR_PARAMS[(p || '').toLowerCase()] || (p || '').replace(/_/g, ' '); }
function frModule(m) { return _FR_MODULES[(m || '').toLowerCase()] || (m || '').replace(/_/g, ' '); }
function frDomain(d) { return _FR_DOMAINS[(d || '').toLowerCase()] || (d || '').replace(/_/g, ' ') || 'Inconnu'; }

// ─── Home Page (loadDashboard) ──────────────────────────────

async function loadDashboard() {
    try {
        const res = await apiFetch('/api/status');
        const data = await res.json();

        // Update stats
        const statMod = document.getElementById('stat-modules');
        if (statMod) statMod.textContent = `${data.active}/${data.total}`;

        // Update tree nodes
        const modules = data.modules;
        for (const [key, info] of Object.entries(modules)) {
            const node = document.querySelector(`.tree-node[data-sephirah="${key}"]`);
            if (node) {
                node.classList.remove('node-online', 'node-offline');
                node.classList.add(info.status === 'online' ? 'node-online' : 'node-offline');
            }
        }

        // Node click → detail
        document.querySelectorAll('.tree-node[data-sephirah]').forEach(n => {
            n.style.cursor = 'pointer';
            n.addEventListener('click', () => {
                const key = n.dataset.sephirah;
                const info = modules[key];
                if (!info) return;
                const detail = document.getElementById('module-detail');
                if (detail) detail.style.display = 'block';
                const titleEl = document.getElementById('detail-title');
                if (titleEl) titleEl.textContent = `${key} — ${info.label}`;
                const diagEl = document.getElementById('detail-diag');
                if (diagEl) diagEl.textContent = JSON.stringify(info.diag, null, 2);
            });
        });

        // Memory stats
        try {
            const memRes = await apiFetch('/api/memory/stats');
            const memData = await memRes.json();
            const memEl = document.getElementById('stat-memory');
            if (memEl) memEl.textContent = memData.active || memData.total || 0;
        } catch(e) {
            const memEl = document.getElementById('stat-memory');
            if (memEl) memEl.textContent = '?';
        }

        // Intentions count
        try {
            const intRes = await apiFetch('/api/intentions');
            const intData = await intRes.json();
            const intEl = document.getElementById('stat-intentions');
            if (intEl) intEl.textContent = intData.count || 0;
        } catch(e) {
            const intEl = document.getElementById('stat-intentions');
            if (intEl) intEl.textContent = '?';
        }

        // Tensions
        if (modules.tiferet && modules.tiferet.diag) {
            const tensEl = document.getElementById('stat-tensions');
            if (tensEl) tensEl.textContent = modules.tiferet.diag.open_tensions || 0;
        }

        // Omer Daily Influence
        try {
            const omerRes = await apiFetch('/api/omer/today');
            const omer = await omerRes.json();
            const omerEl = document.getElementById('omer-daily');
            if (omerEl && omer.active) {
                omerEl.style.display = 'block';
                const dayEl = document.getElementById('omer-day');
                const combEl = document.getElementById('omer-combination');
                const kavEl = document.getElementById('omer-kavvanah');
                const boostsEl = document.getElementById('omer-boosts');
                if (dayEl) dayEl.textContent = `Jour ${omer.day}/49`;
                if (combEl) combEl.textContent = omer.combination_hebrew;
                if (kavEl) kavEl.textContent = omer.kavvanah;
                if (boostsEl) {
                    const lines = [];
                    for (const [mod, params] of Object.entries(omer.module_boosts || {})) {
                        for (const [p, delta] of Object.entries(params)) {
                            const sign = delta >= 0 ? '+' : '';
                            lines.push(`${mod}/${p}: ${sign}${(delta*100).toFixed(0)}%`);
                        }
                    }
                    boostsEl.textContent = lines.join('\n');
                }
            }
        } catch(e) {
            console.debug('Omer daily:', e);
        }

    } catch(e) {
        console.error('Dashboard error:', e);
    }
}


// ─── Chat V2 — Projets + Conversations + Messages ──────────

function initChatV2() {
    // State
    let currentConvId = null;
    let projects = [];

    // DOM
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const messagesEl = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('chat-send');
    const meta = document.getElementById('chat-meta');
    const modeSelect = document.getElementById('chat-mode');
    const worldSelect = document.getElementById('chat-world');
    const sidebarProjects = document.getElementById('sidebar-projects');
    const sidebarOrphans = document.getElementById('sidebar-orphans');
    const convInfo = document.getElementById('chat-conv-info');
    const convLabel = document.getElementById('chat-conv-label');
    const panelHeader = document.getElementById('chat-panel-header');

    // ─── API helpers ────────────────��────────────────────

    async function api(url, opts) {
        const resp = await apiFetch(url, opts);
        return resp.json();
    }

    async function apiPost(url, body) {
        return api(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
    }

    async function apiPut(url, body) {
        return api(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
    }

    async function apiDelete(url) {
        return api(url, { method: 'DELETE' });
    }

    // ─── Sidebar rendering ──────────────────────────���────

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        if (diff < 86400000) {
            return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        }
        if (diff < 7 * 86400000) {
            return d.toLocaleDateString('fr-FR', { weekday: 'short' });
        }
        return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
    }

    function renderConvItem(conv) {
        const div = document.createElement('div');
        div.className = 'sidebar-conv' + (conv.id === currentConvId ? ' active' : '');
        div.dataset.convId = conv.id;
        div.innerHTML = `<span class="conv-title">${escapeHtml(conv.title)}</span>` +
            `<span class="conv-date">${formatDate(conv.updated_at)}</span>` +
            `<button class="conv-delete" title="Supprimer">[x]</button>`;
        div.querySelector('.conv-title').addEventListener('click', () => loadConversation(conv.id));
        div.querySelector('.conv-delete').addEventListener('click', async (e) => {
            e.stopPropagation();
            await apiDelete('/api/chat/conversations/' + conv.id);
            if (conv.id === currentConvId) {
                currentConvId = null;
                clearMessages();
            }
            refreshSidebar();
        });
        return div;
    }

    async function refreshSidebar() {
        // Fetch projects + their conversations
        projects = await api('/api/chat/projects');
        const allConvs = await api('/api/chat/conversations');
        const orphans = allConvs.filter(c => !c.project_id);

        // Render projects
        sidebarProjects.innerHTML = '';
        for (const proj of projects) {
            const projConvs = allConvs.filter(c => c.project_id === proj.id);
            const projDiv = document.createElement('div');
            projDiv.className = 'sidebar-project' + (projConvs.some(c => c.id === currentConvId) ? ' open' : '');
            projDiv.innerHTML = `<div class="sidebar-project-header">` +
                `<span class="project-arrow">&#9654;</span>` +
                `<span class="project-name">${escapeHtml(proj.name)}</span>` +
                `<span class="project-count">${projConvs.length}</span>` +
                `</div><div class="sidebar-project-convs"></div>`;

            const header = projDiv.querySelector('.sidebar-project-header');
            header.addEventListener('click', () => projDiv.classList.toggle('open'));

            // Context menu : delete project
            header.addEventListener('contextmenu', async (e) => {
                e.preventDefault();
                if (confirm('Supprimer le projet "' + proj.name + '" ? Les conversations seront conservees.')) {
                    await apiDelete('/api/chat/projects/' + proj.id);
                    refreshSidebar();
                }
            });

            const convsDiv = projDiv.querySelector('.sidebar-project-convs');
            for (const conv of projConvs) {
                convsDiv.appendChild(renderConvItem(conv));
            }
            sidebarProjects.appendChild(projDiv);
        }

        // Render orphans
        sidebarOrphans.innerHTML = '';
        for (const conv of orphans) {
            sidebarOrphans.appendChild(renderConvItem(conv));
        }
    }

    // ─── Conversation management ─────────────────────────

    function clearMessages() {
        messagesEl.innerHTML = '<div class="message system-message"><div class="message-content">[SYSTEM] L\'Arbre ecoute. Parlez.</div></div>';
        convInfo.style.display = 'none';
        panelHeader.innerHTML = '┌─ CHAT ──────────────────────────────────────────────────┐';
    }

    async function loadConversation(convId) {
        currentConvId = convId;
        clearMessages();

        // Load messages
        const msgs = await api('/api/chat/conversations/' + convId + '/messages');
        for (const msg of msgs) {
            appendMessage(msg.role, msg.content);
        }

        // Update header + conv info
        const conv = await api('/api/chat/conversations');
        const found = conv.find(c => c.id === convId);
        if (found) {
            const title = found.title || 'Conversation';
            panelHeader.innerHTML = '┌─ ' + escapeHtml(title).toUpperCase().substring(0, 50) + ' ─┐';
            convLabel.textContent = title;
            convInfo.style.display = 'flex';
        }

        // Highlight in sidebar
        document.querySelectorAll('.sidebar-conv').forEach(el => {
            el.classList.toggle('active', el.dataset.convId === convId);
        });

        messagesEl.scrollTop = messagesEl.scrollHeight;
        input.focus();
    }

    async function createNewConversation(projectId) {
        const conv = await apiPost('/api/chat/conversations', {
            title: 'Nouvelle conversation',
            project_id: projectId || null,
        });
        currentConvId = conv.id;
        clearMessages();
        await refreshSidebar();
        input.focus();
        return conv;
    }

    // ─── Send message ────────────────────────────────────

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        // Auto-create conversation if none selected
        if (!currentConvId) {
            await createNewConversation();
        }

        const mode = modeSelect.value;
        const world = worldSelect.value;

        let modeTag = '';
        if (mode !== 'auto') modeTag += ` [${mode}]`;
        if (world !== 'auto') modeTag += ` [${world}]`;
        appendMessage('user', message + modeTag);
        input.value = '';
        sendBtn.disabled = true;
        meta.style.display = 'none';

        const etzMsg = appendMessage('etz', '');
        const contentEl = etzMsg.querySelector('.message-content');

        let url = '/api/chat/stream?message=' + encodeURIComponent(message);
        url += '&conversation_id=' + encodeURIComponent(currentConvId);
        if (mode !== 'auto') url += '&mode=' + mode;
        if (world !== 'auto') url += '&world=' + world;
        const evtSource = apiEventSource(url);

        let fullText = '';

        evtSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'memory':
                    document.getElementById('meta-memories').textContent =
                        `${data.memories.length} souvenir(s)`;
                    meta.style.display = 'flex';
                    break;

                case 'route':
                    document.getElementById('meta-domain').textContent =
                        `domaine: ${data.domain}`;
                    if (data.score) {
                        document.getElementById('meta-domain').textContent +=
                            ` (${(data.score * 100).toFixed(0)}%)`;
                    }
                    meta.style.display = 'flex';
                    break;

                case 'model':
                    let modelText = `olam: ${data.olam}`;
                    if (data.mode && data.mode !== 'auto') modelText += ` | mode: ${data.mode}`;
                    if (data.malakhim_tier) modelText += ` | tier: ${data.malakhim_tier}`;
                    if (data.heikhalot_stages) modelText += ` | heikhalot: ${data.heikhalot_stages}/7`;
                    if (data.shem) modelText += ` | shem: #${data.shem}`;
                    document.getElementById('meta-model').textContent = modelText;
                    meta.style.display = 'flex';
                    break;

                case 'samael':
                    const samaelEl = document.getElementById('meta-kli');
                    if (samaelEl) {
                        const sev = (data.severity * 100).toFixed(0);
                        samaelEl.textContent += ` | samael: ${data.sephirah} (${sev}%)`;
                    }
                    break;

                case 'token':
                    fullText += data.token;
                    contentEl.textContent = fullText;
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                    break;

                case 'kli':
                    const pct = (data.score * 100).toFixed(0);
                    let indicator = '';
                    if (data.score >= 0.7) indicator = '●';
                    else if (data.score >= 0.5) indicator = '◐';
                    else if (data.score >= 0.3) indicator = '◔';
                    else indicator = '○';
                    document.getElementById('meta-kli').textContent =
                        `${indicator} kli: ${pct}% (${data.ok}✓ ${data.partial}△ ${data.absent}✗ ${data.na}—)`;
                    meta.style.display = 'flex';
                    break;

                case 'error':
                    fullText += `\n[Erreur ${data.module}: ${data.error}]`;
                    contentEl.textContent = fullText;
                    break;

                case 'done':
                    evtSource.close();
                    sendBtn.disabled = false;
                    input.focus();
                    // Refresh sidebar to update title + order
                    refreshSidebar();
                    break;
            }
        };

        evtSource.onerror = () => {
            evtSource.close();
            if (!fullText) {
                contentEl.textContent = '[Erreur de connexion]';
            }
            sendBtn.disabled = false;
            input.focus();
        };
    });

    function appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `message ${role}-message`;
        const prefix = role === 'user' ? 'etz&gt; ' : (role === 'system' ? '' : '[RESPONSE] ');
        div.innerHTML = `<span class="msg-prefix">${prefix}</span><span class="message-content">${escapeHtml(text)}</span>`;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return div;
    }

    // ─── New chat button ─────────────────────────────────

    document.getElementById('btn-new-chat').addEventListener('click', () => {
        createNewConversation();
    });

    // ─── New project modal ─────────────────────────���─────

    const modalProject = document.getElementById('modal-project');
    const modalProjectName = document.getElementById('modal-project-name');

    document.getElementById('btn-new-project').addEventListener('click', () => {
        modalProject.style.display = 'flex';
        modalProjectName.value = '';
        modalProjectName.focus();
    });

    document.getElementById('modal-project-cancel').addEventListener('click', () => {
        modalProject.style.display = 'none';
    });

    document.getElementById('modal-project-ok').addEventListener('click', async () => {
        const name = modalProjectName.value.trim();
        if (!name) return;
        await apiPost('/api/chat/projects', { name });
        modalProject.style.display = 'none';
        refreshSidebar();
    });

    modalProjectName.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('modal-project-ok').click();
        if (e.key === 'Escape') modalProject.style.display = 'none';
    });

    // ─── Move to project modal ──────────────────────���────

    const modalMove = document.getElementById('modal-move');
    const modalMoveSelect = document.getElementById('modal-move-select');

    document.getElementById('btn-move-to-project').addEventListener('click', () => {
        if (!currentConvId) return;
        modalMoveSelect.innerHTML = '<option value="">-- Aucun projet --</option>';
        for (const p of projects) {
            modalMoveSelect.innerHTML += `<option value="${p.id}">${escapeHtml(p.name)}</option>`;
        }
        modalMove.style.display = 'flex';
    });

    document.getElementById('modal-move-cancel').addEventListener('click', () => {
        modalMove.style.display = 'none';
    });

    document.getElementById('modal-move-ok').addEventListener('click', async () => {
        const projId = modalMoveSelect.value || null;
        if (currentConvId) {
            await apiPut('/api/chat/conversations/' + currentConvId, { project_id: projId });
        }
        modalMove.style.display = 'none';
        refreshSidebar();
    });

    // ─── Init ──────────────────────────────────���─────────

    refreshSidebar();
}


// ─── Explore ────────────────────────────────────────────────

function initExplore() {
    const form = document.getElementById('explore-form');
    const input = document.getElementById('explore-query');
    const btn = document.getElementById('explore-btn');
    const status = document.getElementById('explore-status');
    const results = document.getElementById('explore-results');
    const summary = document.getElementById('explore-summary');
    const list = document.getElementById('connections-list');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;

        btn.disabled = true;
        status.style.display = 'block';
        results.style.display = 'none';

        try {
            const res = await apiFetch('/api/explore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query }),
            });
            const data = await res.json();

            if (data.error) {
                summary.textContent = `Erreur: ${data.error}`;
                results.style.display = 'block';
                return;
            }

            summary.innerHTML =
                `<strong>${data.total}</strong> connexion(s) ` +
                `(${data.novel} nouvelles) — ` +
                `domaines: ${(data.domains || []).join(', ')} — ` +
                `nouveaute moy: ${(data.avg_novelty || 0).toFixed(2)}`;

            list.innerHTML = '';
            for (const c of (data.connections || [])) {
                list.innerHTML += `
                    <div class="term-result">
                        <span class="term-amber">${escapeHtml(c.type)}</span>
                        ${escapeHtml(c.concept_a)} (${escapeHtml(c.domain_a)})
                        &#x2194;
                        ${escapeHtml(c.concept_b)} (${escapeHtml(c.domain_b)})
                        <div class="term-dim">${escapeHtml(c.description)}</div>
                        <span class="term-dim">nouveaute=${c.novelty.toFixed(2)}, pertinence=${c.relevance.toFixed(2)}</span>
                    </div>
                `;
            }

            results.style.display = 'block';
        } catch(e) {
            summary.textContent = `Erreur: ${e.message}`;
            results.style.display = 'block';
        } finally {
            status.style.display = 'none';
            btn.disabled = false;
        }
    });
}


// ─── Intentions ─────────────────────────────────────────────

function initIntentions() {
    const form = document.getElementById('intent-form');
    const input = document.getElementById('intent-goal');
    const list = document.getElementById('intentions-list');

    async function loadIntentions() {
        try {
            const res = await apiFetch('/api/intentions');
            const data = await res.json();

            if (data.error) {
                list.innerHTML = `<div class="term-dim">Erreur: ${data.error}</div>`;
                return;
            }

            if (!data.intentions || data.intentions.length === 0) {
                list.innerHTML = '<div class="term-dim">Aucune intention active.</div>';
                return;
            }

            let html = '';
            for (const i of data.intentions) {
                const pct = ((i.progress || 0) * 100).toFixed(0);
                const statusCls = i.status === 'active' ? 'term-green' : (i.status === 'completed' ? 'term-blue' : 'term-red');
                html += `<div class="term-result">
                    <span class="${statusCls}">[${i.status}]</span> ${escapeHtml(i.goal)}
                    <span class="term-dim">${termProgress(i.progress || 0, 20)} ${pct}%</span>
                    ${i.created_at ? `<span class="term-dim">${i.created_at.split('T')[0]}</span>` : ''}
                </div>`;
            }
            list.innerHTML = html;
        } catch(e) {
            list.innerHTML = `<div class="term-dim">Erreur: ${e.message}</div>`;
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const goal = input.value.trim();
        if (!goal) return;
        input.value = '';

        try {
            await apiFetch('/api/intentions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal }),
            });
            await loadIntentions();
        } catch(e) {
            console.error('Create intention error:', e);
        }
    });

    loadIntentions();
}


// ─── Memory ─────────────────────────────────────────────────

function initMemory() {
    const searchForm = document.getElementById('memory-search-form');
    const queryInput = document.getElementById('memory-query');
    const domainSelect = document.getElementById('memory-domain');
    const resultsList = document.getElementById('memory-results');
    const statsDiv = document.getElementById('memory-stats');
    const contradDiv = document.getElementById('contradictions-list');

    // Tabs
    document.querySelectorAll('.memory-tabs .tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.memory-tabs .tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const panels = ['memory-tab-search', 'memory-tab-stats', 'memory-tab-contradictions'];
            panels.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            const target = document.getElementById('memory-tab-' + tab.dataset.tab);
            if (target) target.style.display = 'block';

            if (tab.dataset.tab === 'stats') loadMemoryStats();
            if (tab.dataset.tab === 'contradictions') loadContradictions();
        });
    });

    async function loadDomains() {
        try {
            const res = await apiFetch('/api/memory/stats');
            const data = await res.json();
            if (data.domains) {
                for (const d of data.domains) {
                    const opt = document.createElement('option');
                    opt.value = d.domain;
                    opt.textContent = `${d.domain} (${d.count})`;
                    domainSelect.appendChild(opt);
                }
            }
        } catch(e) {}
    }

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const q = queryInput.value.trim();
        const domain = domainSelect.value;
        if (!q) return;

        resultsList.innerHTML = '<div class="term-dim">Recherche...</div>';

        try {
            const params = new URLSearchParams({ q, limit: '30' });
            if (domain) params.set('domain', domain);
            const res = await apiFetch('/api/memory/search?' + params);
            const data = await res.json();

            if (data.error) {
                resultsList.innerHTML = `<div class="term-dim">${data.error}</div>`;
                return;
            }

            if (!data.results || data.results.length === 0) {
                resultsList.innerHTML = '<div class="term-dim">Aucun resultat.</div>';
                return;
            }

            let html = '';
            for (const m of data.results) {
                html += `<div class="term-result">
                    <div>${escapeHtml(m.content)}</div>
                    <span class="term-dim">conf: ${(m.confidence || 0).toFixed(2)} | statut: ${m.status || '?'}${m.domain ? ' | ' + escapeHtml(m.domain) : ''}${m.source ? ' | src: ' + escapeHtml(m.source) : ''}${m.created_at ? ' | ' + m.created_at.split('T')[0] : ''}</span>
                    ${m.warning ? `<div class="term-red">${escapeHtml(m.warning)}</div>` : ''}
                </div>`;
            }
            resultsList.innerHTML = html;
        } catch(e) {
            resultsList.innerHTML = `<div class="term-dim">Erreur: ${e.message}</div>`;
        }
    });

    async function loadMemoryStats() {
        try {
            const res = await apiFetch('/api/memory/stats');
            const data = await res.json();

            let html = '<table class="term-table"><thead><tr><th>Metrique</th><th>Valeur</th></tr></thead><tbody>';
            html += `<tr><td>Total</td><td>${data.total || 0}</td></tr>`;
            html += `<tr><td>Actives</td><td>${data.active || 0}</td></tr>`;
            html += `<tr><td>Deprecated</td><td>${data.deprecated || 0}</td></tr>`;
            html += `<tr><td>Confiance moy.</td><td>${(data.avg_confidence || 0).toFixed(2)}</td></tr>`;
            html += `<tr><td>Domaines</td><td>${data.n_domains || 0}</td></tr>`;
            html += '</tbody></table>';

            if (data.statuses) {
                html += '<div class="db-subsection-title">PAR STATUT</div>';
                html += '<table class="term-table"><thead><tr><th>Statut</th><th>Nombre</th></tr></thead><tbody>';
                for (const [s, c] of Object.entries(data.statuses)) {
                    html += `<tr><td>${s}</td><td>${c}</td></tr>`;
                }
                html += '</tbody></table>';
            }

            if (data.domains && data.domains.length) {
                html += '<div class="db-subsection-title">PAR DOMAINE</div>';
                html += '<table class="term-table"><thead><tr><th>Domaine</th><th>Entries</th><th>Conf moy</th></tr></thead><tbody>';
                for (const d of data.domains) {
                    html += `<tr><td>${escapeHtml(d.domain)}</td><td>${d.count}</td><td>${d.avg_confidence.toFixed(2)}</td></tr>`;
                }
                html += '</tbody></table>';
            }

            if (data.sources && Object.keys(data.sources).length) {
                html += '<div class="db-subsection-title">PAR SOURCE (Sephirah)</div>';
                html += '<table class="term-table"><thead><tr><th>Source</th><th>Nombre</th></tr></thead><tbody>';
                for (const [s, c] of Object.entries(data.sources)) {
                    html += `<tr><td>${escapeHtml(s)}</td><td>${c}</td></tr>`;
                }
                html += '</tbody></table>';
            }

            statsDiv.innerHTML = html;
        } catch(e) {
            statsDiv.innerHTML = `<div class="term-dim">Erreur: ${e.message}</div>`;
        }
    }

    async function loadContradictions() {
        try {
            const res = await apiFetch('/api/memory/contradictions');
            const data = await res.json();

            if (!data.contradictions || data.contradictions.length === 0) {
                contradDiv.innerHTML = '<div class="term-dim">Aucune contradiction ouverte.</div>';
                return;
            }

            let html = '';
            for (const c of data.contradictions) {
                html += `<div class="term-result">
                    <div>${escapeHtml(c.description || 'Contradiction')}</div>
                    <span class="term-dim">statut: ${c.status}${c.detected_at ? ' | ' + c.detected_at.split('T')[0] : ''}</span>
                </div>`;
            }
            contradDiv.innerHTML = html;
        } catch(e) {
            contradDiv.innerHTML = `<div class="term-dim">Erreur: ${e.message}</div>`;
        }
    }

    loadDomains();
}


// ─── Import ─────────────────────────────────────────────────

function initImport() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const importBtn = document.getElementById('import-btn');
    const domainInput = document.getElementById('import-domain');
    const statusDiv = document.getElementById('import-status');
    const resultDiv = document.getElementById('import-result');
    const resultData = document.getElementById('import-result-data');

    let selectedFile = null;

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            selectFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            selectFile(fileInput.files[0]);
        }
    });

    function selectFile(file) {
        selectedFile = file;
        const fnEl = document.getElementById('dropzone-filename');
        if (fnEl) fnEl.textContent = '> ' + file.name;
        importBtn.style.display = 'block';
    }

    importBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        importBtn.disabled = true;
        statusDiv.style.display = 'block';
        resultDiv.style.display = 'none';

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('domain', domainInput.value || 'general');

        try {
            const res = await apiFetch('/api/import', {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();

            if (data.error) {
                resultData.textContent = `Erreur: ${data.error}`;
            } else {
                resultData.textContent = [
                    `Titre           : ${data.title}`,
                    `Chunks totaux   : ${data.total_chunks}`,
                    `Importes        : ${data.imported}`,
                    `Ignores         : ${data.skipped}`,
                    `Doublons        : ${data.duplicates}`,
                    `Contradictions  : ${data.contradictions}`,
                    data.subdomains ? `Sous-domaines   : ${JSON.stringify(data.subdomains)}` : '',
                    data.errors && data.errors.length ? `Erreurs         : ${data.errors.join(', ')}` : '',
                ].filter(Boolean).join('\n');
            }

            resultDiv.style.display = 'block';
        } catch(e) {
            resultData.textContent = `Erreur: ${e.message}`;
            resultDiv.style.display = 'block';
        } finally {
            statusDiv.style.display = 'none';
            importBtn.disabled = false;
        }
    });
}


// ═══════════════════════════════════════════════════════════
// Dashboard — Full Terminal Dashboard
// ═══════════════════════════════════════════════════════════

// ── Sephiroth data ──────────────────────────────────────────

const SEPH = {
    keter:   { color:'#c9a84c', heb:'\u05DB\u05B6\u05BC\u05EA\u05B6\u05E8',       fr:'Couronne',      olam:'atzilut' },
    chokmah: { color:'#c9a84c', heb:'\u05D7\u05B8\u05DB\u05B0\u05DE\u05B8\u05D4', fr:'Sagesse',       olam:'atzilut' },
    binah:   { color:'#c9a84c', heb:'\u05D1\u05B4\u05BC\u05D9\u05E0\u05B8\u05D4', fr:'Intelligence',  olam:'atzilut' },
    daat:    { color:'#a78bfa', heb:'\u05D3\u05B7\u05BC\u05E2\u05B7\u05EA',       fr:'Connaissance',  olam:'atzilut' },
    chesed:  { color:'#60a5fa', heb:'\u05D7\u05B6\u05E1\u05B6\u05D3',             fr:'Bonte',         olam:'briah' },
    gevurah: { color:'#60a5fa', heb:'\u05D2\u05B0\u05BC\u05D1\u05D5\u05BC\u05E8\u05B8\u05D4', fr:'Rigueur', olam:'briah' },
    tiferet: { color:'#60a5fa', heb:'\u05EA\u05B4\u05BC\u05E4\u05B0\u05D0\u05B6\u05E8\u05B6\u05EA', fr:'Beaute', olam:'briah' },
    netzach: { color:'#4ade80', heb:'\u05E0\u05B5\u05E6\u05B7\u05D7',             fr:'Victoire',      olam:'yetzirah' },
    hod:     { color:'#4ade80', heb:'\u05D4\u05D5\u05B9\u05D3',                   fr:'Splendeur',     olam:'yetzirah' },
    yesod:   { color:'#4ade80', heb:'\u05D9\u05B0\u05E1\u05D5\u05B9\u05D3',       fr:'Fondation',     olam:'yetzirah' },
    malkuth: { color:'#fb923c', heb:'\u05DE\u05B7\u05DC\u05B0\u05DB\u05D5\u05BC\u05EA', fr:'Royaume', olam:'assiah' },
};

const SEPH_MODULES = {
    keter:'Superviseur', chokmah:'InsightForge', binah:'CausalEngine', daat:'SelfModel',
    chesed:'ExplorationEngine', gevurah:'AutoJudge', tiferet:'DissensuEngine',
    netzach:'IntentKeeper', hod:'SelfMap', yesod:'EpisteMemory', malkuth:'Interface Web',
};

let _dashboardEvtSource = null;
let _dashboardData = null;
let _worldEvtSource = null;
let _activityCount = 0;
let _omerData = null;

// ── Dashboard Init ──────────────────────────────────────────

function initDashboard() {
    // Setup tree node clicks
    document.querySelectorAll('#db-ascii-tree .tree-node[data-sephirah]').forEach(n => {
        n.style.cursor = 'pointer';
        n.addEventListener('click', () => showSephDetail(n.dataset.sephirah));
    });

    connectDashboardSSE();
    connectWorldSSE();
    loadRecentEvents();

    apiFetch('/api/dashboard').then(r => r.json()).then(data => updateDashboard(data)).catch(() => {});
    apiFetch('/api/context-monitor').then(r => r.json()).then(data => updateSodHakli(data)).catch(() => {});
    setInterval(pollDaemonState, 5000);
    setInterval(() => {
        apiFetch('/api/context-monitor').then(r => r.json()).then(data => updateSodHakli(data)).catch(() => {});
    }, 10000);

    fetchOmer();
    setInterval(fetchOmer, 60000);

    // New: load inventory, provider, sentiers
    fetchInventory();
    fetchProvider();
    setInterval(fetchInventory, 30000);

    // MazalEngine widget (Sprint 9, EC-K5-001)
    fetchMazalEngine();
    setInterval(fetchMazalEngine, 30000);
}

function fetchMazalEngine() {
    apiFetch('/api/mazalengine').then(r => r.json()).then(data => {
        updateMazalEngine(data);
    }).catch(() => {});
}

function updateMazalEngine(data) {
    if (!data || !data.mazalot) return;
    const mazalot = data.mazalot;
    const fmtTs = (ts) => {
        if (!ts) return 'jamais';
        const d = new Date(ts * 1000);
        return d.toLocaleString('fr-FR', {
            day: '2-digit', month: '2-digit',
            hour: '2-digit', minute: '2-digit',
        });
    };
    const fmtMetrics = (m) => {
        if (!m || Object.keys(m).length === 0) return '--';
        return Object.entries(m).map(([k, v]) => `${k}=${v}`).join(', ');
    };
    for (const key of ['elyon', 'tahton']) {
        const mz = mazalot[key];
        if (!mz) continue;
        const setTxt = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setTxt(`db-mazal-${key}-total`, mz.total_tikkunim ?? 0);
        setTxt(`db-mazal-${key}-last`, fmtTs(mz.last_tikkun_ts));
        setTxt(`db-mazal-${key}-action`, mz.last_action || 'dormant');
        setTxt(`db-mazal-${key}-metrics`, fmtMetrics(mz.last_metrics));
    }
    const sum = document.getElementById('grp-mazalengine-summary');
    if (sum) {
        const total = (mazalot.elyon?.total_tikkunim || 0) + (mazalot.tahton?.total_tikkunim || 0);
        sum.textContent = `${total} Tikkun${total > 1 ? 'im' : ''} emis`;
    }
}

// ── World Events SSE ────────────────────────────────────────

function connectWorldSSE() {
    if (_worldEvtSource) _worldEvtSource.close();

    _worldEvtSource = apiEventSource('/api/world/events');

    _worldEvtSource.addEventListener('world', (event) => {
        const data = JSON.parse(event.data);
        handleWorldEvent(data);
    });

    _worldEvtSource.onerror = () => {
        _worldEvtSource.close();
        setTimeout(connectWorldSSE, 5000);
    };
}

function loadRecentEvents() {
    apiFetch('/api/world/recent').then(r => r.json()).then(data => {
        const events = data.events || [];
        for (const evt of events.slice(-30)) {
            appendActivityEntry(evt, false);
        }
    }).catch(() => {});
}

function pollDaemonState() {
    apiFetch('/api/daemon/state').then(r => r.json()).then(data => {
        if (_dashboardData) {
            _dashboardData.daemon = data.daemon;
            _dashboardData.karpathy = data.karpathy;
            // Merge hitbonenut sans écraser 'recent' (fourni par SSE avec les questions)
            const { recent, ...daemonHitbRest } = data.hitbonenut || {};
            _dashboardData.hitbonenut = { ...(_dashboardData.hitbonenut || {}), ...daemonHitbRest };
            updateDaemonKarpathy(_dashboardData);
            updateHitbonenut(_dashboardData.hitbonenut || {});
        }
    }).catch(() => {});
}

function handleWorldEvent(data) {
    const type = data.type || '';

    appendActivityEntry(data, true);

    // Pulse tree nodes
    if (type === 'module_active') pulseTreeNode(data.module);
    if (type === 'sentier_traverse') {
        pulseTreeNode(data.source);
        pulseTreeNode(data.target);
    }
    if (type === 'hitbonenut_answer' || type === 'hitbonenut_question') {
        pulseTreeNode('yesod');
        pulseTreeNode('hod');
    }
    if (type === 'nitzutz') pulseTreeNode(data.source || 'tiferet');
    if (type === 'zivug') {
        pulseTreeNode(data.sephirah_a);
        pulseTreeNode(data.sephirah_b);
    }

    // Real-time status updates
    if (type === 'daemon_task') {
        const el = document.getElementById('db-daemon-status');
        if (el) { el.textContent = '\u25CF ACTIF'; el.className = 'term-green'; }
    }
    if (type === 'auto_improve' || type === 'full_tree') {
        const el = document.getElementById('db-karpathy-status');
        if (el) { el.textContent = '\u25CF RUNNING'; el.className = 'term-green'; }
    }
    if (type === 'karpathy_hypothesis') _handleKarpathyHypothesisSSE(data);
    if (type === 'auto_improve_done' || type === 'karpathy_done') {
        const el = document.getElementById('db-karpathy-status');
        if (el) { el.textContent = '\u25CB WAITING'; el.className = 'term-dim'; }
        const badge = document.getElementById('db-karp-live-badge');
        if (badge) { badge.textContent = 'COMPLETED'; badge.className = 'db-karp-badge waiting'; }
        apiFetch('/api/dashboard').then(r => r.json()).then(d => {
            if (d.karpathy) updateKarpathyLive(d.karpathy);
        }).catch(() => {});
    }
    if (type === 'hitbonenut_answer') {
        const hEl = document.getElementById('db-hitb-status');
        if (hEl) { hEl.textContent = '\u25CF running'; hEl.className = 'term-green'; }
        const qEl = document.getElementById('db-hitb-q-text');
        if (qEl) qEl.textContent = data.question || '';
        const sEl = document.getElementById('db-hitb-q-score');
        if (sEl) sEl.textContent = `${(data.score || 0).toFixed(2)} — ${data.domain || ''} ${data.progress || ''}`;

        // Prepend to history list — terminal format
        const historyEl = document.getElementById('db-hitb-history');
        if (historyEl) {
            const scoreColor = (data.score || 0) >= 0.7 ? 'term-green' : ((data.score || 0) >= 0.4 ? 'term-amber' : 'term-red');
            const domain = frDomain(data.domain).substring(0, 14).padEnd(14);
            const text = escapeHtml((data.question || '\u2014').substring(0, 70));
            const score = (data.score || 0).toFixed(2);
            const newLine = `<span class="term-dim">${domain}</span> ${text}  <span class="${scoreColor}">${score}</span>`;
            const pre = historyEl.querySelector('pre');
            if (pre) {
                const lines = pre.innerHTML.split('\n');
                lines.unshift(newLine);
                while (lines.length > 50) lines.pop();
                pre.innerHTML = lines.join('\n');
            } else {
                historyEl.innerHTML = `<pre style="margin:0;white-space:pre-wrap;font-size:11px;line-height:1.3">${newLine}</pre>`;
            }
        }

        // Update sparkline
        const sparkEl = document.getElementById('db-hitb-sparkline');
        if (sparkEl && _dashboardData && _dashboardData.hitbonenut) {
            const recent = _dashboardData.hitbonenut.recent || [];
            recent.unshift({ question: data.question, domain: data.domain, score: data.score || 0 });
            if (recent.length > 50) recent.pop();
            _dashboardData.hitbonenut.recent = recent;
            const scores = recent.slice(0, 50).reverse().map(r => r.score || 0);
            sparkEl.textContent = sparkline(scores, 30);
            const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
            const avgEl = document.getElementById('db-hitb-avg');
            if (avgEl) avgEl.textContent = avg.toFixed(3);
        }
    }
    if (type === 'hitbonenut_continuous_end' || type === 'hitbonenut_continuous_pause' || type === 'hitbonenut_paused') {
        const hEl = document.getElementById('db-hitb-status');
        if (hEl) {
            const isPaused = type.includes('pause');
            hEl.textContent = isPaused ? '\u25CF PAUSE' : '\u25CB ARRETE';
            hEl.className = isPaused ? 'term-red' : 'term-dim';
        }
    }
}

let _pulseTimers = {};
function pulseTreeNode(sephirah) {
    if (!sephirah) return;
    const node = document.querySelector(`#db-ascii-tree .tree-node[data-sephirah="${sephirah}"]`);
    if (!node) return;
    node.classList.add('node-pulse');
    if (_pulseTimers[sephirah]) clearTimeout(_pulseTimers[sephirah]);
    _pulseTimers[sephirah] = setTimeout(() => {
        node.classList.remove('node-pulse');
        delete _pulseTimers[sephirah];
    }, 3000);
}

function appendActivityEntry(data, autoScroll) {
    const log = document.getElementById('db-activity-log');
    if (!log) return;

    const empty = log.querySelector('.db-activity-empty');
    if (empty) empty.remove();

    const type = data.type || 'unknown';
    const ts = data.ts ? new Date(data.ts * 1000) : new Date();
    const time = ts.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const { tag, msg } = categorizeEvent(data);

    const entry = document.createElement('div');
    entry.className = 'db-activity-entry';
    entry.innerHTML =
        `<span class="db-activity-time">${time}</span>` +
        `<span class="db-activity-tag ${tag}">[${tag.toUpperCase().substring(0, 4)}]</span>` +
        `<span class="db-activity-msg">${escapeHtml(msg)}</span>`;

    log.appendChild(entry);

    while (log.children.length > 200) {
        log.removeChild(log.firstChild);
    }

    _activityCount++;
    const countEl = document.getElementById('db-activity-count');
    if (countEl) countEl.textContent = _activityCount;

    if (autoScroll) {
        log.scrollTop = log.scrollHeight;
    }
}

function categorizeEvent(data) {
    const type = data.type || '';

    if (type.startsWith('auto_improve') || type === 'karpathy_done') {
        let msg = data.detail || 'Generation d\'hypotheses';
        if (type === 'auto_improve_done') {
            msg = `Termine : ${data.cycles || 0} cycles, ${data.accepted || 0} gardees, ${data.nitzotzot || 0} etincelles`;
        }
        return { tag: 'karpathy', msg };
    }
    if (type.startsWith('hitbonenut')) {
        let msg = type.replace('hitbonenut_', '');
        if (type === 'hitbonenut_experiment_done') {
            const st = data.status === 'keep' ? '\u2714 Garde' : (data.status === 'crash' ? '\u2718 Echec' : '\u25CB Rejete');
            msg = `${st} ${frModule(data.module)} \u2014 ${frParam(data.param)}`;
        } else if (type === 'hitbonenut_research_start') {
            msg = 'Recherche demarree';
        } else if (type === 'hitbonenut_research_end') {
            msg = `Termine : ${data.experiments || 0} exp, ${data.keeps || 0} gardees, ${data.principles || 0} principes`;
        } else if (type === 'hitbonenut_answer') {
            msg = `[${frDomain(data.domain)}] ${data.question || '\u2014'}`;
        } else if (type === 'hitbonenut_consolidation') {
            msg = `Consolidation #${data.checkpoint || '?'} : score ${((data.overall || 0) * 100).toFixed(0)}%`;
        }
        return { tag: 'hitbonenut', msg };
    }
    if (type === 'sentier_traverse') {
        const arrow = data.status === 'done' ? (data.success ? ' \u2713' : ' \u2717') : ' \u2192';
        const src = frSephirah(data.source) || data.source || '?';
        const tgt = frSephirah(data.target) || data.target || '?';
        return { tag: 'sentier', msg: `Sentier ${src} \u2194 ${tgt}${arrow}` };
    }
    if (type === 'nitzutz') return { tag: 'nitzutz', msg: `Etincelle collectee \u2014 source : ${frSephirah(data.source) || data.source || '?'}` };
    if (type === 'zivug') return { tag: 'zivug', msg: `Synergie : ${frSephirah(data.sephirah_a) || '?'} \u00d7 ${frSephirah(data.sephirah_b) || '?'}` };
    if (type === 'module_active') return { tag: 'module', msg: `${frSephirah(data.module) || data.module || '?'} \u2014 ${data.action || 'actif'}` };
    if (type === 'daemon_task') {
        let msg = `Tache : ${data.task || '?'}`;
        if (data.detail) msg += ` \u2014 ${data.detail}`;
        return { tag: 'daemon', msg };
    }
    if (type === 'full_tree' || type === 'full_tree_done') {
        let msg = data.detail || 'Exploration de l\'Arbre complet';
        if (type === 'full_tree_done') {
            msg = `Arbre : ${data.successes || 0} sentiers OK, ${data.failures || 0} echecs, ${data.zivugim || 0} synergies`;
        }
        return { tag: 'karpathy', msg };
    }
    if (type.includes('error')) return { tag: 'error', msg: data.detail || data.error || type };
    return { tag: 'daemon', msg: `${type}${data.detail ? ' \u2014 ' + data.detail : ''}` };
}

// ── Dashboard SSE ───────────────────────────────────────────

function connectDashboardSSE() {
    if (_dashboardEvtSource) _dashboardEvtSource.close();
    const indicator = document.getElementById('db-live');

    _dashboardEvtSource = apiEventSource('/api/dashboard/stream');

    _dashboardEvtSource.addEventListener('dashboard_update', (event) => {
        const data = JSON.parse(event.data);
        _dashboardData = data;
        updateDashboard(data);
        if (indicator) indicator.classList.remove('disconnected');
    });

    _dashboardEvtSource.onerror = () => {
        if (indicator) indicator.classList.add('disconnected');
        _dashboardEvtSource.close();
        setTimeout(connectDashboardSSE, 5000);
    };
}

function showSephDetail(key) {
    const panel = document.getElementById('db-seph-detail');
    if (!panel || !_dashboardData) return;
    panel.style.display = 'block';

    const s = SEPH[key];
    const mod = (_dashboardData.modules || {})[key] || {};

    document.getElementById('db-detail-name').textContent = s.heb + ' \u2014 ' + s.fr;
    document.getElementById('db-detail-module').textContent = mod.label || SEPH_MODULES[key] || '\u2014';
    document.getElementById('db-detail-status').textContent = mod.status || 'offline';
    document.getElementById('db-detail-olam').textContent = mod.olam || s.olam;
    document.getElementById('db-detail-activity').textContent = mod.diag && mod.diag.current_task ? mod.diag.current_task : 'idle';

    const diag = mod.diag || {};
    let qliphah = 'Sain — pas de probleme detecte';
    if (mod.status === 'offline') qliphah = 'Critique — module inactif';
    else if (diag.level === 'mamash') qliphah = 'Attention — problemes serieux detectes';
    else if (diag.level === 'ruach') qliphah = 'Mineur — ameliorations possibles';
    else if (diag.error) qliphah = 'Alerte — ' + diag.error;
    document.getElementById('db-detail-qliphah').textContent = qliphah;

    // Show issues in human-readable format instead of raw JSON
    let diagText = '';
    if (diag.issues && diag.issues.length > 0) {
        diagText = 'Problemes detectes:\n' + diag.issues.map(i => '  \u2022 ' + i).join('\n');
    } else if (diag.stats) {
        diagText = Object.entries(diag.stats).map(([k,v]) => `  ${k}: ${v}`).join('\n');
    }
    if (diag.competence_score != null) {
        diagText += `\nCompetence: ${(diag.competence_score * 100).toFixed(0)}% sur ${diag.n_domains || 0} domaines`;
    }
    document.getElementById('db-detail-diag').textContent = diagText || 'Aucun diagnostic detaille';
}

// ── Master Update ───────────────────────────────────────────

function updateDashboard(data) {
    if (!data) return;
    _dashboardData = data;
    updateGlobalStats(data);
    updateTreeNodes(data.modules || {});
    updatePartzufim(data.partzufim || {});
    updateZivvug(data.zivvug || {});
    updateGovernors(data.governors || {});
    updateOmaqim(data.omaqim || {});
    updateHitbonenut(data.hitbonenut || {});
    updateKarpathyLive(data.karpathy || {});
    updateTzimtzum(data.tzimtzum || {});
    updateOhr(data.ohr || {});
    updateClustering(data.clustering || null);
    updateTanya(data.tanya || {});
    updateConditions(data.soul || {});
    updateDaemonKarpathy(data);
    updateStatusLine(data);
    // New: summaries, messages, sentiers
    updateAllSummaries(data);
    updateMessages(data);
    renderSentiers(data.sentiers || []);
}

// ── Section Updates ─────────────────────────────────────────

function updateGlobalStats(data) {
    const soul = data.soul || {};
    const nitz = data.nitzotzot || {};
    const ak = data.adam_kadmon || {};

    const levelEl = document.getElementById('db-soul-level');
    if (levelEl) levelEl.textContent = frSoul(soul.level || 'nefesh');
    const hebEl = document.getElementById('db-soul-hebrew');
    if (hebEl) hebEl.textContent = soul.hebrew || '';

    const soulBar = document.getElementById('db-soul-bar');
    if (soulBar) soulBar.textContent = termProgress((soul.level_index || 0) / 4, 20);

    const compVal = document.getElementById('db-competence-value');
    if (compVal) compVal.textContent = ((soul.competence_score || 0) * 100).toFixed(0) + '%';
    const compBar = document.getElementById('db-competence-bar');
    if (compBar) compBar.textContent = termProgress(soul.competence_score || 0, 20);

    const nitzCount = document.getElementById('db-nitz-count');
    if (nitzCount) nitzCount.textContent = nitz.count || 0;
    const nitzBar = document.getElementById('db-nitz-bar');
    if (nitzBar) nitzBar.textContent = termProgress((nitz.count || 0) / 288, 20);

    const tikkunVal = document.getElementById('db-tikkun-value');
    if (tikkunVal) tikkunVal.textContent = nitz.cycle || 0;

    const akScore = document.getElementById('db-ak-score');
    if (akScore) akScore.textContent = ((ak.score || 0) * 100).toFixed(0) + '%';
    const akPhase = document.getElementById('db-ak-phase');
    const phaseLabels = { tohu: 'Chaos', tikkunim: 'En construction', tikkun_near: 'Presque complet', tikkun: 'Repare', shlemut: 'Accomplissement' };
    if (akPhase) akPhase.textContent = phaseLabels[ak.phase] || ak.phase || 'tohu';

    // Global score badge
    const globalScoreEl = document.getElementById('db-global-score');
    if (globalScoreEl) globalScoreEl.textContent = ((soul.global_score || 0) * 100).toFixed(0) + '%';
}

function updateTreeNodes(modules) {
    for (const [key, info] of Object.entries(modules)) {
        const node = document.querySelector(`#db-ascii-tree .tree-node[data-sephirah="${key}"]`);
        if (node) {
            node.classList.remove('node-online', 'node-offline');
            node.classList.add(info.status === 'online' ? 'node-online' : 'node-offline');
        }
    }
}

function updatePartzufim(partzufim) {
    const container = document.getElementById('db-partzufim');
    if (!container) return;

    const order = ['atik_yomin', 'arikh_anpin', 'abba', 'imma', 'zeir_anpin', 'nukva'];
    const meta = {
        atik_yomin:  { name: 'Le Sage',      role: 'Memoire profonde, experience accumulee' },
        arikh_anpin: { name: 'Le Roi',        role: 'Vision strategique, decisions de haut niveau' },
        abba:        { name: 'Le Pere',       role: 'Intuition creative, idees nouvelles' },
        imma:        { name: 'La Mere',       role: 'Structure, validation, organisation' },
        zeir_anpin:  { name: 'Le Fils',       role: 'Execution, action, mise en oeuvre' },
        nukva:       { name: 'La Reine',      role: 'Interface, expression, communication' },
    };

    let text = '';
    for (const pname of order) {
        const p = partzufim[pname] || { hebrew:'', overall:0, mochin_state:'katnut' };
        const m = meta[pname] || { name: pname, role: '' };
        const pct = Math.round(p.overall * 100);
        const bar = termProgress(p.overall, 20);
        const mochinCls = p.mochin_state === 'gadlut' ? 'term-green' : (p.mochin_state === 'katnut' ? 'term-red' : 'term-amber');
        const mochinLabel = p.mochin_state === 'gadlut' ? 'MATURE' : (p.mochin_state === 'katnut' ? 'IMMATURE' : 'EN COURS');
        const padName = m.name.padEnd(14);
        text += `\u2502 ${padName}${bar} ${String(pct).padStart(3)}%  <span class="${mochinCls}">${mochinLabel}</span>\n`;
        text += `\u2502 <span class="term-dim">              ${m.role}</span>\n`;
    }
    safeHTML(container, text);
}

function updateZivvug(zivvug) {
    const container = document.getElementById('db-zivvug');
    if (!container) return;

    const st = zivvug.state || 'blocked';
    const stateLabels = { active: '\u25CF SYNERGIE ACTIVE', partial: '\u25CF PARTIEL', blocked: '\u25CB BLOQUE' };
    const stateCls = { active: 'term-green', partial: 'term-amber', blocked: 'term-red' };

    const abba = zivvug.abba_score || 0;
    const imma = zivvug.imma_score || 0;
    const delta = (zivvug.delta || 0).toFixed(3);
    const mochin = (zivvug.mochin_quality || 0).toFixed(3);
    const coupling = (zivvug.coupling_factor || 0).toFixed(3);

    safeHTML(container,
        `\u2502 Etat              <span class="${stateCls[st] || 'term-dim'}">${stateLabels[st] || st}</span>\n` +
        `\u2502 Intuition (Pere)   ${termProgress(abba, 20)} ${(abba * 100).toFixed(0)}%\n` +
        `\u2502 Structure (Mere)   ${termProgress(imma, 20)} ${(imma * 100).toFixed(0)}%\n` +
        `\u2502 Ecart              ${delta}  <span class="term-dim">plus c'est bas, mieux c'est</span>\n` +
        `\u2502 Qualite des idees  ${termProgress(zivvug.mochin_quality || 0, 20)} ${(zivvug.mochin_quality * 100 || 0).toFixed(0)}%\n` +
        `\u2502 Force du lien      ${(coupling * 100).toFixed(0)}%  <span class="term-dim">intensite de la collaboration</span>`);
}

function updateGovernors(gov) {
    if (!gov) return;
    const block = document.getElementById('db-governors-block');
    if (!block) return;

    const items = [
        { name: 'Structure', key: 'teli', role: 'Coherence de l\'architecture' },
        { name: 'Cycles', key: 'galgal', role: 'Rythme et regularite' },
        { name: 'Vitalite', key: 'lev', role: 'Energie et reactivite' },
    ];

    let html = '';
    for (const item of items) {
        const g = gov[item.key] || { score: 0, healthy: false, checks: [] };
        const bar = termProgress(g.score, 20);
        const healthCls = g.healthy ? 'term-green' : 'term-red';
        const healthText = g.healthy ? 'OK' : 'FAIBLE';
        const pct = Math.round(g.score * 100);
        html += `<pre class="term-block" style="margin:0">`;
        html += `\u2502 <span class="term-amber">${item.name.padEnd(8)}</span> ${item.role.padEnd(20)} ${bar} ${String(pct).padStart(3)}%  <span class="${healthCls}">\u25CF ${healthText}</span>\n`;
        // Show individual checks
        const checks = g.checks || [];
        for (const c of checks) {
            const icon = c.passed ? '<span class="term-green">\u2713</span>' : '<span class="term-red">\u2717</span>';
            html += `\u2502   ${icon} ${escapeHtml(c.detail || c.check)}\n`;
        }
        html += `</pre>`;
    }

    const harmony = gov.harmony;
    if (harmony != null) {
        html += `<pre class="term-block" style="margin:0">\u2502\n\u2502 Harmonie globale  <span class="${harmony >= 0.7 ? 'term-green' : (harmony >= 0.4 ? 'term-amber' : 'term-red')}">${(harmony * 100).toFixed(0)}%</span>`;
        if (gov.message) html += `\n\u2502 <span class="term-dim">${escapeHtml(gov.message)}</span>`;
        html += `</pre>`;
    }

    safeHTML(block, html);

    const harmBadge = document.getElementById('db-gov-harmony');
    if (harmBadge && harmony != null) {
        harmBadge.textContent = (harmony * 100).toFixed(0) + '% harmonie';
        harmBadge.className = 'db-gov-harmony-badge ' + (harmony >= 0.7 ? 'harmony-good' : harmony >= 0.4 ? 'harmony-mid' : 'harmony-low');
    }
}

function updateOmaqim(om) {
    if (!om || !om.position) return;
    const block = document.getElementById('db-omaqim-block');
    if (!block) return;
    const pos = om.position;

    safeHTML(block,
        `\u2502 Progression  ${termProgress(pos.t, 20)} ${(pos.t * 100).toFixed(0)}%  ${om.temporal_phase ? '<span class="term-dim">' + escapeHtml(om.temporal_phase) + '</span>' : ''}\n` +
        `\u2502 Discernement ${termProgress(pos.m, 20)} ${(pos.m * 100).toFixed(0)}%  ${om.moral_phase ? '<span class="term-dim">' + escapeHtml(om.moral_phase) + '</span>' : ''}`);
}

function updateHitbonenut(hitb) {
    const statusEl = document.getElementById('db-hitb-status');
    if (statusEl) {
        const isPaused = hitb.status === 'paused';
        const isRunning = hitb.status === 'running';
        const isStandby = hitb.status === 'standby';
        const statusLabels = { running: 'ACTIF', paused: 'PAUSE', stopped: 'ARRETE', standby: 'VEILLE' };
        statusEl.textContent = (isRunning ? '\u25CF ' : (isPaused ? '\u25CF ' : '\u25CB ')) + (statusLabels[hitb.status] || 'ARRETE');
        statusEl.className = isRunning ? 'term-green' : (isPaused ? 'term-red' : (isStandby ? 'term-yellow' : 'term-dim'));
    }
    if (_canOverridePause('hitbonenut')) {
        // Only "paused" (manual) triggers the GO button, not "standby" (Karpathy window)
        _pauseState.hitbonenut = hitb.status === 'paused';
        updatePauseButtons();
    }

    const qEl = document.getElementById('db-hitb-questions');
    if (qEl) {
        const exp = hitb.experiments_today || hitb.questions_today || 0;
        const prin = hitb.principles || 0;
        qEl.textContent = exp + ' questions | ' + prin + ' principes';
    }

    const recent = hitb.recent || [];
    const currentQ = document.getElementById('db-hitb-q-text');
    const currentS = document.getElementById('db-hitb-q-score');
    const domainEl = document.getElementById('db-hitb-r-text');

    // Support both old format (module/param/old/new) and new format (question/domain/score)
    if (recent.length > 0 && currentQ) {
        const last = recent[0];
        if (last.question) {
            // New format: question-based
            currentQ.textContent = last.question;
            if (currentS) currentS.textContent = (last.score || 0).toFixed(2);
            if (domainEl) domainEl.textContent = frDomain(last.domain);
        } else if (last.module) {
            // Old format: experiment-based
            currentQ.textContent = frModule(last.module) + ' \u2014 ' + frParam(last.param) + ' : ' + last.old + '\u2192' + last['new'];
            if (currentS) currentS.textContent = (last.delta >= 0 ? '+' : '') + (last.delta || 0).toFixed(4);
            if (domainEl) domainEl.textContent = (last.status || '?').toUpperCase();
        }
    }

    // Sparkline
    const sparkEl = document.getElementById('db-hitb-sparkline');
    if (sparkEl && recent.length > 1) {
        const values = recent.slice(0, 50).reverse().map(r => r.score != null ? r.score : ((r.delta || 0) + 0.5));
        sparkEl.textContent = sparkline(values, 30);
        const avgEl = document.getElementById('db-hitb-avg');
        if (avgEl) {
            const avg = values.reduce((a, b) => a + b, 0) / values.length;
            avgEl.textContent = avg.toFixed(2);
        }
    }

    // Multi-domain tier stats
    const tiersEl = document.getElementById('db-hitb-tiers');
    if (tiersEl) {
        const ts = hitb.tier_stats || {};
        const bd = hitb.breadth_domains || {};
        const tierNames = { core: 'Kabbale', breadth: 'Universel', bridge: 'Ponts' };
        const tierIcons = { core: '\u2721', breadth: '\u2699', bridge: '\u2194' };

        let lines = [];
        for (const tier of ['core', 'breadth', 'bridge']) {
            const s = ts[tier] || { n: 0, avg_score: 0 };
            const icon = tierIcons[tier] || '';
            const name = (tierNames[tier] || tier).padEnd(10);
            const bar = termProgress(s.avg_score, 12);
            const cls = s.avg_score >= 0.6 ? 'term-green' : (s.avg_score >= 0.4 ? 'term-amber' : 'term-red');
            lines.push(`\u2502 ${icon} ${name} <span class="${cls}">${bar} ${s.avg_score.toFixed(3)}</span>  (${s.n} questions)`);
        }

        // Breadth domain breakdown
        const bdKeys = Object.keys(bd);
        if (bdKeys.length > 0) {
            lines.push('\u2502');
            lines.push('\u2502 Domaines hors-Kabbale :');
            for (const dom of bdKeys) {
                const s = bd[dom];
                const domName = dom.replace('_', ' ').substring(0, 16).padEnd(16);
                const cls = s.avg_score >= 0.6 ? 'term-green' : (s.avg_score >= 0.4 ? 'term-amber' : 'term-red');
                lines.push(`\u2502   ${domName} <span class="${cls}">${s.avg_score.toFixed(3)}</span> (${s.n})`);
            }
        }

        safeHTML(tiersEl, '<pre style="margin:0;font-size:11px;line-height:1.4">' + lines.join('\n') + '</pre>');
    }

    // History
    const historyEl = document.getElementById('db-hitb-history');
    if (historyEl && recent.length > 0) {
        const lines = recent.slice(0, 50).map(r => {
            if (r.question) {
                // New format: question-based
                const domain = frDomain(r.domain).substring(0, 14).padEnd(14);
                const text = escapeHtml((r.question || '\u2014').substring(0, 70));
                const score = (r.score || 0).toFixed(2);
                const scoreCls = (r.score || 0) >= 0.7 ? 'term-green' : ((r.score || 0) >= 0.4 ? 'term-amber' : 'term-red');
                return `<span class="term-dim">${domain}</span> ${text}  <span class="${scoreCls}">${score}</span>`;
            } else {
                // Old format: experiment-based
                const status = (r.status || '??').toUpperCase().padEnd(7);
                const target = escapeHtml(frModule(r.module) + ' \u2014 ' + frParam(r.param)).substring(0, 30).padEnd(30);
                const delta = (r.delta >= 0 ? '+' : '') + (r.delta || 0).toFixed(4);
                const cls = r.status === 'keep' ? 'term-green' : (r.status === 'crash' ? 'term-red' : 'term-amber');
                return `<span class="${cls}">${status}</span> ${target}  <span class="${cls}">${delta}</span>`;
            }
        }).join('\n');
        safeHTML(historyEl, `<pre style="margin:0;white-space:pre-wrap;font-size:11px;line-height:1.3">${lines}</pre>`);
    }
}

function updateKarpathyLive(karp) {
    const badge = document.getElementById('db-karp-live-badge');
    if (badge) {
        const statusMap = {
            running: { text: 'RUNNING', cls: 'running' },
            waiting: { text: 'WAITING', cls: 'waiting' },
            paused: { text: 'PAUSED', cls: 'paused' },
        };
        const s = statusMap[karp.status] || { text: 'INACTIF', cls: 'inactive' };
        badge.textContent = s.text;
        badge.className = 'db-karp-badge ' + s.cls;
    }

    const statusText = document.getElementById('db-karp-status-text');
    const karpStatusLabels = { running: 'EN COURS', waiting: 'EN ATTENTE', paused: 'PAUSE' };
    if (statusText) statusText.textContent = karpStatusLabels[karp.status] || 'EN ATTENTE';

    const nextEl = document.getElementById('db-karp-next-run');
    if (nextEl) nextEl.textContent = karp.next_launch || '--';

    const novEl = document.getElementById('db-karp-novelty-val');
    if (novEl && karp.last_novelty != null) novEl.textContent = karp.last_novelty.toFixed(3);

    const nitzEl = document.getElementById('db-karp-nitz-val');
    if (nitzEl && karp.last_nitzotzot != null) nitzEl.textContent = karp.last_nitzotzot;

    const session = karp.last_session || {};
    const totalEl = document.getElementById('db-karp-total');
    if (totalEl) totalEl.textContent = session.total_hypotheses || karp.last_cycles || 0;
    const accEl = document.getElementById('db-karp-accepted');
    if (accEl) accEl.textContent = session.accepted || 0;
    const rejEl = document.getElementById('db-karp-rejected');
    if (rejEl) rejEl.textContent = session.rejected || 0;
    const avgEl = document.getElementById('db-karp-avg-score');
    if (avgEl) avgEl.textContent = (session.avg_score || 0).toFixed(2);

    const alltime = karp.all_time || {};
    const alltimeEl = document.getElementById('db-karp-alltime');
    if (alltimeEl && alltime.total) {
        alltimeEl.textContent = `Total : ${alltime.total} hypotheses, ${alltime.accepted} acceptees, ${alltime.sessions || 0} sessions`;
    }

    const recent = karp.recent_hypotheses || [];
    const histEl = document.getElementById('db-karp-history');
    const decisionLabels = { accepted: 'GARDEE', rejected: 'REJETEE', pending: 'EN TEST' };
    if (histEl && recent.length > 0) {
        let html = '';
        for (const h of recent) {
            const decLabel = decisionLabels[h.decision] || 'REJETEE';
            const decCls = h.decision === 'accepted' ? 'term-green' : (h.decision === 'rejected' ? 'term-red' : 'term-amber');
            const scoreCls = h.score >= 0.6 ? 'term-green' : (h.score >= 0.3 ? 'term-amber' : 'term-red');
            // Clean hypothesis text: take first line, remove technical prefixes
            let hypText = (h.hypothesis || '\u2014').split('\n')[0];
            hypText = hypText.replace(/^Connexions trouv[ée]+es pour '([^']+)'.*$/, '$1');
            // Format timestamp
            let tsText = '';
            if (h.created_at) {
                const d = new Date(h.created_at);
                tsText = d.toLocaleDateString('fr-FR', {day:'2-digit', month:'2-digit'})
                    + ' ' + d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'});
            }
            html += `<div class="db-activity-entry">
                <span class="term-dim" style="min-width:90px">${tsText}</span>
                <span class="${decCls}">[${decLabel}]</span>
                <span class="db-activity-msg">${escapeHtml(hypText)}</span>
                <span class="${scoreCls}">${(h.score || 0).toFixed(2)}</span>
            </div>`;
        }
        safeHTML(histEl, html);
    } else if (histEl) {
        safeHTML(histEl, '<div class="term-dim">Aucune hypothese testee</div>');
    }

    const curWrap = document.getElementById('db-karp-current-wrap');
    if (curWrap) curWrap.style.display = karp.status === 'running' ? '' : 'none';
}

function _handleKarpathyHypothesisSSE(data) {
    const curWrap = document.getElementById('db-karp-current-wrap');
    const curHyp = document.getElementById('db-karp-current-hyp');
    if (curWrap) curWrap.style.display = '';
    if (curHyp) curHyp.textContent = data.hypothesis || '';

    const badge = document.getElementById('db-karp-live-badge');
    if (badge) {
        badge.textContent = 'RUNNING';
        badge.className = 'db-karp-badge running';
    }
}

function updateTzimtzum(tz) {
    const statusEl = document.getElementById('db-tz-status');
    if (statusEl) {
        const phase = tz.pressure_state || (tz.is_contracted ? 'contraction' : 'stable');
        const labels = { contraction: 'FOCUS PROFOND', stable: 'EQUILIBRE', expansion: 'VISION LARGE' };
        const cls = { contraction: 'term-red', stable: 'term-blue', expansion: 'term-green' };
        statusEl.textContent = labels[phase] || phase.toUpperCase();
        statusEl.className = cls[phase] || '';
    }

    const pressure = tz.pressure || 0;
    const pBar = document.getElementById('db-tz-pressure-bar');
    if (pBar) pBar.textContent = termProgress(pressure, 20);
    const pVal = document.getElementById('db-tz-pressure-val');
    if (pVal) pVal.textContent = Math.round(pressure * 100) + '%';

    const kavEl = document.getElementById('db-tz-kav-domain');
    if (kavEl) kavEl.textContent = tz.kav_domain ? ('Sujet en cours : ' + frDomain(tz.kav_domain)) : 'Pas de sujet particulier';

    const details = document.getElementById('db-tz-details');
    if (details) {
        let text = '';
        if (tz.is_contracted && tz.dormant_modules && tz.dormant_modules.length > 0) {
            const dormantFr = tz.dormant_modules.map(m => frSephirah(m) || m).join(', ');
            text += `Modules au repos : ${dormantFr}  `;
        }
        text += `${tz.contraction_count || 0} focus | ${tz.expansion_count || 0} expansions`;
        details.textContent = text;
    }
}

function updateOhr(ohr) {
    const pnimi = ohr.global_pnimi || 0;
    const makif = ohr.global_makif || 0;
    const masakh = ohr.masakh_strength || 0;

    const pBar = document.getElementById('db-ohr-pnimi-bar');
    if (pBar) safeText(pBar, termProgress(pnimi, 20));
    const pVal = document.getElementById('db-ohr-pnimi-val');
    if (pVal) safeText(pVal, (pnimi * 100).toFixed(0) + '%');

    const mBar = document.getElementById('db-ohr-makif-bar');
    if (mBar) safeText(mBar, termProgress(makif, 20));
    const mVal = document.getElementById('db-ohr-makif-val');
    if (mVal) safeText(mVal, (makif * 100).toFixed(0) + '%');

    const masakhBar = document.getElementById('db-ohr-masakh-bar');
    if (masakhBar) safeText(masakhBar, termProgress(masakh, 20));
    const masakhVal = document.getElementById('db-masakh-val');
    if (masakhVal) safeText(masakhVal, (masakh * 100).toFixed(0) + '%');

    const phaseEl = document.getElementById('db-ohr-phase');
    if (phaseEl) {
        const ohrPhaseLabels = { embryonic: 'Embryonnaire', growing: 'En croissance', mature: 'Mature', luminous: 'Lumineux' };
        safeText(phaseEl, ohrPhaseLabels[ohr.maturity_phase] || ohr.maturity_phase || '--');
    }
}

// ── Sod HaKli — 29 Dimensions ──────────────────────────────
function updateSodHakli(data) {
    if (!data) return;
    const dims = data.dimensions || [];
    const score = data.score_global;
    const olam = data.olam || '--';

    // Score global
    const scoreEl = document.getElementById('db-kli-score-val');
    if (scoreEl) {
        const pct = score != null ? (score * 100).toFixed(0) + '%' : '--';
        scoreEl.textContent = pct;
        if (score >= 0.7) scoreEl.className = 'term-bold term-green';
        else if (score >= 0.4) scoreEl.className = 'term-bold term-yellow';
        else scoreEl.className = 'term-bold term-red';
    }

    // Compteurs
    let ok = 0, partial = 0, absent = 0, na = 0;
    dims.forEach(d => {
        if (d.status === '\u2713') ok++;
        else if (d.status === '\u25b3') partial++;
        else if (d.status === '\u2717') absent++;
        else na++;
    });
    const set = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    set('db-kli-ok-count', ok);
    set('db-kli-partial-count', partial);
    set('db-kli-absent-count', absent);
    set('db-kli-na-count', na);
    set('db-kli-olam', olam);

    // Grille des 29 dimensions — 4 catégories
    const block = document.getElementById('db-kli-dims-block');
    if (!block) return;

    const categories = [
        { label: 'META-CONTEXTES', range: [1, 4] },
        { label: 'SEFIROT', range: [5, 13] },
        { label: 'PROCESSUS', range: [14, 16] },
        { label: 'STRUCTURES', range: [17, 29] },
    ];

    let lines = [];
    for (const cat of categories) {
        lines.push('\u2502 \x1b[1m' + cat.label + '\x1b[0m');
        // Use plain text since we're in a <pre>
        let catLine = '\u2502  ';
        for (const d of dims) {
            const num = parseInt(d.id, 10);
            if (num < cat.range[0] || num > cat.range[1]) continue;
            let icon = '\u25cb'; // empty circle
            let cls = 'term-dim';
            if (d.status === '\u2713') { icon = '\u25cf'; cls = 'term-green'; }
            else if (d.status === '\u25b3') { icon = '\u25d0'; cls = 'term-yellow'; }
            else if (d.status === '\u2717') { icon = '\u25cb'; cls = 'term-red'; }
            else { icon = '\u2500'; cls = 'term-dim'; }
            catLine += '<span class="' + cls + '" title="' + d.id + ' ' + d.name + ' [' + d.status + ']">' + icon + '</span> ';
        }
        lines.push(catLine);
    }
    safeHTML(block, lines.join('\n'));
}

function updateDaemonKarpathy(data) {
    const daemon = data.daemon || {};
    const karpathy = data.karpathy || {};

    const daemonEl = document.getElementById('db-daemon-status');
    if (daemonEl) {
        if (daemon.active) {
            let label = '\u25CF ACTIVE';
            if (daemon.pid) label += '  PID ' + daemon.pid;
            daemonEl.textContent = label;
            daemonEl.className = 'term-green';
        } else {
            daemonEl.textContent = '\u25CB INACTIVE';
            daemonEl.className = 'term-dim';
        }
    }

    const daemonSub = document.getElementById('db-daemon-sub');
    if (daemonSub && daemon.uptime != null) {
        const h = Math.floor(daemon.uptime / 3600);
        const m = Math.floor((daemon.uptime % 3600) / 60);
        daemonSub.textContent = `uptime ${h}h${m.toString().padStart(2, '0')}m`;
    }

    const karpathyEl = document.getElementById('db-karpathy-status');
    if (karpathyEl) {
        const statusMap = {
            'running': { text: '\u25CF RUNNING', cls: 'term-green' },
            'waiting': { text: '\u25CB WAITING', cls: 'term-dim' },
            'paused': { text: '\u25CF PAUSED', cls: 'term-red' },
        };
        const s = statusMap[karpathy.status] || { text: '\u25CB INACTIVE', cls: 'term-dim' };
        karpathyEl.textContent = s.text;
        karpathyEl.className = s.cls;
    }
    const karpNext = document.getElementById('db-karpathy-next');
    if (karpNext) {
        if (karpathy.detail) {
            karpNext.textContent = karpathy.detail;
        } else if (karpathy.next_launch) {
            karpNext.textContent = 'next ' + karpathy.next_launch;
        }
    }
    if (_canOverridePause('karpathy')) {
        _pauseState.karpathy = karpathy.status === 'paused';
        updatePauseButtons();
    }
}

function updateClustering(cl) {
    const wrap = document.getElementById('db-clustering-summary');
    const empty = document.getElementById('db-clustering-empty');
    if (!cl) {
        if (wrap) wrap.style.display = 'none';
        if (empty) empty.style.display = 'block';
        return;
    }
    if (wrap) wrap.style.display = 'block';
    if (empty) empty.style.display = 'none';

    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    set('db-cl-concepts', cl.n_concepts || 0);
    set('db-cl-kab', cl.n_clusters_kab || 0);
    set('db-cl-ml', cl.n_clusters_ml || 0);
    set('db-cl-disagree', cl.n_disagreements || 0);
    const ratio = cl.agreement_ratio || 0;
    set('db-cl-ratio', (ratio * 100).toFixed(1) + '%');

    if (cl.run_date) {
        const d = new Date(cl.run_date);
        set('db-cl-date', d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'}));
    }

    const tbody = document.getElementById('db-cl-tbody');
    if (tbody && cl.top) {
        tbody.innerHTML = '';
        for (const r of cl.top) {
            const typeLabel = r.type === 'kab_close_ml_far' ? 'Kabbale rapproche' : 'ML rapproche';
            const a = _humanizeConceptName(r.a);
            const b = _humanizeConceptName(r.b);
            const tr = document.createElement('tr');
            tr.innerHTML = `<td title="${escapeHtml(r.a)}">${escapeHtml(a)}</td><td title="${escapeHtml(r.b)}">${escapeHtml(b)}</td>`
                + `<td>${r.kab.toFixed(2)}</td><td>${r.ml.toFixed(2)}</td>`
                + `<td class="term-amber">${r.gap.toFixed(2)}</td>`
                + `<td>${typeLabel}</td>`;
            tbody.appendChild(tr);
        }
    }
}

// ─── Pause / Go ─────────────────────────────────────────────

const _pauseState = { hitbonenut: false, karpathy: false };
// Cooldown: after a manual toggle, ignore SSE/polling overrides for 6 seconds
const _pauseCooldown = { hitbonenut: 0, karpathy: 0 };
const PAUSE_COOLDOWN_MS = 6000;

function togglePause(target) {
    const btn = document.getElementById(
        target === 'hitbonenut' ? 'db-hitb-pause-btn' : 'db-karp-pause-btn'
    );
    // Immediate visual feedback
    if (btn) {
        btn.textContent = '[...]';
        btn.disabled = true;
    }
    const isPaused = _pauseState[target];
    const endpoint = isPaused ? `/api/go/${target}` : `/api/pause/${target}`;
    apiFetch(endpoint, { method: 'POST' })
        .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(d => {
            _pauseState[target] = d.paused;
            _pauseCooldown[target] = Date.now() + PAUSE_COOLDOWN_MS;
            updatePauseButtons();
            if (btn) btn.disabled = false;
            // Refresh daemon state
            apiFetch('/api/daemon/state').then(r => r.json()).then(data => {
                if (data.hitbonenut) updateHitbonenut(data.hitbonenut);
                if (data.karpathy) {
                    updateKarpathyLive(data.karpathy);
                    updateDaemonKarpathy(data);
                }
            }).catch(() => {});
        })
        .catch(e => {
            console.error('Pause toggle error:', e);
            // Restore button on error
            if (btn) {
                btn.textContent = isPaused ? '[GO]' : '[PAUSE]';
                btn.disabled = false;
            }
        });
}

function _canOverridePause(target) {
    return Date.now() > (_pauseCooldown[target] || 0);
}

function updatePauseButtons() {
    const hitbBtn = document.getElementById('db-hitb-pause-btn');
    if (hitbBtn) {
        hitbBtn.textContent = _pauseState.hitbonenut ? '[GO]' : '[PAUSE]';
        hitbBtn.title = _pauseState.hitbonenut ? 'Reprendre Hitbonenut' : 'Pause Hitbonenut';
        hitbBtn.classList.toggle('is-paused', _pauseState.hitbonenut);
    }
    const karpBtn = document.getElementById('db-karp-pause-btn');
    if (karpBtn) {
        karpBtn.textContent = _pauseState.karpathy ? '[GO]' : '[PAUSE]';
        karpBtn.title = _pauseState.karpathy ? 'Reprendre Karpathy' : 'Pause Karpathy';
        karpBtn.classList.toggle('is-paused', _pauseState.karpathy);
    }
}

// ─── Tanya — Double Ame ────────────────────────────────────

function updateTanya(tanya) {
    const block = document.getElementById('db-tanya-block');
    if (!block) return;
    if (!tanya || !tanya.soul_category) {
        safeHTML(block, '\u2502 Pas de donnees');
        return;
    }

    const categoryLabels = {
        rasha_she_eino_gamur: 'Domine par l\'inertie', am_haretz: 'Debutant',
        beinoni: 'Equilibre', tzaddik_nimna: 'Presque juste', tzaddik_nigleh: 'Juste revele'
    };
    const categoryColors = {
        rasha_she_eino_gamur: 'term-red', am_haretz: 'term-amber',
        beinoni: 'term-amber', tzaddik_nimna: 'term-green', tzaddik_nigleh: 'term-green'
    };
    const dominantLabels = { neutral: 'Equilibre', elokit: 'Creativite domine', behamit: 'Prudence domine' };
    const dominantColors = { neutral: 'term-dim', elokit: 'term-green', behamit: 'term-red' };
    const atzvutLabels = { simcha: '\u25CF Joie', neutral: '\u25CB Neutre', atzvut: '\u25CF Fatigue' };
    const atzvutColors = { simcha: 'term-green', neutral: 'term-dim', atzvut: 'term-red' };
    const trendSymbols = { rising: '\u2191', stable: '\u2192', falling: '\u2193' };
    const trendColors = { rising: 'term-green', stable: 'term-dim', falling: 'term-red' };

    const cat = tanya.soul_category;
    const dom = tanya.dominant_soul || 'neutral';
    const atz = tanya.atzvut_state || 'neutral';
    const elokit = tanya.ratio_elokit || 0;
    const behamit = tanya.ratio_behamit || 0;
    const nogah = tanya.nogah_ratio || 0;
    const dira = tanya.dira_penetration || 0;
    const lev = tanya.levushim_avg || {};
    const bt = tanya.beinoni_tracker || {};

    let t = '';
    t += '\u2502 Profil         <span class="' + (categoryColors[cat] || 'term-amber') + '">' + (categoryLabels[cat] || cat) + '</span>\n';
    t += '\u2502 Tendance       <span class="' + (dominantColors[dom] || 'term-dim') + '">' + (dominantLabels[dom] || dom) + '</span>\n';
    t += '\u2502 Humeur         <span class="' + (atzvutColors[atz] || 'term-dim') + '">' + (atzvutLabels[atz] || atz) + '</span>\n';
    t += '\u2502\n';
    t += '\u2502 Creativite (envie de produire)  ' + termProgress(elokit, 20) + ' ' + (elokit * 100).toFixed(0) + '%\n';
    t += '\u2502 Prudence (envie de verifier)    ' + termProgress(behamit, 20) + ' ' + (behamit * 100).toFixed(0) + '%\n';
    t += '\u2502\n';
    t += '\u2502 <span class="term-dim">\u2500\u2500\u2500 Zone grise \u2500\u2500\u2500 Ce qui n\'est ni bon ni mauvais, a trier</span>\n';
    t += '\u2502 A trier        ' + termProgress(nogah, 20) + ' ' + (nogah * 100).toFixed(0) + '%\n';
    t += '\u2502 Vitesse de tri ' + (tanya.birur_rate || 0).toFixed(2) + '  Tries effectues : ' + (tanya.total_birurims || 0) + '\n';
    t += '\u2502\n';
    t += '\u2502 <span class="term-dim">\u2500\u2500\u2500 Ancrage \u2500\u2500\u2500 Capacite a appliquer dans le reel</span>\n';
    t += '\u2502 Ancrage        ' + termProgress(dira, 20) + ' ' + (dira * 100).toFixed(0) + '%\n';
    t += '\u2502 Applications   ' + (tanya.dira_count || 0) + '\n';
    t += '\u2502\n';
    t += '\u2502 <span class="term-dim">\u2500\u2500\u2500 Modes d\'expression \u2500\u2500\u2500 Comment la connaissance s\'exprime</span>\n';
    t += '\u2502 Pensee         ' + termProgress(lev.machshava || 0, 20) + ' ' + ((lev.machshava || 0) * 100).toFixed(0) + '%\n';
    t += '\u2502 Communication  ' + termProgress(lev.dibour || 0, 20) + ' ' + ((lev.dibour || 0) * 100).toFixed(0) + '%\n';
    t += '\u2502 Action         ' + termProgress(lev.maase || 0, 20) + ' ' + ((lev.maase || 0) * 100).toFixed(0) + '%\n';
    t += '\u2502\n';
    t += '\u2502 <span class="term-dim">\u2500\u2500\u2500 Suivi de l\'equilibre</span>\n';
    t += '\u2502 Part creative  ' + termProgress(bt.elokit_ratio || 0, 20) + ' ' + ((bt.elokit_ratio || 0) * 100).toFixed(0) + '%\n';
    const trendLabels = { rising: 'EN HAUSSE', stable: 'STABLE', falling: 'EN BAISSE' };
    const trend = bt.trend || 'stable';
    t += '\u2502 Evolution      <span class="' + (trendColors[trend] || 'term-dim') + '">' + (trendSymbols[trend] || '\u2192') + ' ' + (trendLabels[trend] || 'STABLE') + '</span>\n';
    if (bt.regression) t += '\u2502 <span class="term-red">\u26A0 Regression detectee</span>\n';
    if (bt.elevation) t += '\u2502 <span class="term-green">\u2191 Progression en cours</span>\n';

    safeHTML(block, t);
}

// ─── Conditions de Montee ──────────────────────────────────

function updateConditions(soul) {
    const block = document.getElementById('db-conditions-block');
    if (!block) return;

    const cond = soul.conditions_next;
    if (!cond) {
        safeHTML(block, '\u2502 Pas de donn\u00e9es');
        return;
    }

    if (cond.reached_maximum) {
        safeHTML(block, '\u2502 <span class="term-green">\u2713 Niveau maximum atteint — unite complete</span>');
        return;
    }

    const currentFr = frSoul(soul.level);
    const nextFr = frSoul(cond.next_level);
    const missing = cond.missing || [];

    let t = '';
    t += '\u2502 Niveau actuel : <span class="term-amber">' + escapeHtml(currentFr) + '</span>\n';
    t += '\u2502 Prochain niveau : <span class="term-blue">' + escapeHtml(nextFr) + '</span>\n';
    t += '\u2502\n';

    if (cond.ready || missing.length === 0) {
        t += '\u2502 <span class="term-green">[\u2713] PRET A MONTER</span>';
    } else {
        t += '\u2502 <span class="term-dim">Il manque :</span>\n';
        for (const m of missing) {
            t += '\u2502 <span class="term-red">\u2717 ' + escapeHtml(m) + '</span>\n';
        }
    }

    safeHTML(block, t);
}

// ─── Sefirat Ha'Omer ───────────────────────────────────────

function fetchOmer() {
    apiFetch('/api/omer/today').then(r => r.json()).then(data => {
        _omerData = data;
        updateOmer(data);
        updateOmerBadge(data);
        if (_dashboardData) updateStatusLine(_dashboardData);
    }).catch(() => {});
}

function updateOmer(data) {
    const block = document.getElementById('db-omer-block');
    if (!block) return;

    if (!data || !data.active) {
        safeHTML(block, '\u2502 <span class="term-dim">Hors periode du cycle de raffinement</span>');
        return;
    }

    const day = data.day || 0;
    const week = data.week || 0;
    const dayInWeek = data.day_in_week || 0;
    const primaryFr = frSephirah(data.primary) || data.primary || '';
    const secondaryFr = frSephirah(data.secondary) || data.secondary || '';
    const boosts = data.module_boosts || {};

    let t = '';
    t += '\u2502 Jour ' + day + '/49\n';
    t += '\u2502 ' + termProgress(day / 49, 40) + ' ' + Math.round(day / 49 * 100) + '%\n';
    t += '\u2502\n';
    t += '\u2502 Qualite de la semaine : <span class="term-amber">' + escapeHtml(primaryFr) + '</span>\n';
    t += '\u2502 Qualite du jour :       <span class="term-amber">' + escapeHtml(secondaryFr) + '</span>\n';
    t += '\u2502 <span class="term-dim">Combinaison : ' + escapeHtml(secondaryFr) + ' dans ' + escapeHtml(primaryFr) + '</span>\n';

    const allBoosts = [];
    for (const mod of Object.keys(boosts)) {
        for (const [param, delta] of Object.entries(boosts[mod])) {
            allBoosts.push([mod, param, delta]);
        }
    }
    if (allBoosts.length > 0) {
        t += '\u2502\n';
        t += '\u2502 <span class="term-dim">Effets du jour sur le systeme :</span>\n';
        for (const [mod, param, delta] of allBoosts) {
            const sign = delta >= 0 ? '+' : '';
            const cls = delta >= 0 ? 'term-green' : 'term-red';
            const modFr = frModule(mod);
            const paramFr = frParam(param);
            t += '\u2502   ' + escapeHtml(modFr) + ' \u2014 ' + escapeHtml(paramFr).padEnd(22) + ' <span class="' + cls + '">' + sign + delta.toFixed(3) + '</span>\n';
        }
    }

    safeHTML(block, t);
}

// ─── Status Line ────────────────────────────────────────────

function updateStatusLine(data) {
    const el = document.getElementById('status-line');
    if (!el || !data) return;
    const daemon = data.daemon && data.daemon.active ? '\u25CF' : '\u25CB';
    const soulFr = (data.soul && data.soul.level) ? frSoul(data.soul.level) : '--';
    const nitz = (data.nitzotzot && data.nitzotzot.count != null) ? data.nitzotzot.count : '--';
    const zivLabels = { active: '\u25CF', partial: '\u25D0', blocked: '\u25CB' };
    const ziv = (data.zivvug && data.zivvug.state) ? (zivLabels[data.zivvug.state] || '\u25CB') : '\u25CB';
    const comp = (data.soul && data.soul.competence_score != null) ? ((data.soul.competence_score * 100).toFixed(0) + '%') : '--';
    const hitb = (data.hitbonenut && data.hitbonenut.questions_today) || 0;
    const time = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    el.textContent = daemon + ' Gardien \u2502 ' + soulFr + ' \u2502 Puissance:' + comp + ' \u2502 \u2726' + nitz + '/288 \u2502 Synergie:' + ziv + ' \u2502 Questions:' + hitb + ' \u2502 ' + time;
}

// ═══════════════════════════════════════════════════════════
//  NEW: Summaries, Inventory, Sentiers, Provider, Messages
// ═══════════════════════════════════════════════════════════

// ── Narrative Labels ───────────────────────────────────────

function narrativeLabel(value) {
    if (value >= 0.9) return { text: 'Exemplaire', cls: 'n-exemplary' };
    if (value >= 0.7) return { text: 'Solide', cls: 'n-solid' };
    if (value >= 0.5) return { text: 'Stable', cls: 'n-stable' };
    if (value >= 0.3) return { text: 'Fragile', cls: 'n-fragile' };
    return { text: 'Critique', cls: 'n-critical' };
}

function formatBigNumber(n) {
    if (n >= 100000) return (n / 1000).toFixed(0) + 'K';
    if (n >= 10000) return (n / 1000).toFixed(1) + 'K';
    if (n >= 1000) return n.toLocaleString('fr-FR');
    return String(n);
}

// ── Section Summaries ──────────────────────────────────────

function updateAllSummaries(data) {
    // Tree summary
    const mods = data.modules || {};
    const online = Object.values(mods).filter(m => m.status === 'online').length;
    const total = Object.keys(mods).length;
    const offline = Object.entries(mods).filter(([k, m]) => m.status !== 'online').map(([k]) => frSephirah(k) || k);
    const treeSum = document.getElementById('grp-tree-summary');
    if (treeSum) {
        let text = `<span class="${online === total ? 'term-green' : 'term-amber'}">${online}/${total} actifs</span>`;
        if (offline.length > 0) text += ` \u2502 ${offline.join(', ')} en attente`;
        safeHTML(treeSum, text);
    }

    // Learning summary
    const hitb = data.hitbonenut || {};
    const karp = data.karpathy || {};
    const learnSum = document.getElementById('grp-learning-summary');
    if (learnSum) {
        const hitbStatus = hitb.status === 'running' ? '\u25CF' : (hitb.status === 'paused' ? '\u25A0' : '\u25CB');
        const karpStatus = karp.status === 'running' ? '\u25CF' : '\u25CB';
        const qToday = hitb.questions_today || 0;
        safeHTML(learnSum, `Entrainement:${hitbStatus} Forge:${karpStatus} \u2502 ${qToday} questions aujourd'hui`);
    }

    // Forces (Cour Interieure) summary
    const partz = data.partzufim || {};
    const matureCount = Object.values(partz).filter(p => p.mochin_state === 'gadlut').length;
    const totalPartz = Object.keys(partz).length;
    const zState = (data.zivvug || {}).state || 'blocked';
    const zivLabels = { active: 'Synergie active', partial: 'Synergie partielle', blocked: 'Synergie bloquee' };
    const dom = (data.tanya || {}).dominant_soul || 'neutral';
    const domLabels = { neutral: 'Equilibre', elokit: 'Creativite domine', behamit: 'Prudence domine' };
    const forcesSum = document.getElementById('grp-forces-summary');
    if (forcesSum) {
        safeHTML(forcesSum, `${matureCount}/${totalPartz} matures \u2502 ${zivLabels[zState] || zState} \u2502 ${domLabels[dom] || dom}`);
    }

    // Health (Piliers) summary
    const gov = data.governors || {};
    const harmony = gov.harmony || 0;
    const weakest = gov.weakest || '--';
    const weakFr = { teli: 'Structure', galgal: 'Cycles', lev: 'Vitalite' };
    const healthSum = document.getElementById('grp-health-summary');
    if (healthSum) {
        const hLabel = narrativeLabel(harmony);
        safeHTML(healthSum, `Harmonie: <span class="db-narrative ${hLabel.cls}">${(harmony * 100).toFixed(0)}% ${hLabel.text}</span> \u2502 Maillon faible: ${weakFr[weakest] || weakest}`);
    }

    // Progress summary
    const soul = data.soul || {};
    const cond = soul.conditions_next || {};
    const missing = (cond.missing || []).length;
    const progressSum = document.getElementById('grp-progress-summary');
    if (progressSum) {
        if (cond.reached_maximum) {
            safeHTML(progressSum, '<span class="term-green">\u2713 Niveau maximum atteint</span>');
        } else if (cond.ready) {
            safeHTML(progressSum, '<span class="term-green">\u2713 PRET A MONTER</span>');
        } else {
            safeHTML(progressSum, `${frSoul(soul.level)} \u2502 ${missing} condition${missing > 1 ? 's' : ''} manquante${missing > 1 ? 's' : ''}`);
        }
    }

    // Sentiers summary
    const sentiers = data.sentiers || [];
    const sentiersSum = document.getElementById('grp-sentiers-summary');
    if (sentiersSum) {
        safeHTML(sentiersSum, `${sentiers.length} chemins entre les modules`);
    }

    // Maturity summary — updated by updateSodHakli separately

    // Discoveries summary
    const cl = data.clustering;
    const discSum = document.getElementById('grp-discoveries-summary');
    if (discSum) {
        if (cl) {
            safeHTML(discSum, `${cl.n_concepts || 0} concepts \u2502 ${cl.n_disagreements || 0} desaccords \u2502 Accord: ${((cl.agreement_ratio || 0) * 100).toFixed(0)}%`);
        } else {
            safeHTML(discSum, 'En attente du premier run');
        }
    }
}

// ── Messages from API ──────────────────────────────────────

function updateMessages(data) {
    // Zivvug message
    const zMsg = document.getElementById('db-zivvug-message');
    if (zMsg) {
        const msg = (data.zivvug || {}).message;
        if (msg) {
            zMsg.textContent = msg;
            zMsg.style.display = 'block';
        } else {
            zMsg.style.display = 'none';
        }
    }

    // Governors message
    const gMsg = document.getElementById('db-gov-message');
    if (gMsg) {
        const msg = (data.governors || {}).message;
        if (msg) {
            gMsg.textContent = msg;
            gMsg.style.display = 'block';
        } else {
            gMsg.style.display = 'none';
        }
    }

    // Tanya explanation
    const tMsg = document.getElementById('db-tanya-message');
    if (tMsg) {
        const msg = (data.tanya || {}).explanation;
        if (msg) {
            tMsg.textContent = msg;
            tMsg.style.display = 'block';
        } else {
            tMsg.style.display = 'none';
        }
    }
}

// ── Clustering n_disagreements ─────────────────────────────

function updateClusteringExtra(cl) {
    const el = document.getElementById('db-cl-disagree');
    if (el && cl) safeText(el, cl.n_disagreements || 0);
}

// ── Inventory ──────────────────────────────────────────────

function fetchInventory() {
    const set = (id, val) => { const el = document.getElementById(id); if (el) safeText(el, formatBigNumber(val)); };

    Promise.all([
        apiFetch('/api/memory/stats').then(r => r.json()).catch(() => ({})),
        apiFetch('/api/intentions').then(r => r.json()).catch(() => ({ count: 0 })),
        apiFetch('/api/sifrei-yesod/stats').then(r => r.json()).catch(() => ({ global: {} })),
        apiFetch('/api/dashboard/counts').then(r => r.json()).catch(() => ({})),
    ]).then(([mem, intent, sifrei, counts]) => {
        const g = sifrei.global || {};

        set('db-inv-memories', mem.total || 0);
        set('db-inv-concepts', g.concepts || 0);
        set('db-inv-assertions', g.assertions || 0);
        set('db-inv-intentions', intent.count || 0);

        // DB counts from dedicated endpoint
        set('db-inv-claims', counts.causal_claims || 0);
        set('db-inv-tensions', counts.tensions || 0);
        set('db-inv-questions', counts.hitbonenut_questions || 0);
        set('db-inv-novelty', counts.novelty_assessments || 0);
        set('db-inv-principles', counts.hitbonenut_principles || 0);
        set('db-inv-analogies', counts.analogies || 0);
        set('db-inv-explorations', counts.explorations || 0);
        set('db-inv-selfmodel', counts.selfmodel_states || 0);

        // Update inventory summary
        const invSum = document.getElementById('grp-inventory-summary');
        if (invSum) {
            safeHTML(invSum, `${formatBigNumber(mem.total || 0)} souvenirs \u2502 ${formatBigNumber(g.concepts || 0)} concepts \u2502 ${formatBigNumber(counts.causal_claims || 0)} liens causaux`);
        }
    });
}

// ── Sentiers ───────────────────────────────────────────────

function renderSentiers(sentiers) {
    const grid = document.getElementById('db-sentiers-grid');
    if (!grid || !sentiers || sentiers.length === 0) return;

    const html = sentiers.map(s => {
        const src = frSephirah(s.source) || s.source;
        const tgt = frSephirah(s.target) || s.target;
        const prog = s.program || '?';
        return `<div class="db-sentier-item">
            <span class="db-sentier-letter">${s.letter || '?'}</span>
            <span class="db-sentier-path">${escapeHtml(src)} \u2194 ${escapeHtml(tgt)}</span>
            <span class="db-sentier-prog">${escapeHtml(prog)}</span>
        </div>`;
    }).join('');

    safeHTML(grid, html);
}

// ── Provider Info ──────────────────────────────────────────

function fetchProvider() {
    apiFetch('/api/provider/status').then(r => r.json()).then(data => {
        const el = document.getElementById('db-provider-text');
        if (el) {
            const profile = data.profile || '?';
            const embOk = data.embedding && data.embedding.available;
            safeText(el, profile + (embOk ? ' \u2713' : ' \u2717'));
        }
    }).catch(() => {});
}

// ── Omer in Hero Badge ─────────────────────────────────────

function updateOmerBadge(data) {
    const badge = document.getElementById('db-omer-badge');
    const text = document.getElementById('db-omer-badge-text');
    if (!badge || !text) return;

    if (data && data.active) {
        badge.style.display = '';
        safeText(text, 'Jour ' + data.day + '/49 \u2014 ' + (data.combination_hebrew || ''));
    } else {
        badge.style.display = 'none';
    }
}

// Hook into existing fetchOmer
const _origFetchOmer = typeof fetchOmer === 'function' ? fetchOmer : null;
