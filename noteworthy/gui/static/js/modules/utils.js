// ============================================================
// UTILS MODULE
// Shared utility functions used across the app
// ============================================================

(function () {
    const UtilsMixin = {
        USER_COLORS: [
            "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3",
            "#F38181", "#AA96DA", "#FCBAD3", "#A8D8EA"
        ],

        getUserColor: function (clientId) {
            return this.USER_COLORS[clientId % this.USER_COLORS.length];
        },

        debounce: function (func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },

        showSaveStatus: function (msg = 'Saved') {
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

        getFileIcon: function (name) {
            const ext = name.split('.').pop().toLowerCase();
            const svgIcons = {
                'typ': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#4ECDC4" opacity="0.2" stroke="#4ECDC4" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="7" fill="#4ECDC4" font-family="monospace" font-weight="bold">t</text></svg>`,
                'pdf': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#FF6B6B" opacity="0.2" stroke="#FF6B6B" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="6" fill="#FF6B6B" font-family="monospace" font-weight="bold">PDF</text></svg>`,
                'png': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#FFE66D" opacity="0.2" stroke="#FFE66D" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="5.5" fill="#FFE66D" font-family="monospace" font-weight="bold">IMG</text></svg>`,
                'jpg': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#FFE66D" opacity="0.2" stroke="#FFE66D" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="5.5" fill="#FFE66D" font-family="monospace" font-weight="bold">IMG</text></svg>`,
                'jpeg': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#FFE66D" opacity="0.2" stroke="#FFE66D" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="5.5" fill="#FFE66D" font-family="monospace" font-weight="bold">IMG</text></svg>`,
                'svg': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle"><rect x="2" y="1" width="12" height="14" rx="2" fill="#95E1D3" opacity="0.2" stroke="#95E1D3" stroke-width="1.2"/><text x="8" y="11" text-anchor="middle" font-size="5.5" fill="#95E1D3" font-family="monospace" font-weight="bold">SVG</text></svg>`,
            };
            if (svgIcons[ext]) {
                return { type: 'svg', value: svgIcons[ext] };
            }
            const lucideIcons = {
                'json': 'braces', 'yaml': 'settings-2', 'yml': 'settings-2',
                'md': 'file-text', 'txt': 'file-text', 'bib': 'book',
                'gitkeep': 'git-commit', 'toml': 'settings'
            };
            return { type: 'lucide', value: lucideIcons[ext] || 'file' };
        },
    };

    // Mix into the global app object once it exists
    window._utilsMixin = UtilsMixin;
})();
