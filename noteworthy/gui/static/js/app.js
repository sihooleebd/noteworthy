/**
 * Noteworthy GUI - Main Application
 */
const app = {
    state: {
        activeFile: null,
        editor: null,
        ws: null,
        ws: null,
        configData: {},
        editorTheme: localStorage.getItem('editorTheme') || 'vs-dark',
        sessionName: localStorage.getItem('sessionName') || 'Anonymous'
    },

    // ============================================================
    // INITIALIZATION
    // ============================================================

    init: async function () {
        // Setup config tab navigation
        document.querySelectorAll('.config-tab').forEach(tab => {
            tab.onclick = () => this.showConfigTab(tab.dataset.tab);
        });

        // Initialize debounced functions
        this.debouncedUpdateMetadata = this.debounce(() => this.updateMetadata(), 1000);
        this.debouncedUpdateConstants = this.debounce(() => this.updateConstants(), 1000);
        this.debouncedSaveHierarchy = this.debounce(() => this.saveHierarchy(), 1000);
        this.debouncedSaveSnippets = this.debounce(() => this.saveSnippets(), 1000);
        this.debouncedSavePreface = this.debounce(() => this.savePreface(), 1000);
        this.debouncedSaveIgnored = this.debounce(() => this.saveIgnored(), 1000);

        // Monaco Editor with saved theme
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], () => {
            this.state.editor = monaco.editor.create(document.getElementById('monaco-container'), {
                value: '// Select a file from the sidebar',
                language: 'markdown',
                theme: this.state.editorTheme,
                automaticLayout: true,
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
                minimap: { enabled: false },
                padding: { top: 16 },
                lineNumbers: 'on',
                roundedSelection: true,
                scrollBeyondLastLine: false
            });

            // Auto-save on change
            let saveTimeout;
            this.state.editor.onDidChangeModelContent((e) => {
                clearTimeout(saveTimeout);
                document.getElementById('save-status').textContent = '● Unsaved';

                // Local Echo: Trigger preview update immediately (optimistic)
                const path = this.state.activeFile;

                saveTimeout = setTimeout(() => this.saveCurrentFile(), 250); // Fast autosave for responsive preview

                // Broadcast edit
                if (app.collab && !app.collab.applyingRemoteChanges) {
                    app.collab.broadcastEdit(e.changes);
                }
            });

            // Collaboration: Cursor broadcast
            this.state.editor.onDidChangeCursorPosition((e) => {
                if (app.collab) {
                    app.collab.broadcastCursor(e.position);
                }
            });

            // Set theme selector to current value
            const themeSelect = document.getElementById('editor-theme');
            if (themeSelect) themeSelect.value = this.state.editorTheme;
        });

        // WebSocket for live preview
        this.connectWebSocket();

        // Load initial data
        await this.refreshTree();
        await this.loadStatus();

        // Show initial config
        this.showConfigTab('metadata');

        // Initialize Collaboration
        if (typeof CollaborationManager !== 'undefined') {
            this.collab = new CollaborationManager(this);
            this.collab.connect(); // Connect to global session

            // Set initial identity if changed from default
            if (this.state.sessionName !== 'Anonymous') {
                this.collab.setIdentity(this.state.sessionName);
            }
        }

        // Initialize resizer
        this.initResizer();
    },

    initResizer: function () {
        const resizer = document.getElementById('editor-resizer');
        const previewPanel = document.querySelector('.preview-panel');
        const mainContent = document.querySelector('.main-content');

        if (!resizer || !previewPanel || !mainContent) return;

        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            // Calculate new width
            const containerRect = mainContent.getBoundingClientRect();
            // Right edge of container minus mouse X gives preview width
            let newWidth = containerRect.right - e.clientX;

            // Constraints (min 200px, max 80%)
            const minWidth = 200;
            const maxWidth = containerRect.width - 200;

            if (newWidth < minWidth) newWidth = minWidth;
            if (newWidth > maxWidth) newWidth = maxWidth;

            previewPanel.style.width = `${newWidth}px`;

            // Resize Monaco
            if (this.state.editor) this.state.editor.layout();
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';

                // Final layout update
                if (this.state.editor) this.state.editor.layout();
            }
        });
    },

    // ============================================================
    // NAVIGATION (Dock)
    // ============================================================

    showPage: function (pageId) {
        // Update pages
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${pageId}`).classList.add('active');

        // Update dock items
        document.querySelectorAll('.dock-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageId);
        });

        // Re-init lucide icons for dynamic content
        if (window.lucide) lucide.createIcons();

        if (pageId === 'build') this.loadBuildGrid();
    },

    setEditorTheme: function (theme) {
        this.state.editorTheme = theme;
        localStorage.setItem('editorTheme', theme);
        if (this.state.editor) {
            monaco.editor.setTheme(theme);
        }
    },

    // ============================================================
    // FILE TREE
    // ============================================================

    refreshTree: async function () {
        const res = await fetch('/api/tree');
        const data = await res.json();
        const container = document.getElementById('file-tree');
        container.innerHTML = '';

        const render = (items, depth) => {
            const div = document.createElement('div');
            items.forEach(item => {
                const el = document.createElement('div');
                el.className = 'tree-item';
                el.style.paddingLeft = `${depth * 16 + 12}px`;

                if (item.is_dir) {
                    // Folder with toggle
                    const isExpanded = this.state.expandedFolders?.[item.path] !== false; // Default expanded
                    el.innerHTML = `<i data-lucide="${isExpanded ? 'chevron-down' : 'chevron-right'}" class="tree-arrow"></i><i data-lucide="folder" class="tree-folder"></i> ${item.name}`;
                    el.onclick = (e) => {
                        e.stopPropagation();
                        this.toggleFolder(item.path);
                    };
                    div.appendChild(el);

                    if (item.children && isExpanded) {
                        const childDiv = render(item.children, depth + 1);
                        childDiv.dataset.folder = item.path;
                        div.appendChild(childDiv);
                    }
                } else {
                    el.innerHTML = `<i data-lucide="file" class="tree-file" style="fill: none; stroke-width: 2px;"></i> ${item.name}`;
                    el.onclick = () => this.openFile(item.path, el);
                    div.appendChild(el);
                }
            });
            return div;
        };

        // Initialize expanded folders state if not exists
        if (!this.state.expandedFolders) {
            this.state.expandedFolders = {};
        }

        container.appendChild(render(data.items, 0));

        // Re-initialize Lucide icons for new elements
        if (window.lucide) {
            lucide.createIcons();
        }
    },

    toggleFolder: function (path) {
        if (!this.state.expandedFolders) {
            this.state.expandedFolders = {};
        }
        // Default is expanded (true), so toggle to false means collapse
        this.state.expandedFolders[path] = this.state.expandedFolders[path] === false ? true : false;
        this.refreshTree();
    },

    openFile: async function (path, el) {
        // Update selection
        document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('selected'));
        if (el) el.classList.add('selected');

        this.state.activeFile = path;
        document.getElementById('active-filename').textContent = path;

        // Switch collab file
        if (this.collab) {
            this.collab.switchFile(path);
        }

        // Load file content
        const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
        const data = await res.json();

        if (this.state.editor && data.content !== undefined) {
            const ext = path.split('.').pop();
            const lang = ext === 'typ' ? 'markdown' : (ext === 'json' ? 'json' : 'plaintext');
            monaco.editor.setModelLanguage(this.state.editor.getModel(), lang);
            this.state.editor.setValue(data.content);
        }

        // Start preview for .typ files
        if (path.endsWith('.typ')) {
            document.getElementById('preview-container').innerHTML = '';
            await fetch('/api/watch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });

            // Connect to collaboration session
            if (app.collab) {
                app.collab.connect(path);
            }
        }
    },

    saveCurrentFile: async function () {
        if (!this.state.activeFile) return;

        await fetch('/api/file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: this.state.activeFile,
                content: this.state.editor.getValue()
            })
        });

        document.getElementById('save-status').textContent = 'Saved';
        setTimeout(() => document.getElementById('save-status').textContent = '', 2000);
    },

    // ============================================================
    // CONFIG TABS
    // ============================================================

    showConfigTab: function (tabId) {
        document.querySelectorAll('.config-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');

        const container = document.getElementById('config-content');

        switch (tabId) {
            case 'metadata': this.renderMetadataTab(container); break;
            case 'constants': this.renderConstantsTab(container); break;
            case 'hierarchy': this.renderHierarchyTab(container); break;
            case 'schemes': this.renderSchemesTab(container); break;
            case 'snippets': this.renderSnippetsTab(container); break;
            case 'preface': this.renderPrefaceTab(container); break;
            case 'ignored': this.renderIgnoredTab(container); break;
            case 'preface': this.renderPrefaceTab(container); break;
            case 'ignored': this.renderIgnoredTab(container); break;
            case 'modules': this.renderModulesTab(container); break;
            case 'session': this.renderSessionTab(container); break;
        }
    },

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

    renderConstantsTab: async function (container) {
        const res = await fetch('/api/constants');
        const data = await res.json();
        this.state.configData.constants = data;

        container.innerHTML = `
            <div class="config-section">
                <h3>Theme & Display Settings</h3>
                <p>Control how your document looks</p>
                
                <div class="form-group">
                    <label>Display Mode (Theme)</label>
                    <input type="text" id="const-display-mode" value="${data['display-mode'] || 'default'}" oninput="app.debouncedUpdateConstants()">
                </div>
                <div class="form-group">
                    <label>Font</label>
                    <input type="text" id="const-font" value="${data['font'] || ''}" oninput="app.debouncedUpdateConstants()">
                </div>
                <div class="form-group">
                    <label>Title Font</label>
                    <input type="text" id="const-title-font" value="${data['title-font'] || ''}" oninput="app.debouncedUpdateConstants()">
                </div>
                <div class="form-group">
                    <label>Chapter Name</label>
                    <input type="text" id="const-chapter-name" value="${data['chapter-name'] || 'Chapter'}" oninput="app.debouncedUpdateConstants()">
                </div>
                <div class="form-group">
                    <label>Section Name</label>
                    <input type="text" id="const-subchap-name" value="${data['subchap-name'] || 'Section'}" oninput="app.debouncedUpdateConstants()">
                </div>
                
                <h4 style="margin-top: 32px; margin-bottom: 16px; font-family: var(--font-display); font-weight: 500;">Display Options</h4>
                <label class="toggle-option">
                    <input type="checkbox" id="const-display-cover" ${data['display-cover'] ? 'checked' : ''} onchange="app.updateConstants()">
                    <span>Show Cover Page</span>
                </label>
                <label class="toggle-option">
                    <input type="checkbox" id="const-display-outline" ${data['display-outline'] ? 'checked' : ''} onchange="app.updateConstants()">
                    <span>Show Table of Contents</span>
                </label>
                <label class="toggle-option">
                    <input type="checkbox" id="const-display-chap-cover" ${data['display-chap-cover'] ? 'checked' : ''} onchange="app.updateConstants()">
                    <span>Show Chapter Covers</span>
                </label>
                <label class="toggle-option">
                    <input type="checkbox" id="const-show-solution" ${data['show-solution'] ? 'checked' : ''} onchange="app.updateConstants()">
                    <span>Show Solutions</span>
                </label>
            </div>
        `;
    },

    updateConstants: async function () {
        const data = {
            ...this.state.configData.constants,
            'display-mode': document.getElementById('const-display-mode').value,
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

    // Utils
    debounce: function (func, wait) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    },

    showSaveStatus: function (msg = 'Saved') {
        // Create toast if it doesn't exist
        let toast = document.getElementById('save-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'save-toast';
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.right = '20px';
            toast.style.background = 'var(--glass-bg-hover)';
            toast.style.color = 'var(--success)';
            toast.style.padding = '8px 16px';
            toast.style.borderRadius = '20px';
            toast.style.border = '1px solid var(--glass-border)';
            toast.style.fontSize = '13px';
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            toast.style.pointerEvents = 'none';
            toast.style.zIndex = '2000';
            document.body.appendChild(toast);
        }

        toast.textContent = msg;
        toast.style.opacity = '1';
        setTimeout(() => toast.style.opacity = '0', 2000);
    },

    // Wrapped update functions with debounce
    debouncedUpdateMetadata: null, // Initialized in init
    debouncedUpdateConstants: null,
    debouncedSaveHierarchy: null,
    debouncedSaveSnippets: null,
    debouncedSavePreface: null,
    debouncedSaveIgnored: null,

    renderHierarchyTab: async function (container) {
        const res = await fetch('/api/hierarchy');
        const data = await res.json();
        this.state.hierarchy = data.hierarchy;

        container.innerHTML = `
            <div class="config-section">
                <h3>Document Structure</h3>
                <p>Organize chapters and pages</p>
                <div class="hierarchy-editor" id="hierarchy-editor"></div>
                <div style="margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="app.addChapter()">
                        <i data-lucide="plus"></i> Add Chapter
                    </button>
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
                        <button class="icon-btn" onclick="app.deleteChapter(${chIdx})" title="Delete Chapter">
                            <i data-lucide="trash-2"></i>
                        </button>
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
                    <button class="icon-btn" onclick="app.deletePage(${chIdx}, ${pgIdx})" title="Delete Page">
                        <i data-lucide="x"></i>
                    </button>
                `;
                pagesContainer.appendChild(pageEl);
            });

            // Add page button
            const addPageBtn = document.createElement('button');
            addPageBtn.className = 'add-btn';
            addPageBtn.innerHTML = '<i data-lucide="plus"></i> Add Page';
            addPageBtn.onclick = () => this.addPage(chIdx);
            pagesContainer.appendChild(addPageBtn);
        });

        if (window.lucide) lucide.createIcons();
    },

    updateChapterTitle: function (chIdx, title) {
        this.state.hierarchy[chIdx].title = title;
        this.debouncedSaveHierarchy();
    },

    updatePageTitle: function (chIdx, pgIdx, title) {
        this.state.hierarchy[chIdx].pages[pgIdx].title = title;
        this.debouncedSaveHierarchy();
    },

    addChapter: function () {
        this.state.hierarchy.push({ title: 'New Chapter', summary: '', pages: [] });
        this.renderHierarchyEditor();
        this.saveHierarchy(); // Immediate save on structure change
    },

    deleteChapter: function (chIdx) {
        if (confirm('Delete this chapter and all its pages?')) {
            this.state.hierarchy.splice(chIdx, 1);
            this.renderHierarchyEditor();
            this.saveHierarchy();
        }
    },

    addPage: function (chIdx) {
        this.state.hierarchy[chIdx].pages.push({ title: 'New Page' });
        this.renderHierarchyEditor();
        this.saveHierarchy();
    },

    deletePage: function (chIdx, pgIdx) {
        this.state.hierarchy[chIdx].pages.splice(pgIdx, 1);
        this.renderHierarchyEditor();
        this.saveHierarchy();
    },

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
            if (t.colors && t.colors.length) {
                t.colors.forEach(c => {
                    colorHtml += `<span style="display:inline-block; width:12px; height:12px; border-radius:50%; background:${c}; border:1px solid var(--glass-border);"></span>`;
                });
            }

            el.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-weight:500;">${t.name}</span>
                    <div style="display:flex; gap:4px; margin-left:auto;">${colorHtml}</div>
                </div>
            `;

            el.onclick = async () => {
                await fetch('/api/schemes/active', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ theme: t.name })
                });
                this.renderSchemesTab(container);
            };
            list.appendChild(el);
        });
    },

    // ... (Snippets Tab code remains unchanged)
    renderSnippetsTab: async function (container) {
        const res = await fetch('/api/snippets');
        const data = await res.json();
        this.state.configData.snippets = data.snippets || [];

        container.innerHTML = `
            <div class="config-section">
                <h3>Code Snippets</h3>
                <p>Reusable code snippets for your documents</p>
                <div id="snippets-list"></div>
                <div style="margin-top: 16px;">
                    <button class="btn btn-secondary" onclick="app.addSnippet()"><i data-lucide="plus"></i> Add</button>
                </div>
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

        // Re-initialize Lucide icons
        if (window.lucide) lucide.createIcons();
    },

    updateSnippet: function (index, field, value) {
        this.state.configData.snippets[index][field] = value;
        this.debouncedSaveSnippets();
    },

    addSnippet: function () {
        this.state.configData.snippets.push({ name: 'new', definition: '[]' });
        this.renderSnippetsList();
        this.saveSnippets();
    },

    deleteSnippet: function (index) {
        this.state.configData.snippets.splice(index, 1);
        this.renderSnippetsList();
        this.saveSnippets();
    },

    saveSnippets: async function () {
        await fetch('/api/snippets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ snippets: this.state.configData.snippets })
        });
        this.showSaveStatus('Snippets Saved');
    },

    renderPrefaceTab: async function (container) {
        const res = await fetch('/api/preface');
        const data = await res.json();

        container.innerHTML = `
            <div class="config-section">
                <h3>Preface</h3>
                <p>Content displayed before the table of contents</p>
                <div class="preface-editor-container">
                    <div id="preface-monaco"></div>
                </div>
            </div>
        `;

        // Create Monaco editor for preface
        if (window.monaco) {
            this.state.prefaceEditor = monaco.editor.create(document.getElementById('preface-monaco'), {
                value: data.content || '',
                language: 'markdown',
                theme: this.state.editorTheme,
                automaticLayout: true,
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
                minimap: { enabled: false },
                padding: { top: 16 },
                wordWrap: 'on',
                lineNumbers: 'on'
            });

            this.state.prefaceEditor.onDidChangeModelContent(() => {
                this.debouncedSavePreface();
            });
        }

        if (window.lucide) lucide.createIcons();
    },

    savePreface: async function () {
        let content = '';
        if (this.state.prefaceEditor) {
            content = this.state.prefaceEditor.getValue();
        } else {
            content = document.getElementById('preface-content')?.value || '';
        }
        await fetch('/api/preface', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        this.showSaveStatus('Preface Saved');
    },

    renderIgnoredTab: async function (container) {
        const res = await fetch('/api/indexignore');
        const data = await res.json();
        this.state.configData.patterns = data.patterns || [];

        container.innerHTML = `
            <div class="config-section">
                <h3>Ignored Patterns</h3>
                <p>Files and folders to exclude from the project</p>
                <div id="ignored-list"></div>
                <div style="margin-top: 16px;">
                    <button class="btn btn-secondary" onclick="app.addIgnoredPattern()"><i data-lucide="plus"></i> Add Pattern</button>
                </div>
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

        // Re-initialize Lucide icons
        if (window.lucide) lucide.createIcons();
    },

    updateIgnoredPattern: function (index, value) {
        this.state.configData.patterns[index] = value;
        this.debouncedSaveIgnored();
    },

    addIgnoredPattern: function () {
        this.state.configData.patterns.push('');
        this.renderIgnoredList();
        this.saveIgnored();
    },

    deleteIgnoredPattern: function (index) {
        this.state.configData.patterns.splice(index, 1);
        this.renderIgnoredList();
        this.saveIgnored();
    },

    saveIgnored: async function () {
        await fetch('/api/indexignore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patterns: this.state.configData.patterns })
        });
        this.showSaveStatus('Patterns Saved');
    },

    renderModulesTab: async function (container) {
        const res = await fetch('/api/modules');
        const modules = await res.json();
        console.log("Modules data:", modules);

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

            let actionHtml = '';
            if (info.has_config) {
                // Pass full name to configureModule
                actionHtml = `
                    <button onclick="app.configureModule('${name}')" class="icon-btn" title="Configure">
                        <i data-lucide="settings"></i>
                    </button>
                `;
            }

            el.innerHTML = `
                <div class="module-info">
                    <div class="module-name">${cleanName}</div>
                    <div class="module-meta">
                        <span class="module-source">${info.source}</span>
                        <span class="module-status">${info.status.toUpperCase()}</span>
                    </div>
                </div>
                ${actionHtml}
            `;
            list.appendChild(el);
        });

        if (window.lucide) lucide.createIcons();
    },

    // ============================================================
    // BUILD MODAL
    // ============================================================

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

        // Add "Select All" toggle
        const selectAllContainer = document.createElement('div');
        selectAllContainer.style.padding = '0 0 16px 0';
        selectAllContainer.style.borderBottom = '1px solid var(--glass-border)';
        selectAllContainer.style.marginBottom = '16px';
        selectAllContainer.innerHTML = `
            <label class="toggle-option">
                <input type="checkbox" checked onchange="app.toggleAllBuild(this.checked)">
                <span style="font-weight: 600;">Select All</span>
            </label>
        `;
        grid.appendChild(selectAllContainer);

        data.chapters.forEach((ch, chIdx) => {
            const group = document.createElement('div');
            group.className = 'build-group';

            // Chapter Header
            const header = document.createElement('div');
            header.className = 'chapter-header';
            header.innerHTML = `
                <label class="toggle-option" style="margin:0;">
                    <input type="checkbox" checked onchange="app.toggleChapterBuild(${chIdx}, this.checked)">
                    <span style="font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">Chapter ${ch.id}</span>
                </label>
            `;
            group.appendChild(header);

            // Container for pages (horizontal scroll)
            const pagesContainer = document.createElement('div');
            pagesContainer.className = 'chapter-pages';

            ch.pages.forEach(p => {
                const cell = document.createElement('div');
                cell.className = 'grid-cell selected';
                cell.dataset.chapterIdx = chIdx;
                cell.dataset.id = p.id;
                cell.dataset.chapter = ch.id;

                // Content
                cell.innerHTML = `
                    <div class="page-num">${p.id}</div>
                    <div class="page-title">${p.path.split('/').pop()}</div> <!-- Show filename -->
                `;

                cell.onclick = () => {
                    cell.classList.toggle('selected');
                    app.updateBuildToggles();
                };

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

    updateBuildToggles: function () {
        // Logic to update intermediate states of checkboxes could go here if needed
    },

    runBuild: async function () {
        const targets = [];
        document.querySelectorAll('.grid-cell.selected').forEach(cell => {
            targets.push({
                chapter: parseInt(cell.dataset.chapterIdx),  // Use chapterIdx (index into hierarchy array)
                page: parseInt(cell.dataset.id) - 1  // page ID to 0-based index
            });
        });

        const options = {
            frontmatter: document.getElementById('opt-frontmatter').checked,
            covers: document.getElementById('opt-covers').checked
        };

        // Show progress
        const progress = document.getElementById('build-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressPage = document.getElementById('progress-page');
        const progressPercent = document.getElementById('progress-percent');
        const log = document.getElementById('build-log');
        const buildBtn = document.getElementById('build-btn');

        progress.style.display = 'block';
        log.style.display = 'none';
        buildBtn.disabled = true;
        buildBtn.innerHTML = '<i data-lucide="loader"></i> Building...';

        progressPage.textContent = 'Preparing...';
        progressPercent.textContent = '0%';
        progressFill.style.width = '0%';

        const res = await fetch('/api/build', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ targets, options })
        });
        const result = await res.json();

        // Update progress to 100%
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';

        buildBtn.disabled = false;
        buildBtn.innerHTML = '<i data-lucide="zap"></i> Build PDF';

        if (result.success) {
            progressPage.textContent = 'Build complete!';
            log.style.display = 'block';
            log.textContent = 'Success! Downloading PDF...';
            log.style.color = 'var(--success)';
            // Create a temporary link with cache-busting timestamp
            const a = document.createElement('a');
            a.href = '/api/download/output.pdf?t=' + Date.now();
            a.download = 'output.pdf';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            progressPage.textContent = 'Build failed';
            log.style.display = 'block';
            log.textContent = result.output || 'Unknown error';
            log.style.color = 'var(--danger)';
        }

        if (window.lucide) lucide.createIcons();
    },

    // ============================================================
    // WEBSOCKET / PREVIEW
    // ============================================================

    connectWebSocket: function () {
        if (this.state.wsRetryCount === undefined) {
            this.state.wsRetryCount = 0;
        }

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.state.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            this.state.ws.onopen = () => {
                console.log('WebSocket connected');
                this.state.wsRetryCount = 0; // Reset on successful connection
            };

            this.state.ws.onmessage = (e) => {
                const msg = JSON.parse(e.data);
                if (msg.type === 'init' || msg.type === 'update') {
                    this.updatePreview(msg.updates);
                }
            };

            this.state.ws.onclose = () => {
                // Exponential backoff: 2s, 4s, 8s, 16s, max 30s
                const delay = Math.min(2000 * Math.pow(2, this.state.wsRetryCount), 30000);
                this.state.wsRetryCount++;
                console.log(`WebSocket closed, reconnecting in ${delay / 1000}s...`);
                setTimeout(() => this.connectWebSocket(), delay);
            };

            this.state.ws.onerror = (e) => {
                // Silently handle errors, onclose will trigger reconnect
            };
        } catch (e) {
            console.error('WebSocket error:', e);
        }
    },

    updatePreview: function (updates) {
        const container = document.getElementById('preview-container');

        // Clear placeholder
        if (container.querySelector('.preview-placeholder')) {
            container.innerHTML = '';
        }

        updates.forEach(u => {
            let img = document.getElementById(`page-${u.page}`);
            if (!img) {
                img = document.createElement('img');
                img.id = `page-${u.page}`;
                img.className = 'page-img';
                container.appendChild(img);
            }
            img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(u.svg);

            // Store numeric index for sorting
            img.dataset.index = u.page;
        });

        // Sort pages
        const pages = Array.from(container.children).sort((a, b) => {
            return parseInt(a.dataset.index) - parseInt(b.dataset.index);
        });

        pages.forEach(p => container.appendChild(p));
    },

    // ============================================================
    // STATUS
    // ============================================================

    loadStatus: async function () {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            const el = document.getElementById('project-name');
            if (el) el.textContent = data.project;
        } catch (e) {
            console.error('Status load failed', e);
        }
    },

    renderSessionTab: function (container) {
        container.innerHTML = `
            <div class="config-section">
                <h3>Session Settings</h3>
                <p>Configure your appearance in collaboration sessions</p>
                
                <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" id="session-name" value="${this.state.sessionName}" oninput="app.updateSessionName(this.value)" placeholder="Anonymous">
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
                        This name will be visible to other users editing the same file. It is saved in your browser storage.
                    </p>
                </div>
            </div>
        `;
    },

    updateSessionName: function (name) {
        this.state.sessionName = name || 'Anonymous';
        localStorage.setItem('sessionName', this.state.sessionName);

        if (this.collab) {
            this.collab.setIdentity(this.state.sessionName);
        }

        this.showSaveStatus('Name Updated');
    },

    configureModule: async function (name) {
        const res = await fetch(`/api/modules/${name}/config`);
        const data = await res.json();
        const settings = data.settings;

        if (!settings || settings.length === 0) {
            this.showSaveStatus('No configuration available');
            return;
        }

        // Create or get modal overlay (not just modal)
        let overlay = document.getElementById('config-modal-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'config-modal-overlay';
            overlay.className = 'modal-overlay'; // This gives fixed position & backdrop
            overlay.innerHTML = `
                <div class="modal">
                    <div class="modal-header">
                        <h2>Configure Module</h2>
                        <button onclick="document.getElementById('config-modal-overlay').classList.remove('active')" class="icon-btn-small">
                            <i data-lucide="x"></i>
                        </button>
                    </div>
                    <div id="module-config-form" style="display: flex; flex-direction: column; gap: 16px; margin-top: 16px;"></div>
                    <div class="build-actions" style="margin-top: 24px;">
                        <button id="save-module-config-btn" class="btn btn-primary">Save Changes</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }

        // Render form
        this.renderModuleConfig(name, settings);

        // Show modal
        overlay.classList.add('active');
        if (window.lucide) lucide.createIcons();
    },

    renderModuleConfig: function (name, settings) {
        const form = document.getElementById('module-config-form');
        form.innerHTML = '';

        // Configure Save Button
        document.getElementById('save-module-config-btn').onclick = () => this.saveModuleConfig(name);

        // Populate form
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
                    option.value = opt;
                    option.textContent = opt;
                    if (opt === setting.value) option.selected = true;
                    input.appendChild(option);
                });
            } else if (setting.type === 'bool') {
                // For bool we use the toggle-option structure
                group.className = 'toggle-option';
                group.innerHTML = ''; // Clear previous structure
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
            let value;

            if (type === 'bool') value = input.checked;
            else if (type === 'int') value = parseInt(input.value);
            else value = input.value;

            config[key] = value;
        });

        await fetch(`/api/modules/${name}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        document.getElementById('config-modal').classList.remove('active');
        this.showSaveStatus('Configuration Saved');
    },

    // ============================================================
    // USERS & PRESENCE
    // ============================================================

    updateOnlineUsers: function (users) {
        const container = document.getElementById('online-users');
        if (!container) return;

        container.innerHTML = '';
        users.forEach(user => {
            if (user.id === this.state.user?.id) return; // Don't show self

            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.style.backgroundColor = user.color;
            avatar.title = user.name;

            // Initials
            const nameParts = user.name.split(' ');
            const initials = nameParts.length > 1
                ? nameParts[0][0] + nameParts[nameParts.length - 1][0]
                : user.name.substring(0, 2);
            avatar.textContent = initials.toUpperCase();

            avatar.onclick = () => this.jumpToUser(user);
            container.appendChild(avatar);
        });
    },

    jumpToUser: function (user) {
        if (!this.state.editor || !user.cursor) return;

        const position = {
            lineNumber: user.cursor.line,
            column: user.cursor.column
        };

        this.state.editor.revealPositionInCenter(position);
        this.state.editor.setPosition(position);
        this.state.editor.focus();
    },

    // ============================================================
    // CHAT
    // ============================================================

    toggleChat: function () {
        const panel = document.getElementById('chat-panel');
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            document.getElementById('chat-input').focus();
            this.scrollChatToBottom();
        }
    },

    handleChatKey: function (e) {
        if (e.key === 'Enter') {
            this.sendChatMessage();
        }
    },

    sendChatMessage: function () {
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text) return;

        if (this.collab) {
            this.collab.sendChat(text);
            input.value = '';
        }
    },

    receiveChatMessage: function (msg) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        const isSelf = msg.userId === this.state.user?.id;

        div.className = `chat-message ${isSelf ? 'self' : 'other'}`;

        const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const colorStyle = msg.color ? `background-color: ${msg.color};` : 'background-color: #888;';
        const nameStyle = msg.color ? `color: ${msg.color}; font-weight: 600;` : '';

        div.innerHTML = `
            <div class="chat-meta">
                <span class="chat-user-group">
                    <span class="chat-dot" style="${colorStyle}"></span>
                    <span style="${nameStyle}">${msg.name}</span>
                </span>
                <span>${time}</span>
            </div>
            <div class="chat-text">${msg.text}</div>
        `;

        container.appendChild(div);
        this.scrollChatToBottom();

        // Show indicator if chat is hidden
        const panel = document.getElementById('chat-panel');
        if (panel.classList.contains('hidden') && !isSelf) {
            // Optional: Add notification dot logic here
        }
    },

    scrollChatToBottom: function () {
        const container = document.getElementById('chat-messages');
        container.scrollTop = container.scrollHeight;
    }
};

// Initialize on load
window.onload = () => app.init();
window.app = app;


