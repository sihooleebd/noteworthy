// ============================================================
// COLLAB MODULE
// Single source of truth for cursor display and user presence.
// Uses Yjs Awareness for cursor sharing between web clients.
// The DocumentHub WebSocket is used for: Emacs cursors (bridged
// from server to Awareness), chat, preview, diagnostics, and
// file join/leave control. Cursor rendering is driven solely
// by Awareness state changes.
// ============================================================

(function () {
    const CollabMixin = {
        // --------------------------------------------------------
        // WebSocket (DocumentHub)
        // --------------------------------------------------------
        connectDocSocket: function () {
            if (this.state.wsRetryCount === undefined) this.state.wsRetryCount = 0;
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const name = encodeURIComponent(this.state.sessionName);

                let clientId = sessionStorage.getItem('noteworthy_client_id');
                if (!clientId) {
                    clientId = Math.random().toString(36).substring(2, 15);
                    sessionStorage.setItem('noteworthy_client_id', clientId);
                }

                this.state.docSocket = new WebSocket(`${protocol}//${window.location.host}/ws/doc?name=${name}&id=${clientId}`);

                this.state.docSocket.onopen = () => {
                    console.log('[Doc] Connected');
                    this.state.wsRetryCount = 0;
                    if (this.state.activeFile) this.joinFile(this.state.activeFile);
                };

                this.state.docSocket.onmessage = (e) => {
                    const msg = JSON.parse(e.data);
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
                case 'joined':
                    // Store our own server-assigned user ID and color
                    this.state.userId = msg.userId;
                    this.state.userColor = msg.color;
                    console.log(`[Doc] Joined as ${msg.userId}`);
                    // Render the initial list of online users
                    if (msg.users && Array.isArray(msg.users)) {
                        this._syncAwarenessFromServerUsers(msg.users);
                    }
                    break;

                case 'init':
                    // File is loaded – set language mode. Content comes via Yjs.
                    if (this.state.editor) {
                        const ext = this.state.activeFile?.split('.').pop() || 'typ';
                        const lang = ext === 'typ' ? 'markdown' : (ext === 'json' ? 'json' : 'plaintext');
                        monaco.editor.setModelLanguage(this.state.editor.getModel(), lang);
                        this.state.docVersion = msg.version || 0;
                        this.state.docHash = msg.hash || '';
                        document.getElementById('save-status').textContent = '';
                        this.startSyncVerification();
                    }
                    break;

                case 'content':
                    // Legacy full-content sync from server (Emacs edits via OT path)
                    if (msg.userId !== this.state.userId && this.state.editor) {
                        this.state.applyingRemote = true;
                        const pos = this.state.editor.getPosition();
                        this.state.editor.setValue(msg.content);
                        this.state.docVersion = msg.version;
                        this.state.docHash = msg.hash;
                        if (pos) {
                            const model = this.state.editor.getModel();
                            const maxLine = model.getLineCount();
                            const newLine = Math.min(pos.lineNumber, maxLine);
                            const newCol = Math.min(pos.column, model.getLineMaxColumn(newLine));
                            this.state.editor.setPosition({ lineNumber: newLine, column: newCol });
                        }
                        this.state.applyingRemote = false;
                    }
                    break;

                case 'operation':
                    // Incremental OT operation from a remote user (e.g., Emacs)
                    if (msg.userId !== this.state.userId && this.state.editor) {
                        this.state.applyingRemote = true;
                        const model = this.state.editor.getModel();
                        const op = msg.op;
                        const cursorPos = this.state.editor.getPosition();
                        const cursorOffset = model.getOffsetAt(cursorPos);

                        if (op.type === 'insert') {
                            const pos = model.getPositionAt(op.position);
                            this.state.editor.executeEdits('remote', [{
                                range: new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column),
                                text: op.text
                            }]);
                            if (op.position <= cursorOffset) {
                                const newPos = model.getPositionAt(cursorOffset + op.text.length);
                                this.state.editor.setPosition(newPos);
                            }
                        } else if (op.type === 'delete') {
                            const startPos = model.getPositionAt(op.position);
                            const endPos = model.getPositionAt(op.position + op.length);
                            this.state.editor.executeEdits('remote', [{
                                range: new monaco.Range(startPos.lineNumber, startPos.column, endPos.lineNumber, endPos.column),
                                text: ''
                            }]);
                            if (op.position + op.length <= cursorOffset) {
                                const newPos = model.getPositionAt(cursorOffset - op.length);
                                this.state.editor.setPosition(newPos);
                            } else if (op.position < cursorOffset) {
                                const newPos = model.getPositionAt(op.position);
                                this.state.editor.setPosition(newPos);
                            }
                        }
                        this.state.docVersion = msg.version;
                        this.state.docHash = msg.hash;
                        this.state.applyingRemote = false;
                    }
                    break;

                case 'ack':
                    this.state.docVersion = msg.version;
                    this.state.docHash = msg.hash;
                    document.getElementById('save-status').textContent = 'Synced';
                    setTimeout(() => document.getElementById('save-status').textContent = '', 1500);
                    break;

                case 'resync':
                    console.log('[Sync] Resync received - applying authoritative content');
                    if (this.state.editor) {
                        this.state.applyingRemote = true;
                        const pos = this.state.editor.getPosition();
                        this.state.editor.setValue(msg.content);
                        this.state.docVersion = msg.version;
                        this.state.docHash = msg.hash;
                        if (pos) {
                            const model = this.state.editor.getModel();
                            const maxLine = model.getLineCount();
                            const newLine = Math.min(pos.lineNumber, maxLine);
                            const newCol = Math.min(pos.column, model.getLineMaxColumn(newLine));
                            this.state.editor.setPosition({ lineNumber: newLine, column: newCol });
                        }
                        this.state.applyingRemote = false;
                    }
                    break;

                case 'cursor':
                    // Cursor from a non-Yjs client (e.g., Emacs). Bridge to Awareness.
                    this._bridgeExternalCursorToAwareness(msg);
                    break;

                case 'preview':
                    this.updatePreview(msg.updates);
                    break;

                case 'diagnostics':
                    this.applyDiagnostics(msg.diagnostics);
                    break;

                case 'user_joined':
                case 'user_left':
                case 'user_updated':
                    this.updateUserPresence(msg);
                    break;

                case 'chat':
                    this.addChatMessage(msg);
                    break;
            }
        },

        // --------------------------------------------------------
        // Awareness-based cursor rendering (Yjs)
        // Called whenever Awareness state changes.
        // --------------------------------------------------------
        renderCursorsFromAwareness: function () {
            if (!this.state.yjsProvider || !this.state.editor) return;
            // Guard against re-entrant calls (Monaco fires model events synchronously
            // during deltaDecorations which can retrigger awareness changes).
            if (this._renderingCursors) return;
            this._renderingCursors = true;

            const awareness = this.state.yjsProvider.awareness;
            const states = awareness.getStates();
            const decorations = [];

            states.forEach((state, clientId) => {
                if (clientId === awareness.clientID) return; // skip self

                const cursor = state.cursor;
                if (!cursor || !cursor.line) return;

                const user = state.user || {};
                const color = user.color || this.getUserColor(clientId);
                const name = user.name || `User ${clientId}`;

                // Inject per-user CSS if not already done
                this._injectUserCss(String(clientId), color);

                // Caret decoration
                decorations.push({
                    range: new monaco.Range(cursor.line, cursor.column, cursor.line, cursor.column),
                    options: {
                        className: `remote-cursor-${clientId}`,
                        hoverMessage: { value: `**${name}**` },
                        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                    }
                });

                // Selection decoration
                if (cursor.selection) {
                    const sel = cursor.selection;
                    decorations.push({
                        range: new monaco.Range(sel.startLine, sel.startColumn, sel.endLine, sel.endColumn),
                        options: {
                            className: `remote-selection-${clientId}`,
                            hoverMessage: { value: `${name}'s selection` },
                            stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                        }
                    });
                }
            });

            try {
                this.state.remoteCursorDecorations = this.state.editor.deltaDecorations(
                    this.state.remoteCursorDecorations || [],
                    decorations
                );
            } finally {
                this._renderingCursors = false;
            }
        },

        // --------------------------------------------------------
        // Online users list (avatars above editor)
        // --------------------------------------------------------
        renderOnlineUsers: function () {
            const container = document.getElementById('online-users');
            if (!container) return;
            container.innerHTML = '';

            if (!this.state.yjsProvider) return;

            const awareness = this.state.yjsProvider.awareness;
            const states = awareness.getStates();

            states.forEach((state, clientId) => {
                if (clientId === awareness.clientID) return; // skip self

                const user = state.user || {};
                const cursor = state.cursor;
                const name = user.name || `User ${clientId}`;
                const color = user.color || this.getUserColor(clientId);

                const avatar = document.createElement('div');
                avatar.className = 'user-avatar';
                avatar.style.backgroundColor = color;
                avatar.style.cursor = 'pointer';
                avatar.title = `${name}\nClick to follow`;
                avatar.textContent = name.charAt(0).toUpperCase();

                avatar.onclick = () => {
                    if (cursor && cursor.line && this.state.editor) {
                        this.state.editor.revealLineInCenter(cursor.line);
                        this.state.editor.setPosition({ lineNumber: cursor.line, column: cursor.column || 1 });
                        this.state.editor.focus();
                    } else {
                        console.warn('[Collab] User has no cursor info in awareness');
                    }
                };

                container.appendChild(avatar);
            });

            // Also show users from DocumentHub that may not be in Yjs (e.g. Emacs clients)
            const docHubUsers = Object.values(this.state.onlineUsers || {});
            const awarenessNames = new Set();
            states.forEach((state) => {
                if (state.user?.name) awarenessNames.add(state.user.name);
            });

            docHubUsers.forEach(user => {
                if (user.id === this.state.userId) return; // skip self
                if (awarenessNames.has(user.name)) return; // already shown via Awareness

                const avatar = document.createElement('div');
                avatar.className = 'user-avatar';
                avatar.style.backgroundColor = user.color || '#888';
                avatar.style.cursor = 'pointer';
                avatar.title = `${user.name} (Emacs)\nClick to follow`;
                avatar.textContent = user.name.charAt(0).toUpperCase();

                avatar.onclick = () => {
                    if (user.file) {
                        this.openFile(user.file);
                        if (user.cursor_line) {
                            setTimeout(() => {
                                if (this.state.editor) {
                                    this.state.editor.revealLineInCenter(user.cursor_line);
                                    this.state.editor.setPosition({
                                        lineNumber: user.cursor_line,
                                        column: user.cursor_column || 1
                                    });
                                    this.state.editor.focus();
                                }
                            }, 200);
                        }
                    }
                };

                container.appendChild(avatar);
            });
        },

        // --------------------------------------------------------
        // User presence events from DocumentHub
        // --------------------------------------------------------
        updateUserPresence: function (msg) {
            if (!this.state.onlineUsers) this.state.onlineUsers = {};

            if (msg.type === 'user_joined') {
                this.state.onlineUsers[msg.user.id] = msg.user;
            } else if (msg.type === 'user_left') {
                delete this.state.onlineUsers[msg.userId];
            } else if (msg.type === 'user_updated' && msg.user) {
                this.state.onlineUsers[msg.user.id] = msg.user;
            }

            this.renderOnlineUsers();
        },

        // --------------------------------------------------------
        // Bridge an external (Emacs) cursor update into Yjs Awareness
        // so web clients can display it via the unified Awareness path.
        // --------------------------------------------------------
        _bridgeExternalCursorToAwareness: function (msg) {
            // We track Emacs cursors in a synthetic awareness-like entry
            // stored on state, then refresh the online users list.
            // Since we can't write to awareness as another clientId,
            // we store them in state.onlineUsers with cursor fields.
            if (!this.state.onlineUsers) this.state.onlineUsers = {};
            if (msg.userId && this.state.onlineUsers[msg.userId]) {
                this.state.onlineUsers[msg.userId].cursor_line = msg.line;
                this.state.onlineUsers[msg.userId].cursor_column = msg.column;
            }
            // Render the external cursor as a decoration
            this._renderExternalCursor(msg);
        },

        _renderExternalCursor: function (msg) {
            if (!this.state.editor || !msg.line) return;

            if (!this.state.externalCursorDecorations) this.state.externalCursorDecorations = {};
            const key = `external-${msg.userId}`;
            const color = msg.color || '#888888';

            this._injectUserCss(key, color);

            const decorations = [{
                range: new monaco.Range(msg.line, msg.column || 1, msg.line, (msg.column || 1) + 1),
                options: {
                    className: `remote-cursor-${key}`,
                    hoverMessage: { value: `**${msg.name || 'Remote'}** (Emacs)` },
                    stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                }
            }];

            if (msg.selectionStartLine && msg.selectionEndLine) {
                decorations.push({
                    range: new monaco.Range(
                        msg.selectionStartLine, msg.selectionStartColumn || 1,
                        msg.selectionEndLine, msg.selectionEndColumn || 1
                    ),
                    options: {
                        className: `remote-selection-${key}`,
                        hoverMessage: { value: `${msg.name || 'Remote'}'s selection` },
                        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
                    }
                });
            }

            this.state.externalCursorDecorations[key] = this.state.editor.deltaDecorations(
                this.state.externalCursorDecorations[key] || [],
                decorations
            );
        },

        // --------------------------------------------------------
        // Sync awareness from server user list on initial 'joined'
        // --------------------------------------------------------
        _syncAwarenessFromServerUsers: function (users) {
            this.state.onlineUsers = {};
            users.forEach(u => {
                this.state.onlineUsers[u.id] = u;
            });
            this.renderOnlineUsers();
        },

        // --------------------------------------------------------
        // CSS injection for dynamic user colors
        // --------------------------------------------------------
        _injectUserCss: function (id, color) {
            const styleId = `user-style-${id}`;
            if (document.getElementById(styleId)) return;
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                .remote-cursor-${id} {
                    border-left: 2px solid ${color};
                    background-color: ${color}25;
                }
                .remote-selection-${id} {
                    background-color: ${color}30;
                }
            `;
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
