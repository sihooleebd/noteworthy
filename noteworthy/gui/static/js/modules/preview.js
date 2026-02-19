// ============================================================
// PREVIEW MODULE
// SVG preview panel updates and click-to-navigate source mapping
// ============================================================

(function () {
    const PreviewMixin = {
        updatePreview: function (updates) {
            const container = document.getElementById('preview-container');
            if (!container) return;

            if (container.querySelector('.preview-placeholder') || container.querySelector('.preview-loading')) {
                container.innerHTML = '';
            }

            updates.forEach(u => {
                let pageContainer = document.getElementById(`page-${u.page}`);
                if (!pageContainer) {
                    pageContainer = document.createElement('div');
                    pageContainer.id = `page-${u.page}`;
                    pageContainer.className = 'page-container';
                    container.appendChild(pageContainer);
                }
                pageContainer.innerHTML = u.svg;
                pageContainer.dataset.index = u.page;

                const svgElement = pageContainer.querySelector('svg');
                if (svgElement) {
                    svgElement.style.width = '100%';
                    svgElement.style.height = 'auto';
                    svgElement.style.cursor = 'pointer';
                    svgElement.addEventListener('click', (e) => this.handlePreviewClick(e));
                }
            });

            // Sort pages in order
            const pages = Array.from(container.children).sort((a, b) => parseInt(a.dataset.index) - parseInt(b.dataset.index));
            pages.forEach(p => container.appendChild(p));
        },

        handlePreviewClick: function (e) {
            if (!this.state.editor || !this.state.activeFile) return;

            let textContent = '';
            let target = e.target;
            while (target && !textContent) {
                if (target.textContent && target.textContent.trim()) textContent = target.textContent.trim();
                if (target.tagName === 'svg') break;
                target = target.parentElement;
            }

            textContent = textContent.replace(/\s+/g, ' ').trim();
            if (textContent.length > 50) textContent = textContent.substring(0, 50);
            if (!textContent || textContent.length < 3) {
                console.log('[SourceMap] No meaningful text found at click position');
                return;
            }

            console.log(`[SourceMap] Searching for: "${textContent}"`);
            const model = this.state.editor.getModel();
            if (!model) return;

            const searchResult = model.findNextMatch(textContent, { lineNumber: 1, column: 1 }, false, false, null, false);
            if (searchResult) {
                const { startLineNumber, startColumn } = searchResult.range;
                this.state.editor.revealLineInCenter(startLineNumber);
                this.state.editor.setPosition({ lineNumber: startLineNumber, column: startColumn });
                this.state.editor.focus();

                const decorations = this.state.editor.deltaDecorations([], [{
                    range: searchResult.range,
                    options: { className: 'source-map-highlight', isWholeLine: false }
                }]);
                setTimeout(() => this.state.editor.deltaDecorations(decorations, []), 1500);
                console.log(`[SourceMap] Jumped to line ${startLineNumber}`);
            } else {
                console.log('[SourceMap] No match found in source');
            }
        },
    };

    window._previewMixin = PreviewMixin;
})();
