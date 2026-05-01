/* ═══════════════════════════════════════════════════════════
   avatars.js — SSE + interactions pour la page Personnages
   ═══════════════════════════════════════════════════════════ */

(function() {
    'use strict';

    // ─── Mapping personnage → composant pour le detail ────
    var COMPOSANTS = {
        strategic: {label: 'Strategic', api: 'configurationim', key: 'strategic'},
        generative:        {label: 'Generative',        api: 'configurationim', key: 'generative'},
        structuring:        {label: 'Structuring',        api: 'configurationim', key: 'structuring'},
        execution:  {label: 'Execution',  api: 'configurationim', key: 'execution'},
        interface_config:       {label: 'Interface',       api: 'configurationim', key: 'interface_config'},
        mikhael:     {label: 'Mikhael',     api: 'malakhim',  key: 'mikhael'},
        gabriel:     {label: 'Gabriel',     api: 'malakhim',  key: 'gabriel'},
        raphael:     {label: 'Raphael',     api: 'malakhim',  key: 'raphael'},
        uriel:       {label: 'Uriel',       api: 'malakhim',  key: 'uriel'},
        metatron:    {label: 'Metatron',    api: 'malakhim',  key: 'metatron'},
        memuneh:     {label: 'Memuneh',     api: 'malakhim',  key: 'memuneh'},
        samael:      {label: 'Samael',      api: 'malakhim',  key: 'samael'},
        sofer:       {label: 'Sofer',       api: 'sifrei',    key: 'sofer'},
        nefesh_habehamit: {label: 'Nefesh HaBehamit', api: 'tanya', key: 'behamit'},
        nefesh_behamit: {label: 'Nefesh HaBehamit', api: 'tanya', key: 'behamit'},
        beinoni:     {label: 'Le Beinoni',  api: 'tanya',     key: 'beinoni'},
        nefesh_haelokit: {label: 'Nefesh HaElokit', api: 'tanya', key: 'elokit'},
        nefesh_elokit: {label: 'Nefesh HaElokit', api: 'tanya', key: 'elokit'},
        daemon:      {label: 'Le Daemon',   api: 'daemon',    key: 'daemon'},
        meditant:    {label: 'Le Meditant', api: 'self-study', key: 'self-study'},
        kategor:     {label: 'Le Kategor',  api: 'malakhim',  key: 'kategor'}
    };

    // ─── Detail overlay ───────────────────────────────────
    var overlay = document.getElementById('av-detail-overlay');
    var detailContent = document.getElementById('av-detail-content');
    var closeBtn = document.getElementById('av-detail-close');

    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            overlay.style.display = 'none';
        });
    }

    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) overlay.style.display = 'none';
        });
    }

    // Escape key closes overlay
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && overlay && overlay.style.display !== 'none') {
            overlay.style.display = 'none';
        }
    });

    // ─── Detail link handlers ─────────────────────────────
    document.querySelectorAll('.av-card-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var id = this.getAttribute('data-detail');
            showDetail(id);
        });
    });

    function showDetail(id) {
        if (!overlay || !detailContent) return;
        var comp = COMPOSANTS[id];
        var perso = window.PERSONNAGES && window.PERSONNAGES[id];
        if (!comp) {
            detailContent.textContent = 'Personnage inconnu: ' + id;
            overlay.style.display = 'flex';
            return;
        }

        detailContent.textContent = 'Chargement ' + comp.label + '...';
        overlay.style.display = 'flex';

        // Fetch status from API
        apiFetch('/api/status')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var lines = [];
                var sep = '\u2502 ';

                // ── Header ──
                lines.push(sep + comp.label);
                if (perso && perso.nom_hebreu) {
                    lines.push(sep + perso.nom_hebreu);
                }
                if (perso && perso.role) {
                    lines.push(sep + perso.role);
                }
                lines.push('\u2502');

                // ── Description accessible (3 niveaux) ──
                if (perso && perso.detail) {
                    var d = perso.detail;
                    lines.push(sep + '\u250c En clair');
                    wrapLines(d.en_clair, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                    lines.push('\u2502');
                    lines.push(sep + '\u250c Dans le systeme');
                    wrapLines(d.dans_le_systeme, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                    lines.push('\u2502');
                    lines.push(sep + '\u250c Tradition');
                    wrapLines(d.tradition, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                } else if (perso && perso.description) {
                    wrapLines(perso.description, 58).forEach(function(l) {
                        lines.push(sep + l);
                    });
                }

                // ── Donnees temps reel ──
                lines.push('\u2502');
                lines.push(sep + '\u2500\u2500 Donnees temps reel \u2500\u2500');

                if (comp.api === 'configurationim' && data.configurationim) {
                    var p = data.configurationim[comp.key];
                    if (p) {
                        lines.push(sep + 'Overall   ' + fmt(p.overall));
                        lines.push(sep + 'Mochin    ' + (p.mochin_state || '--'));
                        lines.push(sep + 'Orient.   ' + (p.orientation || '--'));
                        if (p.faculties) {
                            lines.push('\u2502');
                            lines.push(sep + 'Facultes :');
                            Object.keys(p.faculties).forEach(function(k) {
                                lines.push(sep + '  ' + pad(k, 10) + bar(p.faculties[k]) + ' ' + fmt(p.faculties[k]));
                            });
                        }
                    } else {
                        lines.push(sep + 'Composant ' + comp.api + '.' + comp.key);
                        lines.push(sep + 'Etat      en attente de donnees');
                    }
                } else if (comp.api === 'daemon') {
                    lines.push(sep + 'Status    ' + (data.daemon_status || '--'));
                    if (data.daemon_tasks_today !== undefined) {
                        lines.push(sep + 'Taches    ' + data.daemon_tasks_today + ' aujourd\'hui');
                    }
                } else if (comp.api === 'tanya' && data.tanya) {
                    var t = data.tanya;
                    if (comp.key === 'beinoni' && t.beinoni) {
                        lines.push(sep + 'Profil    ' + (t.beinoni.state || '--'));
                        lines.push(sep + 'Tendance  ' + (t.beinoni.trend || '--'));
                    } else {
                        lines.push(sep + 'Etat ame  ' + (t.soul_state || '--'));
                    }
                } else {
                    lines.push(sep + 'Composant ' + comp.api + '.' + comp.key);
                    lines.push(sep + 'Etat      en attente de connexion');
                }

                lines.push('\u2502');
                lines.push(sep + 'Derniere maj: ' + new Date().toLocaleTimeString('fr-FR'));
                detailContent.textContent = lines.join('\n');
            })
            .catch(function(err) {
                // Show description even if API fails
                var lines = [];
                var sep = '\u2502 ';
                lines.push(sep + comp.label);
                if (perso && perso.detail) {
                    var d = perso.detail;
                    lines.push('\u2502');
                    lines.push(sep + '\u250c En clair');
                    wrapLines(d.en_clair, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                    lines.push('\u2502');
                    lines.push(sep + '\u250c Dans le systeme');
                    wrapLines(d.dans_le_systeme, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                    lines.push('\u2502');
                    lines.push(sep + '\u250c Tradition');
                    wrapLines(d.tradition, 56).forEach(function(l) {
                        lines.push(sep + '\u2502 ' + l);
                    });
                    lines.push(sep + '\u2514');
                }
                lines.push('\u2502');
                lines.push(sep + 'API indisponible');
                detailContent.textContent = lines.join('\n');
            });
    }

    function wrapLines(text, maxLen) {
        if (!text) return ['--'];
        var words = text.split(' ');
        var lines = [];
        var current = '';
        for (var i = 0; i < words.length; i++) {
            var test = current ? current + ' ' + words[i] : words[i];
            if (test.length > maxLen && current) {
                lines.push(current);
                current = words[i];
            } else {
                current = test;
            }
        }
        if (current) lines.push(current);
        return lines;
    }

    function fmt(v) {
        if (v === null || v === undefined) return '--';
        if (typeof v === 'number') return v.toFixed(2);
        return String(v);
    }

    function pad(s, n) {
        s = String(s);
        while (s.length < n) s += ' ';
        return s;
    }

    function bar(v) {
        if (typeof v !== 'number') return '[----------]';
        var n = Math.round(v * 10);
        var filled = '';
        var empty = '';
        for (var i = 0; i < n; i++) filled += '\u2588';
        for (var j = n; j < 10; j++) empty += '\u2591';
        return '[' + filled + empty + ']';
    }

    // ─── SSE for live updates ─────────────────────────────
    // Connect to dashboard stream if available
    function connectSSE() {
        if (typeof EventSource === 'undefined') return;
        try {
            var es = new EventSource('/api/dashboard/stream');
            es.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    updateCardsFromStatus(data);
                } catch(e) { /* ignore parse errors */ }
            };
            es.onerror = function() {
                es.close();
                // Reconnect after 5s
                setTimeout(connectSSE, 5000);
            };
        } catch(e) { /* SSE not available */ }
    }

    function updateCardsFromStatus(data) {
        // Update Configurationim states
        if (data.configurationim) {
            ['strategic', 'generative', 'structuring', 'execution', 'interface_config'].forEach(function(name) {
                var p = data.configurationim[name];
                var card = document.getElementById('card-' + name);
                if (!p || !card) return;
                if (p.mochin_state) card.dataset.mochin = p.mochin_state;
                if (p.overall > 0.6) {
                    card.dataset.etat = 'active';
                } else {
                    card.dataset.etat = 'idle';
                }
            });
        }

        // Update daemon
        if (data.daemon_status) {
            var dc = document.getElementById('card-daemon');
            if (dc) {
                dc.dataset.etat = data.daemon_status === 'RUNNING' ? 'active' : 'idle';
            }
        }

        // Update CrossCoupling line
        if (data.cross_coupling) {
            var line = document.getElementById('cross_coupling-line');
            if (line) {
                if (data.cross_coupling.state === 'ACTIVE') {
                    line.style.background = 'linear-gradient(90deg, transparent, #ffcc00, transparent)';
                    line.style.height = '3px';
                } else {
                    line.style.background = 'linear-gradient(90deg, transparent, #555, transparent)';
                    line.style.height = '1px';
                }
            }
        }
    }

    // ─── Initial load from /api/status ────────────────────
    apiFetch('/api/status')
        .then(function(r) { return r.json(); })
        .then(updateCardsFromStatus)
        .catch(function() { /* silent */ });

    // Start SSE
    connectSSE();

})();
