// ============================================================
// BUILD MODULE
// Build page hierarchy, modal, and PDF generation
// ============================================================

(function () {
    const BuildMixin = {
        renderBuildHierarchy: async function () {
            const container = document.getElementById('build-grid');
            if (!container) return;

            if (!this.state.hierarchy || this.state.hierarchy.length === 0) {
                try {
                    const res = await fetch('/api/hierarchy');
                    const data = await res.json();
                    this.state.hierarchy = data.hierarchy || [];
                } catch (e) {
                    console.error('Failed to load hierarchy:', e);
                    container.innerHTML = '<p style="color:var(--text-muted);">Failed to load structure.</p>';
                    return;
                }
            }

            if (!this.state.buildSelection) {
                this.state.buildSelection = {};
                this.state.hierarchy.forEach((ch, chIdx) => {
                    this.state.buildSelection[chIdx] = {};
                    (ch.pages || []).forEach((pg, pgIdx) => {
                        this.state.buildSelection[chIdx][pgIdx] = true;
                    });
                });
            }

            container.innerHTML = '';
            this.state.hierarchy.forEach((chapter, chIdx) => {
                const pages = chapter.pages || [];
                const selectedCount = pages.filter((_, pgIdx) => this.state.buildSelection[chIdx]?.[pgIdx]).length;
                const allSelected = selectedCount === pages.length && pages.length > 0;

                const rowEl = document.createElement('div');
                rowEl.className = 'build-row';
                const labelEl = document.createElement('div');
                labelEl.className = 'build-row-label';
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'btn btn-ghost btn-sm';
                toggleBtn.textContent = allSelected ? 'Deselect' : 'Select';
                toggleBtn.onclick = (e) => { e.stopPropagation(); this.toggleBuildChapter(chIdx); };
                const titleSpan = document.createElement('span');
                titleSpan.textContent = `Ch ${chIdx + 1}: ${chapter.title || 'Untitled'}`;
                labelEl.appendChild(titleSpan);
                labelEl.appendChild(toggleBtn);
                rowEl.appendChild(labelEl);

                const pagesEl = document.createElement('div');
                pagesEl.className = 'build-row-pages';
                pages.forEach((page, pgIdx) => {
                    const isSelected = this.state.buildSelection[chIdx]?.[pgIdx];
                    const cell = document.createElement('div');
                    cell.className = 'build-cell' + (isSelected ? ' selected' : '');
                    cell.title = page.title || `Page ${pgIdx + 1}`;
                    cell.textContent = pgIdx + 1;
                    cell.dataset.chapterIdx = chIdx;
                    cell.dataset.pageIdx = pgIdx;
                    cell.onclick = () => this.toggleBuildPage(chIdx, pgIdx);
                    pagesEl.appendChild(cell);
                });

                rowEl.appendChild(pagesEl);
                container.appendChild(rowEl);
            });
        },

        toggleBuildChapter: function (chIdx) {
            const pages = this.state.hierarchy[chIdx]?.pages || [];
            if (!this.state.buildSelection[chIdx]) this.state.buildSelection[chIdx] = {};
            const allSelected = pages.every((_, pgIdx) => this.state.buildSelection[chIdx][pgIdx]);
            pages.forEach((_, pgIdx) => { this.state.buildSelection[chIdx][pgIdx] = !allSelected; });
            this.renderBuildHierarchy();
        },

        toggleBuildPage: function (chIdx, pgIdx) {
            if (!this.state.buildSelection[chIdx]) this.state.buildSelection[chIdx] = {};
            this.state.buildSelection[chIdx][pgIdx] = !this.state.buildSelection[chIdx][pgIdx];
            this.renderBuildHierarchy();
        },

        toggleAllBuildPages: function () {
            if (!this.state.hierarchy || !this.state.buildSelection) return;
            let allSelected = true;
            for (let chIdx = 0; chIdx < this.state.hierarchy.length; chIdx++) {
                const pages = this.state.hierarchy[chIdx]?.pages || [];
                for (let pgIdx = 0; pgIdx < pages.length; pgIdx++) {
                    if (!this.state.buildSelection[chIdx]?.[pgIdx]) { allSelected = false; break; }
                }
                if (!allSelected) break;
            }
            this.state.hierarchy.forEach((ch, chIdx) => {
                (ch.pages || []).forEach((_, pgIdx) => { this.state.buildSelection[chIdx][pgIdx] = !allSelected; });
            });
            this.renderBuildHierarchy();
        },

        // --- Build Modal ---
        openBuildModal: function () {
            document.getElementById('build-modal').classList.add('active');
            this.loadBuildGrid();
            if (window.lucide) lucide.createIcons();
        },

        closeBuildModal: function () {
            document.getElementById('build-modal').classList.remove('active');
        },

        loadBuildGrid: async function () {
            const res = await fetch('/api/structure');
            const data = await res.json();
            const grid = document.getElementById('build-grid');
            grid.innerHTML = '';

            const selectAllContainer = document.createElement('div');
            selectAllContainer.style.cssText = 'padding:0 0 16px 0;border-bottom:1px solid var(--glass-border);margin-bottom:16px;';
            selectAllContainer.innerHTML = `<label class="toggle-option"><input type="checkbox" checked onchange="app.toggleAllBuild(this.checked)"><span style="font-weight:600;">Select All</span></label>`;
            grid.appendChild(selectAllContainer);

            data.chapters.forEach((ch, chIdx) => {
                const group = document.createElement('div');
                group.className = 'build-group';
                const header = document.createElement('div');
                header.className = 'chapter-header';
                header.innerHTML = `<label class="toggle-option" style="margin:0;"><input type="checkbox" checked onchange="app.toggleChapterBuild(${chIdx}, this.checked)"><span style="font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Chapter ${ch.id}</span></label>`;
                group.appendChild(header);

                const pagesContainer = document.createElement('div');
                pagesContainer.className = 'chapter-pages';
                ch.pages.forEach(p => {
                    const cell = document.createElement('div');
                    cell.className = 'grid-cell selected';
                    cell.dataset.chapterIdx = chIdx;
                    cell.dataset.id = p.id;
                    cell.dataset.chapter = ch.id;
                    cell.innerHTML = `<div class="page-num">${p.id}</div><div class="page-title">${p.path.split('/').pop()}</div>`;
                    cell.onclick = () => { cell.classList.toggle('selected'); app.updateBuildToggles(); };
                    pagesContainer.appendChild(cell);
                });

                group.appendChild(pagesContainer);
                grid.appendChild(group);
            });
        },

        toggleAllBuild: function (checked) {
            document.querySelectorAll('.build-group input[type="checkbox"]').forEach(cb => cb.checked = checked);
            document.querySelectorAll('.grid-cell').forEach(cell => {
                if (checked) cell.classList.add('selected');
                else cell.classList.remove('selected');
            });
        },

        toggleChapterBuild: function (chIdx, checked) {
            document.querySelectorAll(`.grid-cell[data-chapter-idx="${chIdx}"]`).forEach(cell => {
                if (checked) cell.classList.add('selected');
                else cell.classList.remove('selected');
            });
        },

        updateBuildToggles: function () { /* placeholder for intermediate checkbox states */ },

        // Real build progress, pushed over the doc-socket ('build_progress'
        // messages, see collab.js) from server.py's on_log/on_progress
        // callbacks into BuildManager.build_parallel — no more faked timer.
        updateBuildProgress: function (msg) {
            const progressFill = document.getElementById('progress-fill-new') || document.getElementById('progress-fill');
            const progressPage = document.getElementById('progress-page-new') || document.getElementById('progress-page');
            const progressPercent = document.getElementById('progress-percent-new') || document.getElementById('progress-percent');

            if (msg.phase === 'error') {
                if (progressPage) progressPage.textContent = msg.message || 'Build error';
                return;
            }

            const total = msg.total || 0;
            const completed = msg.completed || 0;
            // BuildManager's pagination-correction passes can re-run tasks,
            // pushing `completed` past the `total` learned from its first
            // "Generated N tasks" log — clamp instead of overshooting 100%
            // before the request has actually resolved.
            const pct = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;

            if (progressFill) progressFill.style.width = `${pct}%`;
            if (progressPercent) progressPercent.textContent = total > 0 ? `${pct}%` : '…';
            if (progressPage) {
                if (total > 0) progressPage.textContent = `Compiled ${completed}/${total}`;
                else if (msg.message) progressPage.textContent = msg.message;
            }
        },

        runBuild: async function () {
            const targets = [];
            document.querySelectorAll('.build-cell.selected').forEach(cell => {
                targets.push({ chapter: parseInt(cell.dataset.chapterIdx), page: parseInt(cell.dataset.pageIdx) });
            });

            const options = {
                frontmatter: (document.getElementById('build-opt-frontmatter') || document.getElementById('opt-frontmatter'))?.checked ?? true,
                covers: (document.getElementById('build-opt-covers') || document.getElementById('opt-covers'))?.checked ?? true
            };

            const progress = document.getElementById('build-progress-new') || document.getElementById('build-progress');
            const progressFill = document.getElementById('progress-fill-new') || document.getElementById('progress-fill');
            const progressPage = document.getElementById('progress-page-new') || document.getElementById('progress-page');
            const progressPercent = document.getElementById('progress-percent-new') || document.getElementById('progress-percent');
            const log = document.getElementById('build-log');
            const buildBtn = document.getElementById('build-btn-new') || document.getElementById('build-btn');

            if (progress) progress.style.display = 'block';
            if (log) log.style.display = 'none';
            if (buildBtn) { buildBtn.disabled = true; buildBtn.innerHTML = '<i data-lucide="loader"></i> Building...'; }
            if (progressPage) progressPage.textContent = 'Preparing...';
            if (progressPercent) progressPercent.textContent = '0%';
            if (progressFill) progressFill.style.width = '0%';

            try {
                const res = await fetch('/api/build', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ targets, options }) });
                const result = await res.json();
                if (progressFill) progressFill.style.width = '100%';
                if (progressPercent) progressPercent.textContent = '100%';
                if (buildBtn) { buildBtn.disabled = false; buildBtn.innerHTML = '<i data-lucide="zap"></i> Build PDF'; }

                if (result.success) {
                    if (progressPage) progressPage.textContent = 'Build complete!';
                    if (log) { log.style.display = 'block'; log.textContent = 'Success! Downloading PDF...'; log.style.color = 'var(--success)'; }
                    const a = document.createElement('a');
                    a.href = '/api/download/output.pdf?t=' + Date.now();
                    a.download = 'output.pdf';
                    document.body.appendChild(a); a.click(); document.body.removeChild(a);
                } else {
                    if (progressPage) progressPage.textContent = 'Build failed';
                    if (log) { log.style.display = 'block'; log.textContent = result.output || 'Unknown error'; log.style.color = 'var(--danger)'; }
                }
                // Re-check diagnostics after a build attempt — a build failure
                // is often exactly the kind of error /api/check would surface.
                if (this.checkDiagnostics) this.checkDiagnostics();
            } catch (err) {
                if (progressPage) progressPage.textContent = 'Build failed';
                if (log) { log.style.display = 'block'; log.textContent = err.message || 'Network error'; log.style.color = 'var(--danger)'; }
                if (buildBtn) { buildBtn.disabled = false; buildBtn.innerHTML = '<i data-lucide="zap"></i> Build PDF'; }
            }
            if (window.lucide) lucide.createIcons();
        },
    };

    window._buildMixin = BuildMixin;
})();
