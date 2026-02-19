// ============================================================
// CONFIG MODULE
// Config tabs: metadata, constants, hierarchy, schemes,
// snippets, preface, ignored patterns, modules, session, info
// ============================================================

(function () {
    const ConfigMixin = {
        showConfigTab: function (tabId) {
            document.querySelectorAll('.config-tab').forEach(t => t.classList.remove('active'));
            const tabEl = document.querySelector(`[data-tab="${tabId}"]`);
            if (tabEl) tabEl.classList.add('active');

            const container = document.getElementById('config-content');
            switch (tabId) {
                case 'metadata': this.renderMetadataTab(container); break;
                case 'constants': this.renderConstantsTab(container); break;
                case 'hierarchy': this.renderHierarchyTab(container); break;
                case 'schemes': this.renderSchemesTab(container); break;
                case 'snippets': this.renderSnippetsTab(container); break;
                case 'preface': this.renderPrefaceTab(container); break;
                case 'ignored': this.renderIgnoredTab(container); break;
                case 'modules': this.renderModulesTab(container); break;
                case 'session': this.renderSessionTab(container); break;
                case 'info': this.renderInfoTab(container); break;
            }
        },

        saveCurrentConfigTab: function () {
            const activeTab = document.querySelector('.config-tab.active');
            if (!activeTab) return;
            const tabId = activeTab.dataset.tab;
            switch (tabId) {
                case 'metadata': this.updateMetadata(); break;
                case 'constants': this.updateConstants(); break;
                case 'hierarchy': this.saveHierarchy(); break;
                case 'snippets': this.saveSnippets(); break;
                case 'preface': this.savePreface(); break;
                case 'ignored': this.saveIgnored(); break;
            }
        },

        // --- Metadata Tab ---
        renderMetadataTab: async function (container) {
            const res = await fetch('/api/metadata');
            const data = await res.json();
            container.innerHTML = `
                <div class="config-section">
                    <h3>Document Metadata</h3>
                    <p>Information displayed on the cover page</p>
                    <div class="form-group">
                        <label>Title</label>
                        <input type="text" id="meta-title" value="${data.title || ''}" oninput="app.debouncedUpdateMetadata()">
                    </div>
                    <div class="form-group">
                        <label>Subtitle</label>
                        <input type="text" id="meta-subtitle" value="${data.subtitle || ''}" oninput="app.debouncedUpdateMetadata()">
                    </div>
                    <div class="form-group">
                        <label>Authors (comma-separated)</label>
                        <input type="text" id="meta-authors" value="${(data.authors || []).join(', ')}" oninput="app.debouncedUpdateMetadata()">
                    </div>
                    <div class="form-group">
                        <label>Affiliation</label>
                        <input type="text" id="meta-affiliation" value="${data.affiliation || ''}" oninput="app.debouncedUpdateMetadata()">
                    </div>
                    <div class="form-group">
                        <label>Logo Path</label>
                        <input type="text" id="meta-logo" value="${data.logo || ''}" oninput="app.debouncedUpdateMetadata()" placeholder="e.g., images/logo.png">
                    </div>
                </div>
            `;
        },

        updateMetadata: async function () {
            const data = {
                title: document.getElementById('meta-title').value,
                subtitle: document.getElementById('meta-subtitle').value,
                authors: document.getElementById('meta-authors').value.split(',').map(s => s.trim()).filter(s => s),
                affiliation: document.getElementById('meta-affiliation').value,
                logo: document.getElementById('meta-logo').value
            };
            await fetch('/api/metadata', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            this.showSaveStatus('Metadata Saved');
        },

        // --- Constants Tab ---
        renderConstantsTab: async function (container) {
            const res = await fetch('/api/constants');
            const data = await res.json();
            this.state.configData.constants = data;
            container.innerHTML = `
                <div class="config-section">
                    <h3>Theme &amp; Display Settings</h3>
                    <p>Control how your document looks</p>
                    <div class="form-group"><label>Font</label><input type="text" id="const-font" value="${data['font'] || ''}" oninput="app.debouncedUpdateConstants()"></div>
                    <div class="form-group"><label>Title Font</label><input type="text" id="const-title-font" value="${data['title-font'] || ''}" oninput="app.debouncedUpdateConstants()"></div>
                    <div class="form-group"><label>Chapter Name</label><input type="text" id="const-chapter-name" value="${data['chapter-name'] || 'Chapter'}" oninput="app.debouncedUpdateConstants()"></div>
                    <div class="form-group"><label>Section Name</label><input type="text" id="const-subchap-name" value="${data['subchap-name'] || 'Section'}" oninput="app.debouncedUpdateConstants()"></div>
                    <h4 style="margin-top:32px;margin-bottom:16px;font-family:var(--font-display);font-weight:500;">Display Options</h4>
                    <label class="toggle-option"><input type="checkbox" id="const-display-cover" ${data['display-cover'] ? 'checked' : ''} onchange="app.updateConstants()"><span>Show Cover Page</span></label>
                    <label class="toggle-option"><input type="checkbox" id="const-display-outline" ${data['display-outline'] ? 'checked' : ''} onchange="app.updateConstants()"><span>Show Table of Contents</span></label>
                    <label class="toggle-option"><input type="checkbox" id="const-display-chap-cover" ${data['display-chap-cover'] ? 'checked' : ''} onchange="app.updateConstants()"><span>Show Chapter Covers</span></label>
                    <label class="toggle-option"><input type="checkbox" id="const-show-solution" ${data['show-solution'] ? 'checked' : ''} onchange="app.updateConstants()"><span>Show Solutions</span></label>
                </div>
            `;
        },

        updateConstants: async function () {
            const data = {
                ...this.state.configData.constants,
                'font': document.getElementById('const-font').value,
                'title-font': document.getElementById('const-title-font').value,
                'chapter-name': document.getElementById('const-chapter-name').value,
                'subchap-name': document.getElementById('const-subchap-name').value,
                'display-cover': document.getElementById('const-display-cover').checked,
                'display-outline': document.getElementById('const-display-outline').checked,
                'display-chap-cover': document.getElementById('const-display-chap-cover').checked,
                'show-solution': document.getElementById('const-show-solution').checked
            };
            await fetch('/api/constants', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            this.showSaveStatus('Settings Saved');
        },

        // --- Hierarchy Tab ---
        renderHierarchyTab: async function (container) {
            const res = await fetch('/api/hierarchy');
            const data = await res.json();
            this.state.hierarchy = data.hierarchy;
            container.innerHTML = `
                <div class="config-section">
                    <h3>Document Structure</h3>
                    <p>Organize chapters and pages</p>
                    <div class="hierarchy-editor" id="hierarchy-editor"></div>
                    <div style="margin-top:20px;">
                        <button class="btn btn-secondary" onclick="app.addChapter()"><i data-lucide="plus"></i> Add Chapter</button>
                    </div>
                </div>
            `;
            this.renderHierarchyEditor();
        },

        renderHierarchyEditor: function () {
            const editor = document.getElementById('hierarchy-editor');
            if (!editor) return;
            editor.innerHTML = '';
            this.state.hierarchy.forEach((chapter, chIdx) => {
                const chapterEl = document.createElement('div');
                chapterEl.className = 'chapter-card';
                chapterEl.innerHTML = `
                    <div class="chapter-header">
                        <span class="chapter-number">Ch ${chIdx + 1}</span>
                        <input type="text" class="chapter-title-input" value="${chapter.title || ''}"
                               oninput="app.updateChapterTitle(${chIdx}, this.value)" placeholder="Chapter Title">
                        <div class="chapter-actions">
                            <button class="icon-btn" onclick="app.addPage(${chIdx})" title="Add Page"><i data-lucide="plus"></i></button>
                            <button class="icon-btn" onclick="app.deleteChapter(${chIdx})" title="Delete Chapter"><i data-lucide="trash-2"></i></button>
                        </div>
                    </div>
                    <div class="chapter-pages" id="chapter-${chIdx}-pages"></div>
                `;
                editor.appendChild(chapterEl);
                const pagesContainer = document.getElementById(`chapter-${chIdx}-pages`);
                (chapter.pages || []).forEach((page, pgIdx) => {
                    const pageEl = document.createElement('div');
                    pageEl.className = 'page-item';
                    pageEl.innerHTML = `
                        <span class="page-number">Page ${pgIdx + 1}</span>
                        <input type="text" class="page-title-input" value="${page.title || ''}"
                               oninput="app.updatePageTitle(${chIdx}, ${pgIdx}, this.value)" placeholder="Page Title">
                        <button class="icon-btn" onclick="app.deletePage(${chIdx}, ${pgIdx})" title="Delete Page"><i data-lucide="x"></i></button>
                    `;
                    pagesContainer.appendChild(pageEl);
                });
            });
            if (window.lucide) lucide.createIcons();
        },

        updateChapterTitle: function (chIdx, title) { this.state.hierarchy[chIdx].title = title; this.debouncedSaveHierarchy(); },
        updatePageTitle: function (chIdx, pgIdx, title) { this.state.hierarchy[chIdx].pages[pgIdx].title = title; this.debouncedSaveHierarchy(); },
        addChapter: function () { this.state.hierarchy.push({ title: 'New Chapter', summary: '', pages: [] }); this.renderHierarchyEditor(); this.saveHierarchy(); },
        deleteChapter: function (chIdx) { if (confirm('Delete this chapter and all its pages?')) { this.state.hierarchy.splice(chIdx, 1); this.renderHierarchyEditor(); this.saveHierarchy(); } },
        addPage: function (chIdx) { this.state.hierarchy[chIdx].pages.push({ title: 'New Page' }); this.renderHierarchyEditor(); this.saveHierarchy(); },
        deletePage: function (chIdx, pgIdx) { this.state.hierarchy[chIdx].pages.splice(pgIdx, 1); this.renderHierarchyEditor(); this.saveHierarchy(); },

        saveHierarchy: async function () {
            try {
                await fetch('/api/hierarchy', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hierarchy: this.state.hierarchy })
                });
                this.showSaveStatus('Structure Saved');
            } catch (e) {
                console.error('Error saving structure:', e);
                this.showSaveStatus('Error Saving');
            }
        },

        // --- Schemes Tab ---
        renderSchemesTab: async function (container) {
            const res = await fetch('/api/schemes');
            const data = await res.json();
            container.innerHTML = `
                <div class="config-section">
                    <h3>Color Themes</h3>
                    <p>Select the active color scheme</p>
                    <div id="schemes-list"></div>
                </div>
            `;
            const list = document.getElementById('schemes-list');
            data.themes.forEach(t => {
                const el = document.createElement('div');
                el.className = 'theme-card' + (t.name === data.active ? ' active' : '');
                let colorHtml = '';
                if (t.colors && t.colors.length) t.colors.forEach(c => { colorHtml += `<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${c};border:1px solid var(--glass-border);"></span>`; });
                el.innerHTML = `<div style="display:flex;align-items:center;gap:8px;"><span style="font-weight:500;">${t.name}</span><div style="display:flex;gap:4px;margin-left:auto;">${colorHtml}</div></div>`;
                el.onclick = async () => {
                    await fetch('/api/schemes/active', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme: t.name }) });
                    this.renderSchemesTab(container);
                };
                list.appendChild(el);
            });
        },

        // --- Snippets Tab ---
        renderSnippetsTab: async function (container) {
            const res = await fetch('/api/snippets');
            const data = await res.json();
            this.state.configData.snippets = data.snippets || [];
            container.innerHTML = `
                <div class="config-section">
                    <h3>Code Snippets</h3>
                    <p>Reusable code snippets for your documents</p>
                    <div id="snippets-list"></div>
                    <div style="margin-top:16px;"><button class="btn btn-secondary" onclick="app.addSnippet()"><i data-lucide="plus"></i> Add</button></div>
                </div>
            `;
            this.renderSnippetsList();
        },

        renderSnippetsList: function () {
            const list = document.getElementById('snippets-list');
            if (!list) return;
            list.innerHTML = '';
            this.state.configData.snippets.forEach((s, i) => {
                const el = document.createElement('div');
                el.className = 'list-item';
                el.innerHTML = `
                    <input type="text" value="${s.name}" oninput="app.updateSnippet(${i}, 'name', this.value)" placeholder="Name" style="flex:1">
                    <input type="text" value="${s.definition.replace(/"/g, '&quot;')}" oninput="app.updateSnippet(${i}, 'definition', this.value)" placeholder="Definition" style="flex:2">
                    <button class="btn btn-danger" onclick="app.deleteSnippet(${i})"><i data-lucide="trash-2"></i></button>
                `;
                list.appendChild(el);
            });
            if (window.lucide) lucide.createIcons();
        },

        updateSnippet: function (index, field, value) { this.state.configData.snippets[index][field] = value; this.debouncedSaveSnippets(); },
        addSnippet: function () { this.state.configData.snippets.push({ name: 'new', definition: '[]' }); this.renderSnippetsList(); this.saveSnippets(); },
        deleteSnippet: function (index) { this.state.configData.snippets.splice(index, 1); this.renderSnippetsList(); this.saveSnippets(); },
        saveSnippets: async function () {
            await fetch('/api/snippets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ snippets: this.state.configData.snippets }) });
            this.showSaveStatus('Snippets Saved');
        },

        // --- Preface Tab ---
        renderPrefaceTab: async function (container) {
            const res = await fetch('/api/preface');
            const data = await res.json();
            container.innerHTML = `
                <div class="config-section">
                    <h3>Preface</h3>
                    <p>Content displayed before the table of contents</p>
                    <div class="preface-editor-container"><div id="preface-monaco"></div></div>
                </div>
            `;
            if (window.monaco) {
                this.state.prefaceEditor = monaco.editor.create(document.getElementById('preface-monaco'), {
                    value: data.content || '', language: 'markdown', theme: this.state.editorTheme,
                    automaticLayout: true, fontSize: 14, fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
                    minimap: { enabled: false }, padding: { top: 16 }, wordWrap: 'on', lineNumbers: 'on'
                });
                this.state.prefaceEditor.onDidChangeModelContent(() => this.debouncedSavePreface());
            }
            if (window.lucide) lucide.createIcons();
        },

        savePreface: async function () {
            const content = this.state.prefaceEditor ? this.state.prefaceEditor.getValue()
                : (document.getElementById('preface-content')?.value || '');
            await fetch('/api/preface', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content }) });
            this.showSaveStatus('Preface Saved');
        },

        // --- Ignored Patterns Tab ---
        renderIgnoredTab: async function (container) {
            const res = await fetch('/api/indexignore');
            const data = await res.json();
            this.state.configData.patterns = data.patterns || [];
            container.innerHTML = `
                <div class="config-section">
                    <h3>Ignored Patterns</h3>
                    <p>Files and folders to exclude from the project</p>
                    <div id="ignored-list"></div>
                    <div style="margin-top:16px;"><button class="btn btn-secondary" onclick="app.addIgnoredPattern()"><i data-lucide="plus"></i> Add Pattern</button></div>
                </div>
            `;
            this.renderIgnoredList();
        },

        renderIgnoredList: function () {
            const list = document.getElementById('ignored-list');
            if (!list) return;
            list.innerHTML = '';
            this.state.configData.patterns.forEach((p, i) => {
                const el = document.createElement('div');
                el.className = 'list-item';
                el.innerHTML = `
                    <input type="text" value="${p}" oninput="app.updateIgnoredPattern(${i}, this.value)" placeholder="Pattern (e.g., node_modules)">
                    <button class="btn btn-danger" onclick="app.deleteIgnoredPattern(${i})"><i data-lucide="trash-2"></i></button>
                `;
                list.appendChild(el);
            });
            if (window.lucide) lucide.createIcons();
        },

        updateIgnoredPattern: function (index, value) { this.state.configData.patterns[index] = value; this.debouncedSaveIgnored(); },
        addIgnoredPattern: function () { this.state.configData.patterns.push(''); this.renderIgnoredList(); this.saveIgnored(); },
        deleteIgnoredPattern: function (index) { this.state.configData.patterns.splice(index, 1); this.renderIgnoredList(); this.saveIgnored(); },
        saveIgnored: async function () {
            await fetch('/api/indexignore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ patterns: this.state.configData.patterns }) });
            this.showSaveStatus('Patterns Saved');
        },

        // --- Modules Tab ---
        renderModulesTab: async function (container) {
            const res = await fetch('/api/modules');
            const modules = await res.json();
            container.innerHTML = `
                <div class="config-section">
                    <h3>Installed Modules</h3>
                    <p>Modules extend Noteworthy with additional features</p>
                    <div id="modules-list"></div>
                </div>
            `;
            const list = document.getElementById('modules-list');
            Object.entries(modules).forEach(([name, info]) => {
                const cleanName = name.split('/').pop();
                const el = document.createElement('div');
                el.className = 'list-item module-item';
                const actionHtml = info.has_config ? `<button onclick="app.configureModule('${name}')" class="icon-btn" title="Configure"><i data-lucide="settings"></i></button>` : '';
                el.innerHTML = `
                    <div class="module-info">
                        <div class="module-name">${cleanName}</div>
                        <div class="module-meta"><span class="module-source">${info.source}</span><span class="module-status">${info.status.toUpperCase()}</span></div>
                    </div>
                    ${actionHtml}
                `;
                list.appendChild(el);
            });
            if (window.lucide) lucide.createIcons();
        },

        configureModule: async function (name) {
            const res = await fetch(`/api/modules/${name}/config`);
            const data = await res.json();
            const settings = data.settings;
            if (!settings || settings.length === 0) { this.showSaveStatus('No configuration available'); return; }

            let overlay = document.getElementById('config-modal-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'config-modal-overlay';
                overlay.className = 'modal-overlay';
                overlay.innerHTML = `
                    <div class="modal">
                        <div class="modal-header">
                            <h2>Configure Module</h2>
                            <button onclick="document.getElementById('config-modal-overlay').classList.remove('active')" class="icon-btn-small"><i data-lucide="x"></i></button>
                        </div>
                        <div id="module-config-form" style="display:flex;flex-direction:column;gap:16px;margin-top:16px;"></div>
                        <div class="build-actions" style="margin-top:24px;"><button id="save-module-config-btn" class="btn btn-primary">Save Changes</button></div>
                    </div>
                `;
                document.body.appendChild(overlay);
            }
            this.renderModuleConfig(name, settings);
            overlay.classList.add('active');
            if (window.lucide) lucide.createIcons();
        },

        renderModuleConfig: function (name, settings) {
            const form = document.getElementById('module-config-form');
            form.innerHTML = '';
            document.getElementById('save-module-config-btn').onclick = () => this.saveModuleConfig(name);
            settings.forEach(setting => {
                const group = document.createElement('div');
                group.className = 'form-group';
                const label = document.createElement('label');
                label.textContent = setting.label || setting.key;
                group.appendChild(label);
                let input;
                if (setting.type === 'choice') {
                    input = document.createElement('select');
                    setting.options.forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt; option.textContent = opt;
                        if (opt === setting.value) option.selected = true;
                        input.appendChild(option);
                    });
                } else if (setting.type === 'bool') {
                    group.className = 'toggle-option';
                    group.innerHTML = '';
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.checked = !!setting.value;
                    const span = document.createElement('span');
                    span.textContent = setting.label || setting.key;
                    group.appendChild(input);
                    group.appendChild(span);
                } else {
                    input = document.createElement('input');
                    input.type = setting.type === 'int' ? 'number' : 'text';
                    input.value = setting.value || '';
                }
                input.id = `mod-cfg-${setting.key}`;
                input.dataset.key = setting.key;
                input.dataset.type = setting.type;
                if (setting.type !== 'bool') group.appendChild(input);
                form.appendChild(group);
            });
        },

        saveModuleConfig: async function (name) {
            const inputs = document.querySelectorAll('#module-config-form [data-key]');
            const config = {};
            inputs.forEach(input => {
                const key = input.dataset.key;
                const type = input.dataset.type;
                if (type === 'bool') config[key] = input.checked;
                else if (type === 'int') config[key] = parseInt(input.value);
                else config[key] = input.value;
            });
            await fetch(`/api/modules/${name}/config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
            document.getElementById('config-modal-overlay').classList.remove('active');
            this.showSaveStatus('Configuration Saved');
        },

        // --- Session Tab ---
        renderSessionTab: function (container) {
            const themeOptions = this.EDITOR_THEMES
                ? Object.keys(this.EDITOR_THEMES).map(id => {
                    const theme = this.EDITOR_THEMES[id];
                    const selected = this.state.editorTheme === id ? 'selected' : '';
                    return `<option value="${id}" ${selected}>${theme.label}</option>`;
                }).join('')
                : '<option value="noteworthy-dark">Noteworthy Dark</option>';
            container.innerHTML = `
                <div class="config-section">
                    <h3>Session Settings</h3>
                    <p>Configure your appearance in collaboration sessions</p>
                    <div class="form-group">
                        <label>Display Name</label>
                        <input type="text" id="session-name" value="${this.state.sessionName}" oninput="app.updateSessionName(this.value)" placeholder="Anonymous">
                        <p style="font-size:12px;color:var(--text-muted);margin-top:8px;">This name will be visible to other users editing the same file. It is saved in your browser storage.</p>
                    </div>
                    <div class="form-group">
                        <label>Editor Theme</label>
                        <select id="editor-theme-select" onchange="app.setEditorTheme(this.value)">${themeOptions}</select>
                        <p style="font-size:12px;color:var(--text-muted);margin-top:8px;">Choose a color scheme for the code editor. Your preference is saved in your browser.</p>
                    </div>
                </div>
            `;
        },

        updateSessionName: function (name) {
            this.state.sessionName = name || 'Anonymous';
            localStorage.setItem('sessionName', this.state.sessionName);
            // Update Yjs Awareness with new name
            if (this.state.yjsProvider) {
                this.state.yjsProvider.awareness.setLocalStateField('user', {
                    name: this.state.sessionName,
                    color: this.state.userColor || this.getUserColor(this.state.yjsProvider.awareness.clientID || 0)
                });
            }
            this.showSaveStatus('Name Updated');
        },

        // --- Info Tab ---
        renderInfoTab: function (container) {
            container.innerHTML = `
                <div class="config-section" style="text-align:center;padding:32px 24px;">
                    <pre style="font-family:'JetBrains Mono',monospace;font-size:14px;line-height:1.2;color:var(--accent-primary);margin-bottom:16px;display:inline-block;">${this.ASCII_LOGO || ''}</pre>
                    <h1 style="font-family:var(--font-display);font-size:28px;font-weight:700;margin-bottom:4px;">Noteworthy</h1>
                    <p style="color:var(--text-muted);margin-bottom:16px;font-size:14px;">A modular Typst template system</p>
                    <span style="background:var(--bg-secondary);border-radius:6px;padding:6px 16px;font-family:'JetBrains Mono',monospace;font-size:13px;">v0.2.0</span>
                </div>
                <div class="config-section" style="display:flex;justify-content:center;gap:24px;padding:16px 24px;flex-wrap:wrap;">
                    <a href="https://noteworthy.benjaminlee.kr/docs.html" target="_blank" class="info-link"><i data-lucide="book-open"></i> Docs</a>
                    <a href="https://github.com/sihooleebd/noteworthy" target="_blank" class="info-link"><i data-lucide="github"></i> GitHub</a>
                    <a href="https://typst.app" target="_blank" class="info-link"><i data-lucide="external-link"></i> Typst</a>
                </div>
                <div class="config-section" style="text-align:center;padding:16px 24px;">
                    <p style="font-size:13px;font-weight:600;margin-bottom:8px;">Special Thanks</p>
                    <p style="font-size:12px;color:var(--text-muted);line-height:1.5;">Design feedback: <strong>discord@ㅅㅈㅁ</strong><br>Beta testing: <strong>discord@Andrew</strong></p>
                </div>
                <div class="config-section" style="text-align:center;padding:16px 24px;border-top:1px solid var(--border-color);">
                    <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">Created by <strong>Benjamin Lee</strong> &amp; <strong>Hojun Lee</strong></p>
                    <p style="font-size:11px;color:var(--text-muted);">© 2024-2026 · Built with Typst, Tinymist, FastAPI, Monaco, and a LOT of coffee.</p>
                </div>
                <style>
                    .info-link { display:flex;align-items:center;gap:6px;color:var(--accent-primary);text-decoration:none;font-size:14px;padding:8px 16px;background:var(--bg-secondary);border-radius:8px;transition:opacity 0.2s; }
                    .info-link:hover { opacity:0.8; }
                    .info-link i { width:16px;height:16px; }
                </style>
            `;
            if (typeof lucide !== 'undefined') lucide.createIcons();
        },
    };

    window._configMixin = ConfigMixin;
})();
