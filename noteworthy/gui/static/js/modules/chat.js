// ============================================================
// CHAT MODULE
// Chat panel: toggling, sending, and receiving chat messages
// ============================================================

(function () {
    const ChatMixin = {
        toggleChat: function () {
            const panel = document.getElementById('chat-panel');
            panel.classList.toggle('hidden');
            if (!panel.classList.contains('hidden')) {
                document.getElementById('chat-input').focus();
                this.scrollChatToBottom();
                const badge = document.getElementById('chat-unread-badge');
                if (badge) badge.style.display = 'none';
            }
        },

        handleChatKey: function (e) {
            if (e.key === 'Enter') this.sendChatMessage();
        },

        sendChatMessage: function () {
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;

            if (this.state.docSocket && this.state.docSocket.readyState === WebSocket.OPEN) {
                this.state.docSocket.send(JSON.stringify({
                    type: 'chat',
                    text: text,
                    timestamp: Date.now()
                }));
                input.value = '';
            }
        },

        addChatMessage: function (msg) {
            const container = document.getElementById('chat-messages');
            if (!container) return;

            const div = document.createElement('div');
            const isSelf = msg.userId === this.state.userId;
            div.className = `chat-message ${isSelf ? 'self' : 'other'}`;

            const time = new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const colorStyle = msg.color ? `background-color: ${msg.color};` : 'background-color: #888;';
            const nameStyle = msg.color ? `color: ${msg.color}; font-weight: 600;` : '';

            div.innerHTML = `
                <div class="chat-meta">
                    <span class="chat-user-group">
                        <span class="chat-dot" style="${colorStyle}"></span>
                        <span style="${nameStyle}">${msg.name || 'Unknown'}</span>
                    </span>
                    <span>${time}</span>
                </div>
                <div class="chat-text">${msg.text}</div>
            `;

            container.appendChild(div);
            this.scrollChatToBottom();

            // Show unread indicator if chat is hidden
            const panel = document.getElementById('chat-panel');
            if (panel && panel.classList.contains('hidden') && !isSelf) {
                const badge = document.getElementById('chat-unread-badge');
                if (badge) badge.style.display = 'block';
            }
        },

        scrollChatToBottom: function () {
            const container = document.getElementById('chat-messages');
            if (container) container.scrollTop = container.scrollHeight;
        },
    };

    window._chatMixin = ChatMixin;
})();
