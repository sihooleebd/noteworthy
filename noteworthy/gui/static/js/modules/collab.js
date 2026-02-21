// ============================================================
// COLLAB MODULE
//
// Packet routing:
//   /yjs  (y-monaco + MonacoBinding)  -> Content sync only.
//   /ws/doc (docSocket)               -> Chat, Preview, Presence, Cursors.
//
// No Yjs Awareness used. Cursors and presence are handled entirely
// via docSocket JSON messages.
// ============================================================

(function () {
    const CollabMixin = {
        // --------------------------------------------------------
        // WebSocket (DocumentHub) - NON-YJS functionality only
        // --------------------------------------------------------
        connectDocSocket: function () {
            if (this.state.wsRetryCount === undefined) this.state.wsRetryCount = 0;
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const name = encodeURIComponent(this.state.sessionName);

                // Keep one ID per browser runtime tab. We intentionally do not
                // reuse a copied sessionStorage value from duplicated tabs.
                let clientId = this.state.docClientId;
                if (!clientId) {
                    clientId = (window.crypto && window.crypto.randomUUID)
                        ? window.crypto.randomUUID()
                        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
                    sessionStorage.setItem('noteworthy_client_id', clientId);
                    this.state.docClientId = clientId;
                }

                // Include token so the server can include it in user_joined/welcome payloads
                const token = this.state.userToken || '';
                this.state.docSocket = new WebSocket(
                    `${protocol}//${window.location.host}/ws/doc?name=${name}&id=${clientId}&token=${token}`);

                // Wrap send for debugging
                const originalSend = this.state.docSocket.send;
                this.state.docSocket.send = function (data) {
                    if (window.__NOTEWORTHY_DEBUG_PACKETS) {
                        try {
                            console.log('[Doc OUT]', JSON.parse(data));
                        } catch (e) {
                            console.log('[Doc OUT]', data);
                        }
                    }
                    originalSend.apply(this, arguments);
                };

                this.state.docSocket.onopen = () => {
                    console.log('[Doc] Connected');
                    this.state.wsRetryCount = 0;
                    if (this.state.activeFile) this.joinFile(this.state.activeFile);
                };

                this.state.docSocket.onmessage = (e) => {
                    let msg;
                    try {
                        msg = JSON.parse(e.data);
                    } catch (err) {
                        console.warn('[Doc] Ignoring malformed message:', e.data);
                        return;
                    }
                    if (window.__NOTEWORTHY_DEBUG_PACKETS) {
                        console.log('[Doc IN]', msg);
                    }
                    this.handleDocMessage(msg);
                };

                this.state.docSocket.onclose = () => {
                    const delay = Math.min(2000 * Math.pow(2, this.state.wsRetryCount), 30000);
                    this.state.wsRetryCount++;
                    console.log(`[Doc] Disconnected, reconnecting in ${delay / 1000}s...`);
                    setTimeout(() => this.connectDocSocket(), delay);
                };

                this.state.docSocket.onerror = (e) => {
                    console.error('[Doc] WebSocket error:', e);
                };
            } catch (e) {
                console.error('[Doc] Connection error:', e);
            }
        },

        handleDocMessage: function (msg) {
            switch (msg.type) {
                // ---- Presence / Identity ----
                case 'welcome':
                    this.state.userId = msg.userId;
                    // Do NOT overwrite state.userColor — it's the stable localStorage color
                    // used in cursor messages. msg.color is the server's rotating palette color.
                    console.log(`[Doc] Welcomed as ${msg.userId} (server color: ${msg.color})`);
                    if (msg.users && Array.isArray(msg.users)) {
                        this._initOnlineUsers(msg.users);
                    }
                    break;

                case 'user_joined':
                case 'user_left':
                case 'user_updated':
                    this.updateUserPresence(msg);
                    break;

                // ---- Chat ----
                case 'chat':
                    this.addChatMessage(msg);
                    break;

                // ---- Preview / Diagnostics ----
                case 'preview':
                    this.updatePreview(msg.updates);
                    break;

                case 'diagnostics':
                    this.applyDiagnostics(msg.diagnostics);
                    break;

                // ---- Remote cursors (custom, low-latency, via docSocket) ----
                case 'cursor':
                    this._applyRemoteCursor(msg);
                    break;

                // ---- Ignored (handled by Yjs) ----
                case 'init':
                case 'content':
                case 'operation':
                case 'ack':
                case 'resync':
                case 'users':
                case 'delta':
                    // Legacy Emacs-bridge or Yjs-layer packets — ignore here.
                    break;

                default:
                    console.warn('[Doc] Unknown message type:', msg.type);
            }
        },

        _onlineUsersRenderPending: false,
        _scheduleRenderOnlineUsers: function () {
            if (this._onlineUsersRenderPending) return;
            this._onlineUsersRenderPending = true;
            requestAnimationFrame(() => {
                this._onlineUsersRenderPending = false;
                this.renderOnlineUsers();
            });
        },

        renderOnlineUsers: function () {
            const container = document.getElementById('online-users');
            if (!container) return;
            container.innerHTML = '';

            // Avatar list driven entirely by docSocket presence (state.onlineUsers).
            const users = this.state.onlineUsers || {};
            const myId = this.state.userId;
            console.log('[Collab] renderOnlineUsers: onlineUsers=', Object.keys(users), 'myId=', myId);

            Object.values(users).forEach(user => {
                if (user.id === myId) return; // skip self

                const name = user.name || 'Anonymous';
                const color = user.color || '#888';
                const currentFile = user.file || null;
                const fileLabel = currentFile ? currentFile.split('/').pop() : '?';

                const avatar = document.createElement('div');
                avatar.className = 'user-avatar';
                avatar.style.backgroundColor = color;
                avatar.title = `${name} \u2192 ${fileLabel}\nClick to follow`;
                avatar.textContent = name.charAt(0).toUpperCase();
                avatar.onclick = () => this._followPeer(user.id, currentFile);
                container.appendChild(avatar);
            });
        },

        // Follow a peer: if different file, open it; then jump to their last cursor pos.
        _followPeer: function (peerId, peerFile) {
            const follow = () => {
                if (!this.state.editor) return;
                const key = peerId == null ? null : String(peerId);
                const cursor = key ? this._remoteCursors[key] : null;
                if (!cursor) { console.warn('[Follow] No cursor data for peer'); return; }
                const model = this.state.editor.getModel();
                if (!model) return;
                const maxLine = Math.max(1, model.getLineCount());
                const line = Math.min(Math.max(1, cursor.line || 1), maxLine);
                const col = Math.min(Math.max(1, cursor.col || 1), model.getLineMaxColumn(line));
                this.state.editor.revealLineInCenter(line);
                this.state.editor.setPosition({ lineNumber: line, column: col });
                this.state.editor.focus();
            };

            if (peerFile && peerFile !== this.state.activeFile) {
                this.openFile(peerFile).then(follow);
            } else {
                follow();
            }
        },

        // --------------------------------------------------------
        // User presence events from DocumentHub
        // --------------------------------------------------------
        updateUserPresence: function (msg) {
            if (!this.state.onlineUsers) this.state.onlineUsers = {};

            if (msg.type === 'user_joined' && msg.user) {
                this.state.onlineUsers[msg.user.id] = msg.user;
            } else if (msg.type === 'user_left') {
                const departingUser = this.state.onlineUsers[msg.userId];
                delete this.state.onlineUsers[msg.userId];
                // Clear by user ID (authoritative) and legacy token key if present.
                this._clearRemoteCursor(msg.userId);
                if (departingUser?.token && departingUser.token !== msg.userId) {
                    this._clearRemoteCursor(departingUser.token);
                }
            } else if (msg.type === 'user_updated' && msg.user) {
                this.state.onlineUsers[msg.user.id] = {
                    ...(this.state.onlineUsers[msg.user.id] || {}),
                    ...msg.user
                };
            }
            // Avatar list is now docSocket-driven — re-render on every presence event.
            this._scheduleRenderOnlineUsers();
        },

        _initOnlineUsers: function (users) {
            this.state.onlineUsers = {};
            users.forEach(u => { this.state.onlineUsers[u.id] = u; });
            this._scheduleRenderOnlineUsers();
        },

        // --------------------------------------------------------
        // Remote cursor rendering (via docSocket, absolute line/col)
        // --------------------------------------------------------
        // Stores: { userId -> { decorationIds: [], color, name, file, line, col, token } }
        _remoteCursors: {},

        _cssSafeId: function (id) {
            return String(id).replace(/[^a-zA-Z0-9_-]/g, '_');
        },
        _normalizeColor: function (value, fallback = '#888') {
            if (typeof value !== 'string') return fallback;
            const v = value.trim();
            if (!v || v === 'undefined' || v === 'null') return fallback;
            if (window.CSS && typeof window.CSS.supports === 'function') {
                return window.CSS.supports('color', v) ? v : fallback;
            }
            return v;
        },

        _applyRemoteCursor: function (msg) {
            const peerId = msg.userId || msg.token;
            if (!peerId) return;
            const key = String(peerId);
            const toInt = (value, fallback) => {
                const parsed = Number.parseInt(value, 10);
                return Number.isFinite(parsed) ? parsed : fallback;
            };
            const color = this._normalizeColor(msg.color, '#888');

            // Always persist the latest position metadata (for _followPeer lookup).
            const prev = this._remoteCursors[key] || {};
            this._remoteCursors[key] = {
                ...prev,
                token: msg.token || prev.token || null,
                color,
                name: msg.name,
                file: msg.file,
                line: toInt(msg.line, prev.line || 1),
                col: toInt(msg.col, prev.col || 1),
            };

            // Only render decorations in the editor if peer is in the same file.
            if (!this.state.editor || msg.file !== this.state.activeFile) {
                // Clear stale decorations if peer moved to a different file.
                if (prev.decorationIds?.length && this.state.editor) {
                    this.state.editor.deltaDecorations(prev.decorationIds, []);
                }
                this._remoteCursors[key].decorationIds = [];
                return;
            }

            const classSuffix = this._cssSafeId(key);
            this._injectRemoteCursorCSS(classSuffix, color);

            const model = this.state.editor.getModel();
            if (!model) return;

            const maxLine = Math.max(1, model.getLineCount());
            const line = Math.min(Math.max(1, toInt(msg.line, 1)), maxLine);
            const col = Math.min(Math.max(1, toInt(msg.col, 1)), model.getLineMaxColumn(line));

            let selStartLine = Math.min(Math.max(1, toInt(msg.selStartLine, line)), maxLine);
            let selEndLine = Math.min(Math.max(1, toInt(msg.selEndLine, line)), maxLine);
            let selStartCol = Math.min(Math.max(1, toInt(msg.selStartCol, col)), model.getLineMaxColumn(selStartLine));
            let selEndCol = Math.min(Math.max(1, toInt(msg.selEndCol, col)), model.getLineMaxColumn(selEndLine));

            if (selEndLine < selStartLine || (selEndLine === selStartLine && selEndCol < selStartCol)) {
                [selStartLine, selEndLine] = [selEndLine, selStartLine];
                [selStartCol, selEndCol] = [selEndCol, selStartCol];
            }

            const hasSelection = selStartLine !== selEndLine || selStartCol !== selEndCol;

            const decorations = [
                {
                    // Zero-width caret decoration keeps remote cursor visible
                    // even at EOL/empty lines.
                    range: new monaco.Range(line, col, line, col),
                    options: {
                        className: `remote-cursor-${classSuffix}`,
                        showIfCollapsed: true,
                        zIndex: 50,
                        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                        hoverMessage: { value: msg.name || 'Peer' },
                    }
                }
            ];

            if (hasSelection) {
                decorations.push({
                    range: new monaco.Range(
                        selStartLine, selStartCol,
                        selEndLine, selEndCol
                    ),
                    options: {
                        className: `remote-selection-${classSuffix}`,
                        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                    }
                });
            }

            const prevIds = prev.decorationIds || [];
            const nextIds = this.state.editor.deltaDecorations(prevIds, decorations);
            this._remoteCursors[key] = {
                ...this._remoteCursors[key],
                line,
                col,
                decorationIds: nextIds
            };
        },

        _clearRemoteCursor: function (key) {
            const cursorKey = String(key);
            const cursor = this._remoteCursors[cursorKey];
            if (!cursor) return;
            if (this.state.editor && cursor.decorationIds?.length) {
                this.state.editor.deltaDecorations(cursor.decorationIds, []);
            }
            delete this._remoteCursors[cursorKey];
        },

        // Clear all remote cursor decorations (call on file switch).
        // Keep last known metadata for cross-document follow.
        clearAllRemoteCursors: function () {
            Object.keys(this._remoteCursors).forEach((key) => {
                const cursor = this._remoteCursors[key];
                if (this.state.editor && cursor.decorationIds?.length) {
                    this.state.editor.deltaDecorations(cursor.decorationIds, []);
                }
                this._remoteCursors[key] = { ...cursor, decorationIds: [] };
            });
        },
        _injectRemoteCursorCSS: function (classSuffix, color) {
            const styleId = `remote-style-${classSuffix}`;
            const css = `
                .remote-cursor-${classSuffix} {
                    border-left: 2px solid ${color};
                    margin-left: -1px;
                    box-sizing: border-box;
                    pointer-events: none;
                }
                .remote-selection-${classSuffix} {
                    background-color: ${color}40;
                    pointer-events: none;
                }
            `;
            const existing = document.getElementById(styleId);
            if (existing) {
                if (existing.textContent !== css) existing.textContent = css;
                return;
            }
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = css;
            document.head.appendChild(style);
        },

        // --------------------------------------------------------
        // Diagnostics
        // --------------------------------------------------------
        applyDiagnostics: function (diagnostics) {
            if (!this.state.editor) return;
            monaco.editor.setModelMarkers(this.state.editor.getModel(), 'owner', []);

            const errorCountEl = document.getElementById('error-count');
            if (diagnostics && diagnostics.length > 0) {
                const markers = diagnostics.map(d => ({
                    severity: monaco.MarkerSeverity.Error,
                    startLineNumber: d.line,
                    startColumn: d.col,
                    endLineNumber: d.line,
                    endColumn: d.col + 10,
                    message: d.message
                }));
                monaco.editor.setModelMarkers(this.state.editor.getModel(), 'owner', markers);
                if (errorCountEl) errorCountEl.style.display = 'none';
            } else {
                if (errorCountEl) errorCountEl.style.display = 'none';
            }
        },
    };

    window._collabMixin = CollabMixin;
})();
