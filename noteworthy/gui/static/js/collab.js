/**
 * Noteworthy GUI - Collaboration Manager
 * Handles real-time cursor sharing and user presence
 */
class CollaborationManager {
    constructor(app) {
        this.app = app;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.users = new Map(); // userId -> userData
        this.decorations = new Map(); // userId -> decorationIds
        this.filePath = null;
        this.applyingRemoteChanges = false;
        this.currentIdentity = null;

        // Colors for remote cursors
        this.colors = [
            '#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3',
            '#F38181', '#AA96DA', '#FCBAD3', '#A8D8EA'
        ];
        this.fadeTimers = new Map(); // userId -> timerId
    }

    connect() {
        if (this.ws) {
            return; // Already connected
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/collab`;

        console.log(`Connecting to global collab: ${url}`);

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('Collab connected');
                this.reconnectAttempts = 0;

                // Resend identity if we have one
                if (this.currentIdentity) {
                    this.setIdentity(this.currentIdentity);
                }

                // If we already have a file path active, send it
                if (this.filePath) {
                    this.switchFile(this.filePath);
                }
            };

            this.ws.onmessage = (e) => this.handleMessage(JSON.parse(e.data));

            this.ws.onclose = () => {
                console.log('Collab disconnected');
                this.ws = null;
                // Auto reconnect after a delay
                setTimeout(() => this.connect(), 2000);
            };

        } catch (e) {
            console.error('Collab connection error:', e);
        }
    }

    switchFile(filePath) {
        this.filePath = filePath;
        // Clean up current cursors when switching files
        this.decorations.forEach((_, userId) => {
            if (userId !== this.app.state.user?.id) {
                this.removeCursor(userId);
            }
        });

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'file_focus',
                path: filePath
            }));
        }
    }

    handleMessage(msg) {
        switch (msg.type) {
            case 'joined':
                console.log('Joined collab session', msg);
                // Store my own identity
                this.app.state.user = {
                    id: msg.userId,
                    color: msg.color,
                    name: this.currentIdentity || 'Anonymous'
                };

                // Initialize existing users
                msg.users.forEach(u => this.handleUserJoined(u));
                break;

            case 'user_joined':
                this.handleUserJoined(msg.user);
                break;

            case 'user_left':
                this.handleUserLeft(msg.userId);
                break;

            case 'cursor':
                this.handleCursorUpdate(msg);
                break;

            case 'edit':
                this.handleEdit(msg);
                break;

            case 'user_updated':
                this.handleUserUpdated(msg.user);
                break;

            case 'chat':
                if (this.app.receiveChatMessage) {
                    this.app.receiveChatMessage(msg);
                }
                break;
        }
    }

    handleUserJoined(user) {
        // Assign a color if not provided
        if (!user.color) {
            user.color = this.colors[Math.floor(Math.random() * this.colors.length)];
        }

        this.users.set(user.id, user);

        this.updateUI();
        console.log(`User joined: ${user.name} (${user.id})`);
    }

    updateUI() {
        if (this.app && this.app.updateOnlineUsers) {
            this.app.updateOnlineUsers(Array.from(this.users.values()));
        }
    }

    handleUserUpdated(user) {
        if (this.users.has(user.id)) {
            // Update user data
            const existing = this.users.get(user.id);
            existing.name = user.name;

            // Re-render cursors to update label
            if (this.decorations.has(user.id)) {
                // We need to force a re-render of the style tag
                this.updateUserStyle(user.id, existing.color);
            }
            this.updateUI();
        }
    }

    handleUserLeft(userId) {
        if (this.users.has(userId)) {
            const user = this.users.get(userId);
            console.log(`User left: ${user.name}`);

            // Remove cursor decorations
            this.removeCursor(userId);
            this.users.delete(userId);
            this.updateUI();
        }
    }

    handleCursorUpdate(data) {
        const userId = data.userId;
        if (!this.users.has(userId)) {
            // Should verify user existence, but can lazily add if needed
            this.users.set(userId, {
                id: userId,
                name: data.name || 'Unknown',
                color: data.color || '#ccc'
            });
        }

        const user = this.users.get(userId);
        user.line = data.line;
        user.column = data.column;

        // Update cursor in object structure expected by app.js (optional but safer)
        user.cursor = { line: data.line, column: data.column };

        this.renderCursor(userId, data.line, data.column, data.name, user.color);
    }

    handleEdit(data) {
        if (!this.app.state.editor || data.userId === this.app.state.user?.id) return;

        this.applyingRemoteChanges = true;
        try {
            const model = this.app.state.editor.getModel();
            model.applyEdits(data.changes);
        } finally {
            this.applyingRemoteChanges = false;
        }
    }

    broadcastCursor(position) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'cursor',
                line: position.lineNumber,
                column: position.column
            }));
        }
    }

    broadcastEdit(changes) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'edit',
                changes: changes
            }));
        }
    }

    setIdentity(name) {
        this.currentIdentity = name;
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'identity',
                name: name
            }));
        }
    }

    renderCursor(userId, line, column, name, color) {
        if (!this.app.state.editor) return;

        // Reset fade timer
        if (this.fadeTimers.has(userId)) {
            clearTimeout(this.fadeTimers.get(userId));
        }

        // Show name immediately
        this.updateUserStyle(userId, color, 1);

        // Set timer to fade
        const timerId = setTimeout(() => {
            this.updateUserStyle(userId, color, 0);
        }, 3000);
        this.fadeTimers.set(userId, timerId);

        // Create a dynamic style tag for this user if it doesn't exist
        this.ensureUserStyle(userId, color);

        const newDecorations = [
            {
                range: new monaco.Range(line, column, line, column),
                options: {
                    className: `remote-cursor-${userId} remote-cursor`,
                    hoverMessage: { value: `${name}` },
                    stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges
                }
            }
        ];

        // Update decorations
        const oldDecorations = this.decorations.get(userId) || [];
        const result = this.app.state.editor.deltaDecorations(oldDecorations, newDecorations);
        this.decorations.set(userId, result);
    }

    removeCursor(userId) {
        if (this.app.state.editor) {
            const oldDecorations = this.decorations.get(userId) || [];
            this.app.state.editor.deltaDecorations(oldDecorations, []);
        }
        this.decorations.delete(userId);

        if (this.fadeTimers.has(userId)) {
            clearTimeout(this.fadeTimers.get(userId));
            this.fadeTimers.delete(userId);
        }

        // Remove valid style tag
        const style = document.getElementById(`style-user-${userId}`);
        if (style) style.remove();
    }

    ensureUserStyle(userId, color) {
        if (document.getElementById(`style-user-${userId}`)) return;

        const style = document.createElement('style');
        style.id = `style-user-${userId}`;
        // Improved style: Attach label to the cursor via ::after on the className element
        this._updateStyleContent(style, userId, color, 1);
        document.head.appendChild(style);
    }

    updateUserStyle(userId, color, opacity = 1) {
        const style = document.getElementById(`style-user-${userId}`);
        if (style) {
            this._updateStyleContent(style, userId, color, opacity);
        }
    }

    _updateStyleContent(style, userId, color, opacity = 1) {
        style.innerHTML = `
            .remote-cursor-${userId} {
                border-left: 2px solid ${color};
            }
            .remote-cursor-${userId}::after {
                content: "${this.users.get(userId).name}";
                position: absolute;
                top: -18px;
                left: -2px;
                background-color: ${color};
                color: #000;
                font-size: 10px;
                padding: 1px 4px;
                border-radius: 3px;
                white-space: nowrap;
                opacity: ${opacity};
                transition: opacity 0.5s ease-in-out;
                pointer-events: none;
                z-index: 1000;
            }
        `;
    }

    sendChat(text) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                text: text,
                timestamp: Date.now()
            }));
        }
    }
}
