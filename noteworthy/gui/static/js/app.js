/**
 * Noteworthy GUI - Main Application (Core)
 *
 * Module files loaded first (see index.html), in order:
 *   js/modules/utils.js       - Shared helpers
 *   js/modules/file_tree.js   - File tree & file CRUD
 *   js/modules/collab.js      - WebSocket, Yjs Awareness cursors, user presence
 *   js/modules/config.js      - Config tab panels
 *   js/modules/build.js       - Build page/modal
 *   js/modules/chat.js        - Chat panel
 *   js/modules/preview.js     - SVG preview / source-map clicks
 */

const app = {
    state: {
        activeFile: null,
        editor: null,
        ws: null,
        configData: {},
        editorTheme: localStorage.getItem('editorTheme') || 'vs-dark',
        sessionName: localStorage.getItem('sessionName') || 'Anonymous',

        // Yjs — per-file (recreated on each openFile, content sync only)
        ydoc: null,
        yjsProvider: null,
        yjsBinding: null,

        // Identity (stable across file switches, from localStorage)
        userToken: null,
        userColor: null,

        // Cursor / presence
        userId: null,
        onlineUsers: {},
        remoteCursorDecorations: [],
        externalCursorDecorations: {},
        projectPath: null,
    },

    ASCII_LOGO: "         ,--. \n       ,--.'| \n   ,--,:  : | \n,`--.'`|  ' : \n|   :  :  | | \n:   |   \\ | : \n|   : '  '; | \n'   ' ;.    ; \n|   | | \\   | \n'   : |  ; .' \n|   | `--'   \n'   : |       \n;   |.'       \n'---'         ",

    SIMPLE_ICONS: {
        'typ': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M12.654 17.846c0 1.114.16 1.861.479 2.242.32.381.901.572 1.743.572.872 0 1.99-.44 3.356-1.319l.871 1.45C16.547 22.931 14.44 24 12.785 24c-1.656 0-2.964-.395-3.922-1.187-.959-.82-1.438-2.256-1.438-4.307V6.989H5.246l-.349-1.626 2.528-.791V2.418L12.654 0v4.835l5.142-.395-.48 2.857-4.662-.176v10.725Z"/></svg>',
        'json': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M5.759 3.975h1.783V5.76H5.759V9.33C5.759 11.116 4.418 12 2.875 12H1.092v-1.784h1.783c.593 0 1.09-.297 1.09-.89V5.759c0-1.04.644-1.584 1.387-1.783-.743-.2-1.387-.744-1.387-1.783V.099H4.965l-.001 3.876zm12.482 0H16.46V5.76h1.783V9.33C18.241 11.116 19.582 12 21.125 12h1.783v-1.784h-1.783c-.594 0-1.09-.297-1.09-.89V5.759c0-1.04-.645-1.584-1.388-1.783.743-.2 1.388-.744 1.388-1.783V.099h-1.783l-.001 3.876z"/></svg>',
        'py': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05z"/></svg>',
        'js': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M0 0h24v24H0V0zm22.034 18.276c-.175-1.095-.888-2.015-3.003-2.873-.736-.345-1.554-.585-1.797-1.14-.091-.33-.105-.51-.046-.705.15-.646.915-.84 1.515-.66.39.12.75.42.976.9 1.034-.676 1.755-1.125 1.755-1.125-.27-.42-.404-.601-.586-.78-.63-.705-1.469-1.065-2.834-1.034l-.705.089c-.676.165-1.32.525-1.71 1.005-1.14 1.291-.811 3.541.569 4.471 1.365 1.02 3.361 1.244 3.616 2.205.24 1.17-.87 1.545-1.966 1.41-.811-.18-1.26-.586-1.755-1.336l-1.83 1.051c.21.48.45.689.81 1.109 1.74 1.756 6.09 1.666 6.871-1.004.029-.09.24-.705.074-1.65l.046.067zm-8.983-7.245h-2.248c0 1.938-.009 3.864-.009 5.805 0 1.232.063 2.363-.138 2.711-.33.689-1.18.601-1.566.48-.396-.196-.597-.466-.83-.855-.063-.105-.11-.196-.127-.196l-1.825 1.125c.305.63.75 1.172 1.324 1.517.855.51 2.004.675 3.207.405.783-.226 1.458-.691 1.811-1.411.51-.93.402-2.07.397-3.346.012-2.054 0-4.109 0-6.179l.004-.056z"/></svg>',
        'css': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M0 0v20.16A3.84 3.84 0 0 0 3.84 24h16.32A3.84 3.84 0 0 0 24 20.16V3.84A3.84 3.84 0 0 0 20.16 0Z"/></svg>',
        'html': '<svg class="tree-file" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;margin-left:20px;fill:currentColor;"><path d="M1.5 0h21l-1.91 21.563L11.977 24l-8.564-2.438L1.5 0zm7.031 9.75l-.232-2.718 10.059.003.23-2.622L5.412 4.41l.698 8.01h9.126l-.326 3.426-2.91.804-2.955-.81-.188-2.11H6.248l.33 4.171L12 19.351l5.379-1.443.744-8.157H8.531z"/></svg>',
    },

    getFileIcon: function (filename) {
        const ext = filename.split('.').pop()?.toLowerCase();
        if (this.SIMPLE_ICONS[ext]) return { type: 'svg', value: this.SIMPLE_ICONS[ext] };
        return { type: 'lucide', value: 'file' };
    },

    // ============================================================
    // INITIALIZATION
    // ============================================================

    init: async function () {
        // Wire in module mixins
        Object.assign(this, window._utilsMixin || {});
        Object.assign(this, window._fileTreeMixin || {});
        Object.assign(this, window._collabMixin || {});
        Object.assign(this, window._configMixin || {});
        Object.assign(this, window._buildMixin || {});
        Object.assign(this, window._chatMixin || {});
        Object.assign(this, window._previewMixin || {});

        // Settings sidebar tabs need explicit click handlers in the
        // collaborative GUI, just like the solo GUI already has.
        document.querySelectorAll('.config-tab').forEach(tab => {
            tab.onclick = () => this.showConfigTab(tab.dataset.tab);
        });

        // Debounced config saves
        this.debouncedUpdateMetadata = this.debounce(this.updateMetadata.bind(this), 500);
        this.debouncedUpdateConstants = this.debounce(this.updateConstants.bind(this), 500);
        this.debouncedSaveHierarchy = this.debounce(this.saveHierarchy.bind(this), 800);
        this.debouncedSaveSnippets = this.debounce(this.saveSnippets.bind(this), 500);
        this.debouncedSavePreface = this.debounce(this.savePreface.bind(this), 800);
        this.debouncedSaveIgnored = this.debounce(this.saveIgnored.bind(this), 500);

        await this._initMonaco();

        // Apply saved theme
        if (this.state.editorTheme === 'noteworthy-dark') {
            document.body.removeAttribute('data-theme');
        } else {
            document.body.dataset.theme = this.state.editorTheme;
        }
        const themeSelect = document.getElementById('editor-theme-select');
        if (themeSelect) themeSelect.value = this.state.editorTheme;

        // ── Stable identity ───────────────────────────────────────
        // Must be set BEFORE connectDocSocket() so the URL includes the token.
        let token = localStorage.getItem('nw_token');
        if (!token) {
            token = ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
            localStorage.setItem('nw_token', token);
        }
        this.state.userToken = token;

        let color = localStorage.getItem('nw_color');
        const validStoredColor = typeof color === 'string'
            && color.trim() !== ''
            && color !== 'undefined'
            && color !== 'null'
            && (!window.CSS || !window.CSS.supports || window.CSS.supports('color', color));
        if (!validStoredColor) {
            color = this.getUserColor(token);
            localStorage.setItem('nw_color', color);
        }
        this.state.userColor = color;
        // ─────────────────────────────────────────────────────────

        this.connectDocSocket();

        this.createWelcomeOverlay();

        const container = document.getElementById('monaco-container');
        if (container) container.style.display = 'none';

        await this.refreshTree();
        await this.loadStatus();

        this.showConfigTab('metadata');
        this.initResizer();

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activePage = document.querySelector('.page.active');
                if (activePage && activePage.id === 'page-config') {
                    this.saveCurrentConfigTab();
                    this.showSaveStatus('Changes saved');
                }
            }
        });
    },

    // ============================================================
    // MONACO SETUP
    // ============================================================

    EDITOR_THEMES: null,

    _initMonaco: async function () {
        return new Promise((resolve) => {
            require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
            require(['vs/editor/editor.main'], () => {
                this._defineEditorThemes();
                monaco.editor.setTheme(this.state.editorTheme);

                this.state.editor = monaco.editor.create(document.getElementById('monaco-container'), {
                    value: '',
                    language: 'markdown',
                    theme: this.state.editorTheme,
                    automaticLayout: true,
                    fontSize: 14,
                    fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
                    fontLigatures: true,
                    minimap: { enabled: false },
                    padding: { top: 20, bottom: 20 },
                    scrollBeyondLastLine: false,
                    wordWrap: 'off',
                    lineNumbers: 'on',
                    renderLineHighlight: 'none',
                    overviewRulerLanes: 0,
                    hideCursorInOverviewRuler: true,
                    scrollbar: {
                        vertical: 'auto', horizontal: 'auto',
                        verticalScrollbarSize: 6, horizontalScrollbarSize: 6,
                    },
                    smoothScrolling: true,
                    cursorBlinking: 'smooth',
                    cursorSmoothCaretAnimation: 'on',
                    bracketPairColorization: { enabled: true },
                    guides: { bracketPairs: true },
                    suggest: { showKeywords: true, showSnippets: true },
                });

                // Cursor change -> broadcast position via docSocket (low latency).
                // We do NOT touch Yjs awareness here — MonacoBinding owns that field.
                // Sending via docSocket is async (no Monaco API call), so no recursion risk.
                let _cursorSendTimer = null;
                this.state.editor.onDidChangeCursorSelection((e) => {
                    if (_cursorSendTimer) return; // throttle at 50ms
                    _cursorSendTimer = setTimeout(() => {
                        _cursorSendTimer = null;
                        if (!this.state.docSocket || this.state.docSocket.readyState !== WebSocket.OPEN) return;
                        if (!this.state.activeFile) return;
                        const pos = this.state.editor.getPosition();
                        const sel = this.state.editor.getSelection();
                        if (!pos || !sel) return;
                        this.state.docSocket.send(JSON.stringify({
                            type: 'cursor',
                            file: this.state.activeFile,
                            line: pos.lineNumber,
                            col: pos.column,
                            selStartLine: sel.startLineNumber,
                            selStartCol: sel.startColumn,
                            selEndLine: sel.endLineNumber,
                            selEndCol: sel.endColumn,
                            name: this.state.sessionName,
                            color: this.state.userColor,
                            token: this.state.userToken,
                        }));
                    }, 50);
                });

                // Diagnostics: re-check after edits settle, not on every
                // keystroke — /api/check shells out to `typst compile`, so
                // firing it per-keystroke would spam the process.
                let _diagnosticsDebounceTimer = null;
                this.state.editor.onDidChangeModelContent(() => {
                    if (!this.state.activeFile || !this.state.activeFile.endsWith('.typ')) return;
                    if (_diagnosticsDebounceTimer) clearTimeout(_diagnosticsDebounceTimer);
                    _diagnosticsDebounceTimer = setTimeout(() => {
                        _diagnosticsDebounceTimer = null;
                        this.checkDiagnostics();
                    }, 2000);
                });

                this._setupSmartEditing();
                resolve();
            });
        });
    },

    _setupSmartEditing: function () {
        this.state.editor.onKeyDown((e) => {
            const model = this.state.editor.getModel();
            const pos = this.state.editor.getPosition();
            if (!model || !pos) return;

            if (e.keyCode === monaco.KeyCode.Enter) {
                const line = model.getLineContent(pos.lineNumber);
                const bulletMatch = line.match(/^(\s*)([-*+]|\d+\.)\s/);
                if (bulletMatch) {
                    const lineText = line.trim();
                    if (lineText === '-' || lineText === '*' || lineText === '+' || /^\d+\.$/.test(lineText)) {
                        e.preventDefault();
                        const range = new monaco.Range(pos.lineNumber, 1, pos.lineNumber, line.length + 1);
                        this.state.editor.executeEdits('smart', [{ range, text: '\n' }]);
                        return;
                    }
                    e.preventDefault();
                    const indent = bulletMatch[1];
                    const bullet = bulletMatch[2];
                    let nextBullet = bullet;
                    if (/^\d+$/.test(bullet.replace('.', ''))) nextBullet = (parseInt(bullet) + 1) + '.';
                    const insertText = '\n' + indent + nextBullet + ' ';
                    const range = new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column);
                    this.state.editor.executeEdits('smart', [{ range, text: insertText }]);
                    this.state.editor.setPosition({ lineNumber: pos.lineNumber + 1, column: indent.length + nextBullet.length + 2 });
                }
            }

            if (e.keyCode === monaco.KeyCode.Tab) {
                const line = model.getLineContent(pos.lineNumber);
                if (/^\s*([-*+]|\d+\.)\s/.test(line)) {
                    e.preventDefault();
                    if (e.shiftKey) {
                        if (line.startsWith('  ')) {
                            const range = new monaco.Range(pos.lineNumber, 1, pos.lineNumber, 3);
                            this.state.editor.executeEdits('smart', [{ range, text: '' }]);
                        }
                    } else {
                        const range = new monaco.Range(pos.lineNumber, 1, pos.lineNumber, 1);
                        this.state.editor.executeEdits('smart', [{ range, text: '  ' }]);
                        this.state.editor.setPosition({ lineNumber: pos.lineNumber, column: pos.column + 2 });
                    }
                }
            }
        });
    },

    _defineEditorThemes: function () {
        this.EDITOR_THEMES = {
            'noteworthy-dark': {
                label: 'Noteworthy Dark',
                base: 'vs-dark',
                colors: {
                    'editor.background': '#0d0d0f',
                    'editor.foreground': '#e8e8f0',
                    'editor.lineHighlightBackground': '#16161a',
                    'editor.selectionBackground': '#4ECDC430',
                    'editor.inactiveSelectionBackground': '#4ECDC415',
                    'editorCursor.foreground': '#4ECDC4',
                    'editorLineNumber.foreground': '#3a3a4a',
                    'editorLineNumber.activeForeground': '#4ECDC4',
                    'editor.findMatchBackground': '#FFE66D30',
                    'editor.findMatchHighlightBackground': '#FFE66D15',
                    'scrollbar.shadow': '#00000000',
                    'scrollbarSlider.background': '#4ECDC420',
                    'scrollbarSlider.hoverBackground': '#4ECDC440',
                    'scrollbarSlider.activeBackground': '#4ECDC460',
                }
            },
            'noteworthy-light': {
                label: 'Noteworthy Light',
                base: 'vs',
                colors: {
                    'editor.background': '#f5f5f7',
                    'editor.foreground': '#1d1d1f',
                    'editor.lineHighlightBackground': '#e8e8ec',
                    'editor.selectionBackground': '#4ECDC440',
                    'editorCursor.foreground': '#0066cc',
                    'editorLineNumber.foreground': '#999aab',
                    'editorLineNumber.activeForeground': '#0066cc',
                }
            },
            'vs-dark': { label: 'VS Dark', base: 'vs-dark', colors: {} },
            'vs': { label: 'VS Light', base: 'vs', colors: {} },
            'hc-black': { label: 'High Contrast', base: 'hc-black', colors: {} },
        };

        Object.entries(this.EDITOR_THEMES).forEach(([id, theme]) => {
            if (id !== 'vs-dark' && id !== 'vs' && id !== 'hc-black') {
                monaco.editor.defineTheme(id, {
                    base: theme.base,
                    inherit: true,
                    rules: [],
                    colors: theme.colors,
                });
            }
        });
    },

    // ============================================================
    // NAVIGATION
    // ============================================================

    showPage: function (pageId) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-' + pageId).classList.add('active');
        document.querySelectorAll('.dock-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageId);
        });
        if (window.lucide) lucide.createIcons();
        if (pageId === 'build') this.renderBuildHierarchy();
    },

    setEditorTheme: function (theme) {
        this.state.editorTheme = theme;
        localStorage.setItem('editorTheme', theme);
        if (theme === 'noteworthy-dark') {
            document.body.removeAttribute('data-theme');
        } else {
            document.body.dataset.theme = theme;
        }
        if (this.state.editor && window.monaco) window.monaco.editor.setTheme(theme);
        this.showSaveStatus('Theme Updated');
    },

    // ============================================================
    // FILE OPEN & YJS LIFECYCLE
    // ============================================================

    openFile: async function (path, el) {
        if (this.state.activeFile === path) {
            document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('selected'));
            if (el) el.classList.add('selected');
            return;
        }

        const overlay = document.getElementById('welcome-overlay');
        if (overlay) overlay.remove();

        document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('selected'));
        if (el) el.classList.add('selected');

        this.state.activeFile = path;
        document.getElementById('active-filename').textContent = path;

        const monacoContainer = document.getElementById('monaco-container');
        const previewContainer = document.getElementById('preview-container');
        const ext = path.split('.').pop().toLowerCase();
        const imageExts = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'];

        if (ext === 'pdf') {
            monacoContainer.style.display = 'none';
            let pdfViewer = document.getElementById('pdf-viewer');
            if (!pdfViewer) {
                pdfViewer = document.createElement('div');
                pdfViewer.id = 'pdf-viewer';
                pdfViewer.style.cssText = 'flex:1;width:100%;height:100%;background:#1e1e1e;border-radius:0 0 20px 20px;overflow:hidden;';
                monacoContainer.parentNode.insertBefore(pdfViewer, monacoContainer.nextSibling);
            }
            pdfViewer.style.display = 'block';
            pdfViewer.innerHTML = '<iframe src="/api/file?path=' + encodeURIComponent(path) + '&raw=1" style="width:100%;height:100%;border:none;"></iframe>';
            previewContainer.innerHTML = '<div class="preview-placeholder"><i data-lucide="file-text"></i><span>Select a .typ file to view preview</span></div>';
            if (window.lucide) lucide.createIcons();
            return;

        } else if (imageExts.includes(ext)) {
            monacoContainer.style.display = 'none';
            let imageViewer = document.getElementById('image-viewer');
            if (!imageViewer) {
                imageViewer = document.createElement('div');
                imageViewer.id = 'image-viewer';
                imageViewer.style.cssText = 'flex:1;width:100%;height:100%;background:#0a0a0a;border-radius:0 0 20px 20px;overflow:auto;display:flex;align-items:center;justify-content:center;padding:20px;';
                monacoContainer.parentNode.insertBefore(imageViewer, monacoContainer.nextSibling);
            }
            imageViewer.style.display = 'flex';
            imageViewer.innerHTML = '<img src="/api/file?path=' + encodeURIComponent(path) + '&raw=1" style="max-width:100%;max-height:100%;object-fit:contain;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.3);">';
            const pdfViewer = document.getElementById('pdf-viewer');
            if (pdfViewer) pdfViewer.style.display = 'none';
            previewContainer.innerHTML = '<div class="preview-placeholder"><i data-lucide="image"></i><span>Select a .typ file to view preview</span></div>';
            if (window.lucide) lucide.createIcons();
            return;

        } else {
            monacoContainer.style.display = 'block';
            if (this.state.editor) this.state.editor.layout();
            const pdfViewer = document.getElementById('pdf-viewer');
            const imageViewer = document.getElementById('image-viewer');
            if (pdfViewer) pdfViewer.style.display = 'none';
            if (imageViewer) imageViewer.style.display = 'none';

            if (path.endsWith('.typ')) {
                previewContainer.innerHTML = '<div class="preview-loading"><div class="skeleton-page"></div><div class="skeleton-page"></div></div>';
            } else {
                previewContainer.innerHTML = '<div class="preview-placeholder"><i data-lucide="file-code"></i><span>Select a .typ file to view preview</span></div>';
                if (window.lucide) lucide.createIcons();
            }
        }

        // ---- Yjs Provider Lifecycle ----
        if (this.state.yjsBinding) {
            this.state.yjsBinding.destroy();
            this.state.yjsBinding = null;
        }
        if (this.state.yjsProvider) {
            this.state.yjsProvider.destroy();
            this.state.yjsProvider = null;
        }
        if (this.state.ydoc) {
            this.state.ydoc.destroy();
        }

        this.state.externalCursorDecorations = {};
        this.state.remoteCursorDecorations = [];
        this.clearAllRemoteCursors();

        if (this.state.editor) {
            this.state.editor.setValue('');
            this.state.editor.updateOptions({ readOnly: true });
        }

        this.state.ydoc = new Y.Doc();
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = wsProtocol + '//' + window.location.host + '/yjs';

        console.log('[Yjs] Connecting to ' + wsUrl + ', room: ' + path);
        this.state.yjsProvider = new WebsocketProvider(
            wsUrl, path, this.state.ydoc,
            { maxBackoffTime: 2500, disableBc: true }
        );

        this.state.yjsProvider.on('status', event => {
            console.log('[Yjs] Status: ' + event.status);
            document.getElementById('save-status').textContent = event.status === 'connected' ? 'Live' : 'Offline';
            if (event.status === 'connected' && this.state.editor) {
                this.state.editor.updateOptions({ readOnly: false });
            }

            // Hook the underlying WebSocket for raw packet debugging.
            // y-websocket recreates provider.ws on each (re)connect.
            if (event.status === 'connected' && window.__NOTEWORTHY_DEBUG_PACKETS) {
                const ws = this.state.yjsProvider.ws;
                if (ws && !ws.__debugPatched) {
                    ws.__debugPatched = true;
                    const room = path;
                    // Python-style b'...' repr: printable ASCII as chars, rest as \xNN
                    const bytesRepr = buf => {
                        let s = "b'";
                        for (const b of buf) {
                            if (b >= 0x20 && b < 0x7f && b !== 0x27 && b !== 0x5c) {
                                s += String.fromCharCode(b);
                            } else {
                                s += '\\x' + b.toString(16).padStart(2, '0');
                            }
                        }
                        return s + "'";
                    };
                    const msgType = t => ['Sync', 'Awareness', 'Auth', 'QueryAwareness'][t] ?? `Type=${t}`;
                    const origOnMessage = ws.onmessage;
                    ws.onmessage = function (e) {
                        if (e.data instanceof ArrayBuffer) {
                            const buf = new Uint8Array(e.data);
                            console.log(`[Yjs] <<< RECV ${room} (${buf.length}b) [${msgType(buf[0])}]`);
                            console.log(bytesRepr(buf));
                        }
                        if (origOnMessage) origOnMessage.call(this, e);
                    };
                    const origSend = ws.send.bind(ws);
                    ws.send = function (data) {
                        if (data instanceof Uint8Array || data instanceof ArrayBuffer) {
                            const buf = data instanceof Uint8Array ? data : new Uint8Array(data);
                            console.log(`[Yjs] >>> SEND ${room} (${buf.length}b) [${msgType(buf[0])}]`);
                            console.log(bytesRepr(buf));
                        }
                        origSend(data);
                    };
                }
            }
        });

        this.state.yjsProvider.on('sync', isSynced => {
            console.log('[Yjs] Sync: ' + isSynced);
            if (isSynced && this.state.editor) {
                this.state.editor.updateOptions({ readOnly: false });
                document.getElementById('save-status').textContent = 'Synced';

                // Render existing peers immediately — 'change' only fires for
                // incremental deltas, not the initial awareness snapshot.
                if (this._scheduleRenderOnlineUsers) this._scheduleRenderOnlineUsers();
                else requestAnimationFrame(() => this.renderOnlineUsers());

                // Focus the editor so MonacoBinding publishes our cursor
                // position to awareness immediately (it tracks cursor via
                // onDidChangeCursorSelection internally).
                requestAnimationFrame(() => this.state.editor.focus());
            }
        });

        // Yjs per-file awareness is still passed to MonacoBinding for its internal
        // content-binding mechanics, but we no longer read or write user identity to it.

        // MonacoBinding
        const ytext = this.state.ydoc.getText('content');
        if (this.state.editor) {
            try {
                this.state.yjsBinding = new MonacoBinding(
                    ytext,
                    this.state.editor.getModel(),
                    new Set([this.state.editor]),
                    this.state.yjsProvider.awareness
                );
                console.log('[Yjs] MonacoBinding created');
                // Render right away — some peers may already be in the
                // awareness map even before the first 'change' event fires.
                if (this._scheduleRenderOnlineUsers) this._scheduleRenderOnlineUsers();
                else requestAnimationFrame(() => this.renderOnlineUsers());
            } catch (e) {
                console.error('[Yjs] Error creating MonacoBinding:', e);
            }
        }

        this.joinFile(path);
    },

    joinFile: function (path) {
        if (this.state.docSocket && this.state.docSocket.readyState === WebSocket.OPEN) {
            this.state.docSocket.send(JSON.stringify({ type: 'join', path }));
        }
    },

    // ============================================================
    // EDITOR HELPERS
    // ============================================================

    // NOTE: no manual save — the Yjs room persists every edit to disk
    // server-side. Posting raw editor text to /api/file here would let a
    // stale tab overwrite collaborators' work.

    toggleErrorDetails: function () {
        const detailsEl = document.getElementById('error-details');
        const chevron = document.querySelector('.error-chevron');
        if (detailsEl) {
            const isVisible = detailsEl.style.display === 'block';
            detailsEl.style.display = isVisible ? 'none' : 'block';
            if (chevron) chevron.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
        }
    },

    checkDiagnostics: async function () {
        if (!this.state.editor || !this.state.activeFile || !this.state.activeFile.endsWith('.typ')) return;
        try {
            const res = await fetch('/api/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: this.state.activeFile })
            });
            const data = await res.json();
            this.applyDiagnostics(data.diagnostics || []);
        } catch (e) {
            console.error('Diagnostic error:', e);
        }
    },

    startSyncVerification: function () { /* placeholder for drift detection */ },

    // ============================================================
    // WELCOME OVERLAY
    // ============================================================

    createWelcomeOverlay: function () {
        const overlay = document.createElement('div');
        overlay.id = 'welcome-overlay';
        const logo = document.createElement('div');
        logo.className = 'ascii-logo';
        logo.textContent = this.ASCII_LOGO;
        const text = document.createElement('div');
        text.className = 'welcome-text';
        text.textContent = 'NOTEWORTHY';
        overlay.appendChild(logo);
        overlay.appendChild(text);
        const container = document.getElementById('monaco-container');
        if (container && container.parentElement) container.parentElement.appendChild(overlay);
    },

    // ============================================================
    // STATUS
    // ============================================================

    loadStatus: async function () {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            this.state.projectPath = data.path || null;
            const el = document.getElementById('project-name');
            if (el) el.textContent = data.project;
        } catch (e) {
            console.error('Status load failed', e);
        }
    },

    // ============================================================
    // RESIZER
    // ============================================================

    initResizer: function () {
        const resizer = document.getElementById('editor-resizer');
        const previewPanel = document.querySelector('.preview-panel');
        const mainContent = document.querySelector('.main-content');
        if (!resizer || !previewPanel || !mainContent) return;

        let isResizing = false;

        resizer.addEventListener('mousedown', () => {
            isResizing = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const containerRect = mainContent.getBoundingClientRect();
            let newWidth = containerRect.right - e.clientX;
            const minWidth = 200, maxWidth = containerRect.width - 200;
            if (newWidth < minWidth) newWidth = minWidth;
            if (newWidth > maxWidth) newWidth = maxWidth;
            previewPanel.style.width = newWidth + 'px';
            if (this.state.editor) this.state.editor.layout();
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                if (this.state.editor) this.state.editor.layout();
            }
        });
    },
};

window.onload = () => app.init();
window.app = app;
