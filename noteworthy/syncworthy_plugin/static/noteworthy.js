// ============================================================
// NOTEWORTHY PLUGIN BUNDLE
//
// Loaded by Syncworthy after the core modules (see
// noteworthy/syncworthy_plugin/__init__.py, static_scripts).  Brings:
//   config.js   - the Settings tabs (metadata, constants, structure, ...)
//   build.js    - the Build page and PDF build
//   preview.js  - the SVG preview panel and click-to-source
// and registers them through the Syncworthy plugin API.
// ============================================================

(function () {
    const mixin = Object.assign({},
        window._noteworthyConfigMixin || {},
        window._noteworthyBuildMixin || {},
        window._noteworthyPreviewMixin || {});

    // The Build page, as the old index.html had it.
    const BUILD_PAGE_HTML = `
        <section class="config-content glass">
            <div class="config-section">
                <h3>Build Document</h3>
                <p>Select chapters and pages to include in the build</p>
            </div>

            <div class="build-options-bar">
                <label class="toggle-option">
                    <input type="checkbox" id="build-opt-frontmatter" checked>
                    <span>Frontmatter</span>
                </label>
                <label class="toggle-option">
                    <input type="checkbox" id="build-opt-covers" checked>
                    <span>Chapter Covers</span>
                </label>
                <button class="btn btn-ghost" onclick="app.toggleAllBuildPages()">
                    Toggle All
                </button>
            </div>

            <div class="build-grid" id="build-grid">
                <!-- JS renders: chapter rows with page checkboxes -->
            </div>

            <div class="build-progress" id="build-progress-new" style="display: none;">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill-new" style="width: 0%;"></div>
                </div>
                <div class="progress-info">
                    <span id="progress-page-new">Preparing...</span>
                    <span id="progress-percent-new">0%</span>
                </div>
            </div>

            <div class="build-footer">
                <button class="btn btn-primary" id="build-btn-new" onclick="app.runBuild()">
                    <i data-lucide="zap"></i>
                    Build PDF
                </button>
            </div>
        </section>`;

    window.Syncworthy.registerPlugin('noteworthy', mixin, {
        init: function () {
            // Debounced config saves (config.js's inline handlers call these on `app`).
            this.debouncedUpdateMetadata = this.debounce(this.updateMetadata.bind(this), 500);
            this.debouncedUpdateConstants = this.debounce(this.updateConstants.bind(this), 500);
            this.debouncedSaveHierarchy = this.debounce(this.saveHierarchy.bind(this), 800);
            this.debouncedSaveSnippets = this.debounce(this.saveSnippets.bind(this), 500);
            this.debouncedSavePreface = this.debounce(this.savePreface.bind(this), 800);
            this.debouncedSaveIgnored = this.debounce(this.saveIgnored.bind(this), 500);

            this.registerPage({
                id: 'build', label: 'Build', icon: 'package', html: BUILD_PAGE_HTML,
                onShow: function () { this.renderBuildHierarchy(); },
            });
        },
        messages: {
            preview: function (msg) { this.updatePreview(msg.updates); },
            build_progress: function (msg) { if (this.updateBuildProgress) this.updateBuildProgress(msg); },
        },
    });

    // Settings tabs.  Each renders into #config-content; the ones with a form
    // save through the same debounced handlers as before.
    const S = window.Syncworthy.registerSettingsPage;
    S('metadata', { render(c) { this.renderMetadataTab(c); }, save() { this.updateMetadata(); } });
    S('constants', { render(c) { this.renderConstantsTab(c); }, save() { this.updateConstants(); } });
    S('hierarchy', { render(c) { this.renderHierarchyTab(c); }, save() { this.saveHierarchy(); } });
    S('schemes', { render(c) { this.renderSchemesTab(c); } });
    S('snippets', { render(c) { this.renderSnippetsTab(c); }, save() { this.saveSnippets(); } });
    S('preface', { render(c) { this.renderPrefaceTab(c); }, save() { this.savePreface(); } });
    S('ignored', { render(c) { this.renderIgnoredTab(c); }, save() { this.saveIgnored(); } });
    S('modules', { render(c) { this.renderModulesTab(c); } });
    S('info', { render(c) { this.renderInfoTab(c); } });
})();
