/**
 * Noteworthy GUI - Main Application
 */
const app = {
    state: {
        activeFile: null,
        editor: null,
        ws: null,
        configData: {},
        editorTheme: localStorage.getItem('editorTheme') || 'vs-dark',
        sessionName: localStorage.getItem('sessionName') || 'Anonymous',
        previewMode: 'file' // Always file mode
    },
    // ============================================================
    // INITIALIZATION
    // ============================================================

    ASCII_LOGO: `         ,--. 
       ,--.'| 
   ,--,:  : | 
,\`--.'\`|  ' : 
|   :  :  | | 
:   |   \\ | : 
|   : '  '; | 
'   ' ;.    ; 
|   | | \\   | 
'   : |  ; .' 
|   | '\`--'   
'   : |       
;   |.'       
'---'         `,

    createWelcomeOverlay: function () {
        // Create overlay element
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

        // Append to editor area (parent of monaco-container)
        const container = document.getElementById('monaco-container');
        if (container && container.parentElement) {
            container.parentElement.appendChild(overlay);
        }
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

        // Debounced content sync (sends full content after pause)
        this.debouncedSyncContent = this.debounce(() => this.syncContent(), 150);

        // Apply saved CSS theme to body on page load
        const savedTheme = this.state.editorTheme;
        if (savedTheme && savedTheme !== 'noteworthy-dark') {
            document.body.dataset.theme = savedTheme;
        }

        // Monaco Editor with saved theme
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], () => {
            // Define all available editor themes
            const EDITOR_THEMES = {
                'noteworthy-dark': {
                    label: 'Noteworthy Dark',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'e0e0e0', background: '000000' },
                        { token: 'comment', foreground: '6a6a6a', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'c792ea', fontStyle: 'bold' },
                        { token: 'string', foreground: 'c3e88d' },
                        { token: 'number', foreground: 'f78c6c' },
                        { token: 'type', foreground: 'ffcb6b' },
                        { token: 'function', foreground: '82aaff' },
                        { token: 'variable', foreground: 'f07178' },
                        { token: 'constant', foreground: '89ddff' },
                        { token: 'operator', foreground: '89ddff' },
                        { token: 'tag', foreground: 'f07178' },
                        { token: 'attribute.name', foreground: 'ffcb6b' },
                        { token: 'attribute.value', foreground: 'c3e88d' },
                    ],
                    colors: {
                        'editor.background': '#000000',
                        'editor.foreground': '#ffffff',
                        'editor.lineHighlightBackground': '#0a0a0a',
                        'editor.selectionBackground': '#333333',
                        'editor.inactiveSelectionBackground': '#222222',
                        'editorCursor.foreground': '#ffffff',
                        'editorWhitespace.foreground': '#222222',
                        'editorLineNumber.foreground': '#444444',
                        'editorLineNumber.activeForeground': '#888888',
                        'editorIndentGuide.background': '#1a1a1a',
                        'editorIndentGuide.activeBackground': '#333333',
                        'editor.selectionHighlightBackground': '#2a2a2a',
                        'editorBracketMatch.background': '#333333',
                        'editorBracketMatch.border': '#555555',
                        'scrollbarSlider.background': '#222222',
                        'scrollbarSlider.hoverBackground': '#333333',
                        'scrollbarSlider.activeBackground': '#444444',
                    }
                },
                'dracula': {
                    label: 'Dracula',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'f8f8f2', background: '282a36' },
                        { token: 'comment', foreground: '6272a4', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'ff79c6', fontStyle: 'bold' },
                        { token: 'string', foreground: 'f1fa8c' },
                        { token: 'number', foreground: 'bd93f9' },
                        { token: 'type', foreground: '8be9fd', fontStyle: 'italic' },
                        { token: 'function', foreground: '50fa7b' },
                        { token: 'variable', foreground: 'f8f8f2' },
                        { token: 'constant', foreground: 'bd93f9' },
                        { token: 'operator', foreground: 'ff79c6' },
                        { token: 'tag', foreground: 'ff79c6' },
                        { token: 'attribute.name', foreground: '50fa7b' },
                        { token: 'attribute.value', foreground: 'f1fa8c' },
                    ],
                    colors: {
                        'editor.background': '#282a36',
                        'editor.foreground': '#f8f8f2',
                        'editor.lineHighlightBackground': '#44475a',
                        'editor.selectionBackground': '#44475a',
                        'editor.inactiveSelectionBackground': '#3d4051',
                        'editorCursor.foreground': '#f8f8f2',
                        'editorWhitespace.foreground': '#44475a',
                        'editorLineNumber.foreground': '#6272a4',
                        'editorLineNumber.activeForeground': '#f8f8f2',
                        'editorIndentGuide.background': '#44475a',
                        'editorIndentGuide.activeBackground': '#6272a4',
                        'editor.selectionHighlightBackground': '#424450',
                        'editorBracketMatch.background': '#44475a',
                        'editorBracketMatch.border': '#ff79c6',
                        'scrollbarSlider.background': '#44475a80',
                        'scrollbarSlider.hoverBackground': '#44475a',
                        'scrollbarSlider.activeBackground': '#6272a4',
                    }
                },
                'one-dark-pro': {
                    label: 'One Dark Pro',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'abb2bf', background: '282c34' },
                        { token: 'comment', foreground: '5c6370', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'c678dd', fontStyle: 'bold' },
                        { token: 'string', foreground: '98c379' },
                        { token: 'number', foreground: 'd19a66' },
                        { token: 'type', foreground: 'e5c07b' },
                        { token: 'function', foreground: '61afef' },
                        { token: 'variable', foreground: 'e06c75' },
                        { token: 'constant', foreground: 'd19a66' },
                        { token: 'operator', foreground: '56b6c2' },
                        { token: 'tag', foreground: 'e06c75' },
                        { token: 'attribute.name', foreground: 'd19a66' },
                        { token: 'attribute.value', foreground: '98c379' },
                    ],
                    colors: {
                        'editor.background': '#282c34',
                        'editor.foreground': '#abb2bf',
                        'editor.lineHighlightBackground': '#2c313a',
                        'editor.selectionBackground': '#3e4451',
                        'editor.inactiveSelectionBackground': '#3a3f4b',
                        'editorCursor.foreground': '#528bff',
                        'editorWhitespace.foreground': '#3b4048',
                        'editorLineNumber.foreground': '#495162',
                        'editorLineNumber.activeForeground': '#abb2bf',
                        'editorIndentGuide.background': '#3b4048',
                        'editorIndentGuide.activeBackground': '#4b5263',
                        'editor.selectionHighlightBackground': '#3e4451',
                        'editorBracketMatch.background': '#3e4451',
                        'editorBracketMatch.border': '#528bff',
                        'scrollbarSlider.background': '#4e566680',
                        'scrollbarSlider.hoverBackground': '#5a6375',
                        'scrollbarSlider.activeBackground': '#747d91',
                    }
                },
                'solarized-dark': {
                    label: 'Solarized Dark',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: '839496', background: '002b36' },
                        { token: 'comment', foreground: '586e75', fontStyle: 'italic' },
                        { token: 'keyword', foreground: '859900', fontStyle: 'bold' },
                        { token: 'string', foreground: '2aa198' },
                        { token: 'number', foreground: 'd33682' },
                        { token: 'type', foreground: 'b58900' },
                        { token: 'function', foreground: '268bd2' },
                        { token: 'variable', foreground: 'cb4b16' },
                        { token: 'constant', foreground: '6c71c4' },
                        { token: 'operator', foreground: '859900' },
                        { token: 'tag', foreground: '268bd2' },
                        { token: 'attribute.name', foreground: '93a1a1' },
                        { token: 'attribute.value', foreground: '2aa198' },
                    ],
                    colors: {
                        'editor.background': '#002b36',
                        'editor.foreground': '#839496',
                        'editor.lineHighlightBackground': '#073642',
                        'editor.selectionBackground': '#073642',
                        'editor.inactiveSelectionBackground': '#064050',
                        'editorCursor.foreground': '#839496',
                        'editorWhitespace.foreground': '#073642',
                        'editorLineNumber.foreground': '#586e75',
                        'editorLineNumber.activeForeground': '#93a1a1',
                        'editorIndentGuide.background': '#073642',
                        'editorIndentGuide.activeBackground': '#586e75',
                        'editor.selectionHighlightBackground': '#0a4050',
                        'editorBracketMatch.background': '#073642',
                        'editorBracketMatch.border': '#268bd2',
                        'scrollbarSlider.background': '#07364280',
                        'scrollbarSlider.hoverBackground': '#586e75',
                        'scrollbarSlider.activeBackground': '#839496',
                    }
                },
                'nord': {
                    label: 'Nord',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'd8dee9', background: '2e3440' },
                        { token: 'comment', foreground: '616e88', fontStyle: 'italic' },
                        { token: 'keyword', foreground: '81a1c1', fontStyle: 'bold' },
                        { token: 'string', foreground: 'a3be8c' },
                        { token: 'number', foreground: 'b48ead' },
                        { token: 'type', foreground: '8fbcbb' },
                        { token: 'function', foreground: '88c0d0' },
                        { token: 'variable', foreground: 'd8dee9' },
                        { token: 'constant', foreground: 'b48ead' },
                        { token: 'operator', foreground: '81a1c1' },
                        { token: 'tag', foreground: '81a1c1' },
                        { token: 'attribute.name', foreground: '8fbcbb' },
                        { token: 'attribute.value', foreground: 'a3be8c' },
                    ],
                    colors: {
                        'editor.background': '#2e3440',
                        'editor.foreground': '#d8dee9',
                        'editor.lineHighlightBackground': '#3b4252',
                        'editor.selectionBackground': '#434c5e',
                        'editor.inactiveSelectionBackground': '#3b4252',
                        'editorCursor.foreground': '#d8dee9',
                        'editorWhitespace.foreground': '#434c5e',
                        'editorLineNumber.foreground': '#4c566a',
                        'editorLineNumber.activeForeground': '#d8dee9',
                        'editorIndentGuide.background': '#434c5e',
                        'editorIndentGuide.activeBackground': '#4c566a',
                        'editor.selectionHighlightBackground': '#434c5e80',
                        'editorBracketMatch.background': '#434c5e',
                        'editorBracketMatch.border': '#88c0d0',
                        'scrollbarSlider.background': '#434c5e80',
                        'scrollbarSlider.hoverBackground': '#4c566a',
                        'scrollbarSlider.activeBackground': '#5e6779',
                    }
                },
                'monokai': {
                    label: 'Monokai',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'f8f8f2', background: '272822' },
                        { token: 'comment', foreground: '88846f', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'f92672', fontStyle: 'bold' },
                        { token: 'string', foreground: 'e6db74' },
                        { token: 'number', foreground: 'ae81ff' },
                        { token: 'type', foreground: '66d9ef', fontStyle: 'italic' },
                        { token: 'function', foreground: 'a6e22e' },
                        { token: 'variable', foreground: 'f8f8f2' },
                        { token: 'constant', foreground: 'ae81ff' },
                        { token: 'operator', foreground: 'f92672' },
                        { token: 'tag', foreground: 'f92672' },
                        { token: 'attribute.name', foreground: 'a6e22e' },
                        { token: 'attribute.value', foreground: 'e6db74' },
                    ],
                    colors: {
                        'editor.background': '#272822',
                        'editor.foreground': '#f8f8f2',
                        'editor.lineHighlightBackground': '#3e3d32',
                        'editor.selectionBackground': '#49483e',
                        'editor.inactiveSelectionBackground': '#3e3d32',
                        'editorCursor.foreground': '#f8f8f2',
                        'editorWhitespace.foreground': '#464741',
                        'editorLineNumber.foreground': '#90908a',
                        'editorLineNumber.activeForeground': '#c2c2bf',
                        'editorIndentGuide.background': '#464741',
                        'editorIndentGuide.activeBackground': '#767771',
                        'editor.selectionHighlightBackground': '#49483e80',
                        'editorBracketMatch.background': '#3e3d32',
                        'editorBracketMatch.border': '#f92672',
                        'scrollbarSlider.background': '#49483e80',
                        'scrollbarSlider.hoverBackground': '#5b5a50',
                        'scrollbarSlider.activeBackground': '#6d6c64',
                    }
                },
                'github-dark': {
                    label: 'GitHub Dark',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'c9d1d9', background: '0d1117' },
                        { token: 'comment', foreground: '8b949e', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'ff7b72', fontStyle: 'bold' },
                        { token: 'string', foreground: 'a5d6ff' },
                        { token: 'number', foreground: '79c0ff' },
                        { token: 'type', foreground: 'ffa657' },
                        { token: 'function', foreground: 'd2a8ff' },
                        { token: 'variable', foreground: 'ffa657' },
                        { token: 'constant', foreground: '79c0ff' },
                        { token: 'operator', foreground: 'ff7b72' },
                        { token: 'tag', foreground: '7ee787' },
                        { token: 'attribute.name', foreground: '79c0ff' },
                        { token: 'attribute.value', foreground: 'a5d6ff' },
                    ],
                    colors: {
                        'editor.background': '#0d1117',
                        'editor.foreground': '#c9d1d9',
                        'editor.lineHighlightBackground': '#161b22',
                        'editor.selectionBackground': '#264f78',
                        'editor.inactiveSelectionBackground': '#1d2d3e',
                        'editorCursor.foreground': '#c9d1d9',
                        'editorWhitespace.foreground': '#21262d',
                        'editorLineNumber.foreground': '#484f58',
                        'editorLineNumber.activeForeground': '#c9d1d9',
                        'editorIndentGuide.background': '#21262d',
                        'editorIndentGuide.activeBackground': '#30363d',
                        'editor.selectionHighlightBackground': '#3fb95040',
                        'editorBracketMatch.background': '#264f78',
                        'editorBracketMatch.border': '#79c0ff',
                        'scrollbarSlider.background': '#484f5880',
                        'scrollbarSlider.hoverBackground': '#6e7681',
                        'scrollbarSlider.activeBackground': '#8b949e',
                    }
                },
                'aether': {
                    label: 'Aether',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'CBD5E1', background: '0F172A' },
                        { token: 'comment', foreground: '64748B', fontStyle: 'italic' },
                        { token: 'keyword', foreground: '6B8799', fontStyle: 'bold' },
                        { token: 'string', foreground: '88B09D' },
                        { token: 'number', foreground: 'CFA098' },
                        { token: 'type', foreground: 'D6B57E' },
                        { token: 'function', foreground: '85A8CC' },
                        { token: 'variable', foreground: 'CBD5E1' },
                        { token: 'constant', foreground: 'CFA098' },
                        { token: 'operator', foreground: '89A3B5' },
                    ],
                    colors: {
                        'editor.background': '#0F172A',
                        'editor.foreground': '#CBD5E1',
                        'editor.lineHighlightBackground': '#1E293B',
                        'editor.selectionBackground': '#334155',
                        'editor.inactiveSelectionBackground': '#1E293B',
                        'editorCursor.foreground': '#CBD5E1',
                        'editorWhitespace.foreground': '#1E293B',
                        'editorLineNumber.foreground': '#64748B',
                        'editorLineNumber.activeForeground': '#CBD5E1',
                        'editorIndentGuide.background': '#1E293B',
                        'editorIndentGuide.activeBackground': '#334155',
                        'scrollbarSlider.background': '#1E293B80',
                        'scrollbarSlider.hoverBackground': '#334155',
                        'scrollbarSlider.activeBackground': '#475569',
                    }
                },
                'catppuccin-mocha': {
                    label: 'Catppuccin Mocha',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'cdd6f4', background: '1e1e2e' },
                        { token: 'comment', foreground: '6c7086', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'cba6f7', fontStyle: 'bold' },
                        { token: 'string', foreground: 'a6e3a1' },
                        { token: 'number', foreground: 'fab387' },
                        { token: 'type', foreground: 'f9e2af' },
                        { token: 'function', foreground: '89b4fa' },
                        { token: 'variable', foreground: 'cdd6f4' },
                        { token: 'constant', foreground: 'fab387' },
                        { token: 'operator', foreground: '89dceb' },
                    ],
                    colors: {
                        'editor.background': '#1e1e2e',
                        'editor.foreground': '#cdd6f4',
                        'editor.lineHighlightBackground': '#313244',
                        'editor.selectionBackground': '#45475a',
                        'editor.inactiveSelectionBackground': '#313244',
                        'editorCursor.foreground': '#f5e0dc',
                        'editorWhitespace.foreground': '#313244',
                        'editorLineNumber.foreground': '#6c7086',
                        'editorLineNumber.activeForeground': '#cdd6f4',
                        'editorIndentGuide.background': '#313244',
                        'editorIndentGuide.activeBackground': '#45475a',
                        'scrollbarSlider.background': '#31324480',
                        'scrollbarSlider.hoverBackground': '#45475a',
                        'scrollbarSlider.activeBackground': '#585b70',
                    }
                },
                'catppuccin-latte': {
                    label: 'Catppuccin Latte',
                    base: 'vs',
                    inherit: true,
                    rules: [
                        { token: '', foreground: '4c4f69', background: 'eff1f5' },
                        { token: 'comment', foreground: '9ca0b0', fontStyle: 'italic' },
                        { token: 'keyword', foreground: '8839ef', fontStyle: 'bold' },
                        { token: 'string', foreground: '40a02b' },
                        { token: 'number', foreground: 'fe640b' },
                        { token: 'type', foreground: 'df8e1d' },
                        { token: 'function', foreground: '1e66f5' },
                        { token: 'variable', foreground: '4c4f69' },
                        { token: 'constant', foreground: 'fe640b' },
                        { token: 'operator', foreground: '04a5e5' },
                    ],
                    colors: {
                        'editor.background': '#eff1f5',
                        'editor.foreground': '#4c4f69',
                        'editor.lineHighlightBackground': '#e6e9ef',
                        'editor.selectionBackground': '#acb0be',
                        'editor.inactiveSelectionBackground': '#bcc0cc',
                        'editorCursor.foreground': '#dc8a78',
                        'editorWhitespace.foreground': '#bcc0cc',
                        'editorLineNumber.foreground': '#9ca0b0',
                        'editorLineNumber.activeForeground': '#4c4f69',
                        'editorIndentGuide.background': '#bcc0cc',
                        'editorIndentGuide.activeBackground': '#acb0be',
                        'scrollbarSlider.background': '#bcc0cc80',
                        'scrollbarSlider.hoverBackground': '#acb0be',
                        'scrollbarSlider.activeBackground': '#9ca0b0',
                    }
                },
                'everforest': {
                    label: 'Everforest',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'd3c6aa', background: '2d353b' },
                        { token: 'comment', foreground: '859289', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'e67e80', fontStyle: 'bold' },
                        { token: 'string', foreground: 'a7c080' },
                        { token: 'number', foreground: 'd699b6' },
                        { token: 'type', foreground: 'dbbc7f' },
                        { token: 'function', foreground: '7fbbb3' },
                        { token: 'variable', foreground: 'd3c6aa' },
                        { token: 'constant', foreground: 'e69875' },
                        { token: 'operator', foreground: 'e67e80' },
                    ],
                    colors: {
                        'editor.background': '#2d353b',
                        'editor.foreground': '#d3c6aa',
                        'editor.lineHighlightBackground': '#343f44',
                        'editor.selectionBackground': '#3d484d',
                        'editor.inactiveSelectionBackground': '#343f44',
                        'editorCursor.foreground': '#d3c6aa',
                        'editorWhitespace.foreground': '#343f44',
                        'editorLineNumber.foreground': '#859289',
                        'editorLineNumber.activeForeground': '#d3c6aa',
                        'editorIndentGuide.background': '#343f44',
                        'editorIndentGuide.activeBackground': '#3d484d',
                        'scrollbarSlider.background': '#343f4480',
                        'scrollbarSlider.hoverBackground': '#3d484d',
                        'scrollbarSlider.activeBackground': '#475258',
                    }
                },
                'gruvbox': {
                    label: 'Gruvbox',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'ebdbb2', background: '282828' },
                        { token: 'comment', foreground: '928374', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'fb4934', fontStyle: 'bold' },
                        { token: 'string', foreground: 'b8bb26' },
                        { token: 'number', foreground: 'd3869b' },
                        { token: 'type', foreground: 'fabd2f' },
                        { token: 'function', foreground: '83a598' },
                        { token: 'variable', foreground: 'ebdbb2' },
                        { token: 'constant', foreground: 'fe8019' },
                        { token: 'operator', foreground: '8ec07c' },
                    ],
                    colors: {
                        'editor.background': '#282828',
                        'editor.foreground': '#ebdbb2',
                        'editor.lineHighlightBackground': '#32302f',
                        'editor.selectionBackground': '#3c3836',
                        'editor.inactiveSelectionBackground': '#32302f',
                        'editorCursor.foreground': '#ebdbb2',
                        'editorWhitespace.foreground': '#3c3836',
                        'editorLineNumber.foreground': '#928374',
                        'editorLineNumber.activeForeground': '#ebdbb2',
                        'editorIndentGuide.background': '#3c3836',
                        'editorIndentGuide.activeBackground': '#504945',
                        'scrollbarSlider.background': '#3c383680',
                        'scrollbarSlider.hoverBackground': '#504945',
                        'scrollbarSlider.activeBackground': '#665c54',
                    }
                },
                'rose-pine': {
                    label: 'Rosé Pine',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'e0def4', background: '191724' },
                        { token: 'comment', foreground: '6e6a86', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'eb6f92', fontStyle: 'bold' },
                        { token: 'string', foreground: 'f6c177' },
                        { token: 'number', foreground: 'c4a7e7' },
                        { token: 'type', foreground: 'ebbcba' },
                        { token: 'function', foreground: '9ccfd8' },
                        { token: 'variable', foreground: 'e0def4' },
                        { token: 'constant', foreground: 'c4a7e7' },
                        { token: 'operator', foreground: '31748f' },
                    ],
                    colors: {
                        'editor.background': '#191724',
                        'editor.foreground': '#e0def4',
                        'editor.lineHighlightBackground': '#1f1d2e',
                        'editor.selectionBackground': '#26233a',
                        'editor.inactiveSelectionBackground': '#1f1d2e',
                        'editorCursor.foreground': '#e0def4',
                        'editorWhitespace.foreground': '#1f1d2e',
                        'editorLineNumber.foreground': '#6e6a86',
                        'editorLineNumber.activeForeground': '#e0def4',
                        'editorIndentGuide.background': '#1f1d2e',
                        'editorIndentGuide.activeBackground': '#26233a',
                        'scrollbarSlider.background': '#1f1d2e80',
                        'scrollbarSlider.hoverBackground': '#26233a',
                        'scrollbarSlider.activeBackground': '#393552',
                    }
                },
                'tokyo-night': {
                    label: 'Tokyo Night',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'c0caf5', background: '1a1b26' },
                        { token: 'comment', foreground: '565f89', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'bb9af7', fontStyle: 'bold' },
                        { token: 'string', foreground: '9ece6a' },
                        { token: 'number', foreground: 'ff9e64' },
                        { token: 'type', foreground: 'e0af68' },
                        { token: 'function', foreground: '7aa2f7' },
                        { token: 'variable', foreground: 'c0caf5' },
                        { token: 'constant', foreground: 'ff9e64' },
                        { token: 'operator', foreground: '89ddff' },
                    ],
                    colors: {
                        'editor.background': '#1a1b26',
                        'editor.foreground': '#c0caf5',
                        'editor.lineHighlightBackground': '#1f2335',
                        'editor.selectionBackground': '#283457',
                        'editor.inactiveSelectionBackground': '#1f2335',
                        'editorCursor.foreground': '#c0caf5',
                        'editorWhitespace.foreground': '#1f2335',
                        'editorLineNumber.foreground': '#565f89',
                        'editorLineNumber.activeForeground': '#c0caf5',
                        'editorIndentGuide.background': '#1f2335',
                        'editorIndentGuide.activeBackground': '#292e42',
                        'scrollbarSlider.background': '#1f233580',
                        'scrollbarSlider.hoverBackground': '#292e42',
                        'scrollbarSlider.activeBackground': '#3b4261',
                    }
                },
                'moonlight': {
                    label: 'Moonlight',
                    base: 'vs-dark',
                    inherit: true,
                    rules: [
                        { token: '', foreground: 'c8d3f5', background: '212337' },
                        { token: 'comment', foreground: '7a88cf', fontStyle: 'italic' },
                        { token: 'keyword', foreground: 'c099ff', fontStyle: 'bold' },
                        { token: 'string', foreground: 'c3e88d' },
                        { token: 'number', foreground: 'ff966c' },
                        { token: 'type', foreground: 'ffc777' },
                        { token: 'function', foreground: '82aaff' },
                        { token: 'variable', foreground: 'c8d3f5' },
                        { token: 'constant', foreground: 'ff966c' },
                        { token: 'operator', foreground: '86e1fc' },
                    ],
                    colors: {
                        'editor.background': '#212337',
                        'editor.foreground': '#c8d3f5',
                        'editor.lineHighlightBackground': '#2f334d',
                        'editor.selectionBackground': '#444a73',
                        'editor.inactiveSelectionBackground': '#2f334d',
                        'editorCursor.foreground': '#c8d3f5',
                        'editorWhitespace.foreground': '#2f334d',
                        'editorLineNumber.foreground': '#7a88cf',
                        'editorLineNumber.activeForeground': '#c8d3f5',
                        'editorIndentGuide.background': '#2f334d',
                        'editorIndentGuide.activeBackground': '#444a73',
                        'scrollbarSlider.background': '#2f334d80',
                        'scrollbarSlider.hoverBackground': '#444a73',
                        'scrollbarSlider.activeBackground': '#545c7e',
                    }
                },
                'solarized-light': {
                    label: 'Solarized Light',
                    base: 'vs',
                    inherit: true,
                    rules: [
                        { token: '', foreground: '657b83', background: 'fdf6e3' },
                        { token: 'comment', foreground: '93a1a1', fontStyle: 'italic' },
                        { token: 'keyword', foreground: '859900', fontStyle: 'bold' },
                        { token: 'string', foreground: '2aa198' },
                        { token: 'number', foreground: 'd33682' },
                        { token: 'type', foreground: 'b58900' },
                        { token: 'function', foreground: '268bd2' },
                        { token: 'variable', foreground: 'cb4b16' },
                        { token: 'constant', foreground: '6c71c4' },
                        { token: 'operator', foreground: '859900' },
                    ],
                    colors: {
                        'editor.background': '#fdf6e3',
                        'editor.foreground': '#657b83',
                        'editor.lineHighlightBackground': '#eee8d5',
                        'editor.selectionBackground': '#d3d0c8',
                        'editor.inactiveSelectionBackground': '#eee8d5',
                        'editorCursor.foreground': '#657b83',
                        'editorWhitespace.foreground': '#eee8d5',
                        'editorLineNumber.foreground': '#93a1a1',
                        'editorLineNumber.activeForeground': '#586e75',
                        'editorIndentGuide.background': '#eee8d5',
                        'editorIndentGuide.activeBackground': '#d3d0c8',
                        'scrollbarSlider.background': '#d3d0c880',
                        'scrollbarSlider.hoverBackground': '#c0bcb0',
                        'scrollbarSlider.activeBackground': '#93a1a1',
                    }
                }
            };

            // Store themes globally for access in settings
            this.EDITOR_THEMES = EDITOR_THEMES;

            // Register all themes with Monaco
            Object.keys(EDITOR_THEMES).forEach(themeId => {
                const theme = EDITOR_THEMES[themeId];
                monaco.editor.defineTheme(themeId, {
                    base: theme.base,
                    inherit: theme.inherit,
                    rules: theme.rules,
                    colors: theme.colors
                });
            });

            // Use saved theme or default to noteworthy-dark
            const themeToUse = this.state.editorTheme || 'noteworthy-dark';

            this.state.editor = monaco.editor.create(document.getElementById('monaco-container'), {
                value: '',
                language: 'markdown',
                theme: themeToUse,
                automaticLayout: true,
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
                minimap: { enabled: false },
                padding: { top: 16 },
                lineNumbers: 'on',
                roundedSelection: true,
                scrollBeyondLastLine: false
            });

            // On content change - sync to server (debounced)
            this.state.editor.onDidChangeModelContent((e) => {
                if (this.state.applyingRemote) return;  // Skip if applying remote changes

                document.getElementById('save-status').textContent = '● Unsaved';

                // Debounced sync - sends full content after 150ms pause
                this.debouncedSyncContent();
            });

            // Cursor broadcast
            this.state.editor.onDidChangeCursorPosition((e) => {
                this.sendCursor(e.position);
            });

            // Set theme selector to current value
            const themeSelect = document.getElementById('editor-theme');
            if (themeSelect) themeSelect.value = this.state.editorTheme;
        });

        // Unified WebSocket for all real-time features
        this.connectDocSocket();

        // Create welcome overlay immediately (synchronous)
        this.createWelcomeOverlay();

        // Hide editor initially until file is selected
        const container = document.getElementById('monaco-container');
        if (container) container.style.display = 'none';

        // Load initial data
        await this.refreshTree();
        await this.loadStatus();

        // Show initial config
        this.showConfigTab('metadata');

        // Initialize resizer
        this.initResizer();

        // ESC key handler for saving config changes
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Save current config tab on ESC
                const activePage = document.querySelector('.page.active');
                if (activePage && activePage.id === 'page-config') {
                    this.saveCurrentConfigTab();
                    this.showSaveStatus('Changes saved');
                }
            }
        });
    },

    saveCurrentConfigTab: function () {
        // Find active config tab and save
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

        if (pageId === 'build') this.renderBuildHierarchy();
    },

    setEditorTheme: function (theme) {
        this.state.editorTheme = theme;
        localStorage.setItem('editorTheme', theme);

        // Apply CSS theme to body (for full UI theming)
        if (theme === 'noteworthy-dark') {
            document.body.removeAttribute('data-theme');
        } else {
            document.body.dataset.theme = theme;
        }

        // Apply Monaco editor theme
        if (this.state.editor && window.monaco) {
            window.monaco.editor.setTheme(theme);
        }

        this.showSaveStatus('Theme Updated');
    },

    // ============================================================
    // FILE TREE
    // ============================================================

    refreshTree: async function () {
        const res = await fetch('/api/tree');
        const data = await res.json();

        // Cache tree data for instant folder toggling
        this.state.treeData = data;

        const container = document.getElementById('file-tree');
        container.innerHTML = '';

        // Initialize expanded folders state if not exists
        if (!this.state.expandedFolders) {
            this.state.expandedFolders = {};
        }

        container.appendChild(this.renderTreeItems(data.items, 0));

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
        // Re-render from cached tree data (no network request)
        this.renderTreeFromCache();
    },

    renderTreeFromCache: function () {
        if (!this.state.treeData) return;
        const container = document.getElementById('file-tree');
        container.innerHTML = '';
        container.appendChild(this.renderTreeItems(this.state.treeData.items, 0));
        if (window.lucide) lucide.createIcons();
    },

    renderTreeItems: function (items, depth) {
        const div = document.createElement('div');

        // Sort items: content first, then other folders, then templates and config at bottom
        const bottomFolders = ['templates', 'config'];
        const sortedItems = [...items].sort((a, b) => {
            const aIsBottom = bottomFolders.includes(a.name);
            const bIsBottom = bottomFolders.includes(b.name);
            if (aIsBottom && !bIsBottom) return 1;
            if (!aIsBottom && bIsBottom) return -1;
            // Put content folder at top
            if (a.name === 'content' && b.name !== 'content') return -1;
            if (a.name !== 'content' && b.name === 'content') return 1;
            return a.name.localeCompare(b.name);
        });

        sortedItems.forEach(item => {
            const el = document.createElement('div');
            el.className = 'tree-item';
            el.style.paddingLeft = `${depth * 16 + 12}px`;

            if (item.is_dir) {
                // Default templates and config to collapsed (false), others to expanded
                const isBottomFolder = bottomFolders.includes(item.name);
                const defaultExpanded = !isBottomFolder;
                const isExpanded = this.state.expandedFolders?.[item.path] ?? defaultExpanded;

                el.innerHTML = `<i data-lucide="${isExpanded ? 'chevron-down' : 'chevron-right'}" class="tree-arrow"></i><i data-lucide="folder" class="tree-folder"></i> ${item.name}`;
                el.onclick = (e) => {
                    e.stopPropagation();
                    this.toggleFolder(item.path);
                };
                div.appendChild(el);

                if (item.children && isExpanded) {
                    const childDiv = this.renderTreeItems(item.children, depth + 1);
                    childDiv.dataset.folder = item.path;
                    div.appendChild(childDiv);
                }
            } else {
                el.innerHTML = `<i data-lucide="file" class="tree-file" style="fill: none; stroke-width: 2px;"></i> ${item.name}`;
                el.onclick = () => this.openFile(item.path, el);
                el.oncontextmenu = (e) => this.showFileContextMenu(e, item.path);
                div.appendChild(el);
            }
        });
        return div;
    },

    // File context menu
    showFileContextMenu: function (e, path) {
        e.preventDefault();
        e.stopPropagation();

        this.state.contextMenuFile = path;
        const menu = document.getElementById('file-context-menu');
        menu.style.left = `${e.clientX}px`;
        menu.style.top = `${e.clientY}px`;
        menu.classList.add('visible');

        // Re-init icons
        if (window.lucide) lucide.createIcons();

        // Close on click outside
        const closeMenu = () => {
            menu.classList.remove('visible');
            document.removeEventListener('click', closeMenu);
        };
        setTimeout(() => document.addEventListener('click', closeMenu), 0);
    },

    // Upload files
    uploadFiles: function () {
        document.getElementById('file-upload-input').click();
    },

    handleFileUpload: async function (event) {
        const files = event.target.files;
        if (!files.length) return;

        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }

        // Upload to current directory (or root if none selected)
        const dir = this.state.activeFile ?
            this.state.activeFile.substring(0, this.state.activeFile.lastIndexOf('/')) :
            '';
        formData.append('directory', dir);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                this.showSaveStatus('Files Uploaded');
                this.refreshTree();
            } else {
                this.showSaveStatus('Upload Failed');
            }
        } catch (e) {
            console.error('Upload error:', e);
            this.showSaveStatus('Upload Error');
        }

        event.target.value = ''; // Reset input
    },

    renameFile: async function () {
        const path = this.state.contextMenuFile;
        if (!path) return;

        const filename = path.split('/').pop();
        const newName = prompt('Rename file:', filename);
        if (!newName || newName === filename) return;

        try {
            const res = await fetch('/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path, newName })
            });
            if (res.ok) {
                this.showSaveStatus('File Renamed');
                this.refreshTree();
                // Update active file if it was renamed
                if (this.state.activeFile === path) {
                    const newPath = path.substring(0, path.lastIndexOf('/') + 1) + newName;
                    this.state.activeFile = newPath;
                    document.getElementById('active-filename').textContent = newPath;
                }
            } else {
                this.showSaveStatus('Rename Failed');
            }
        } catch (e) {
            console.error('Rename error:', e);
            this.showSaveStatus('Rename Error');
        }
    },

    deleteFile: async function () {
        const path = this.state.contextMenuFile;
        if (!path) return;

        if (!confirm(`Delete "${path}"?`)) return;

        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });
            if (res.ok) {
                this.showSaveStatus('File Deleted');
                this.refreshTree();
                // Clear editor if deleted file was active
                if (this.state.activeFile === path) {
                    this.state.activeFile = null;
                    document.getElementById('active-filename').textContent = 'Select a file';
                    if (this.state.editor) this.state.editor.setValue('');
                }
            } else {
                this.showSaveStatus('Delete Failed');
            }
        } catch (e) {
            console.error('Delete error:', e);
            this.showSaveStatus('Delete Error');
        }
    },

    openFile: async function (path, el) {
        // FORCE REMOVAL of welcome overlay (don't just hide)
        const overlay = document.getElementById('welcome-overlay');
        if (overlay) {
            overlay.remove();
        }

        // Update selection
        document.querySelectorAll('.tree-item').forEach(e => e.classList.remove('selected'));
        if (el) el.classList.add('selected');

        this.state.activeFile = path;
        document.getElementById('active-filename').textContent = path;

        const monacoContainer = document.getElementById('monaco-container');
        const previewContainer = document.getElementById('preview-container');
        const ext = path.split('.').pop().toLowerCase();

        // Binary file extensions
        const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico'];
        const pdfExtension = 'pdf';

        if (ext === pdfExtension) {
            // PDF: Show in editor area, placeholder in preview
            monacoContainer.style.display = 'none';

            // Create PDF viewer in editor area (after monaco container)
            let pdfViewer = document.getElementById('pdf-viewer');
            if (!pdfViewer) {
                pdfViewer = document.createElement('div');
                pdfViewer.id = 'pdf-viewer';
                pdfViewer.style.cssText = 'flex: 1; width: 100%; height: 100%; background: #1e1e1e; border-radius: 0 0 20px 20px; overflow: hidden;';
                monacoContainer.parentNode.insertBefore(pdfViewer, monacoContainer.nextSibling);
            }
            pdfViewer.style.display = 'block';
            pdfViewer.innerHTML = `<iframe src="/api/file?path=${encodeURIComponent(path)}&raw=1" style="width: 100%; height: 100%; border: none;"></iframe>`;

            // Preview placeholder
            previewContainer.innerHTML = `
                <div class="preview-placeholder">
                    <i data-lucide="file-text"></i>
                    <span>Select a .typ file to view preview</span>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;

        } else if (imageExtensions.includes(ext)) {
            // Image: Show in editor area, placeholder in preview
            monacoContainer.style.display = 'none';

            let imageViewer = document.getElementById('image-viewer');
            if (!imageViewer) {
                imageViewer = document.createElement('div');
                imageViewer.id = 'image-viewer';
                imageViewer.style.cssText = 'flex: 1; width: 100%; height: 100%; background: #0a0a0a; border-radius: 0 0 20px 20px; overflow: auto; display: flex; align-items: center; justify-content: center; padding: 20px;';
                monacoContainer.parentNode.insertBefore(imageViewer, monacoContainer.nextSibling);
            }
            imageViewer.style.display = 'flex';
            imageViewer.innerHTML = `<img src="/api/file?path=${encodeURIComponent(path)}&raw=1" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">`;

            // Hide PDF viewer if exists
            const pdfViewer = document.getElementById('pdf-viewer');
            if (pdfViewer) pdfViewer.style.display = 'none';

            // Preview placeholder
            previewContainer.innerHTML = `
                <div class="preview-placeholder">
                    <i data-lucide="image"></i>
                    <span>Select a .typ file to view preview</span>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;

        } else {
            // Text file: Show Monaco editor
            monacoContainer.style.display = 'block';
            if (this.state.editor) this.state.editor.layout();

            // Hide binary viewers
            const pdfViewer = document.getElementById('pdf-viewer');
            const imageViewer = document.getElementById('image-viewer');
            if (pdfViewer) pdfViewer.style.display = 'none';
            if (imageViewer) imageViewer.style.display = 'none';

            // Show loading skeleton for .typ files
            if (path.endsWith('.typ')) {
                previewContainer.innerHTML = `
                    <div class="preview-loading">
                        <div class="skeleton-page"></div>
                        <div class="skeleton-page"></div>
                    </div>
                `;
            } else {
                // Non-typ text files: show placeholder in preview
                previewContainer.innerHTML = `
                    <div class="preview-placeholder">
                        <i data-lucide="file-code"></i>
                        <span>Select a .typ file to view preview</span>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            }
        }

        // Join file via unified WebSocket (gets content from server)
        this.joinFile(path);
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


    // setPreviewMode removed - always using file preview

    toggleErrorDetails: function () {
        const detailsEl = document.getElementById('error-details');
        const chevron = document.querySelector('.error-chevron');
        if (detailsEl) {
            const isVisible = detailsEl.style.display === 'block';
            detailsEl.style.display = isVisible ? 'none' : 'block';
            if (chevron) {
                chevron.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(180deg)';
            }
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
            console.log('[LSP] Received diagnostics:', data);

            // Clear old markers
            monaco.editor.setModelMarkers(this.state.editor.getModel(), 'owner', []);

            const errorCountEl = document.getElementById('error-count');
            const errorCountText = document.getElementById('error-count-text');
            const errorDetailsEl = document.getElementById('error-details');

            if (data.diagnostics && data.diagnostics.length > 0) {
                const markers = data.diagnostics.map(d => ({
                    severity: monaco.MarkerSeverity.Error,
                    startLineNumber: d.line,
                    startColumn: d.col,
                    endLineNumber: d.line,
                    endColumn: d.col + 10,
                    message: d.message
                }));
                monaco.editor.setModelMarkers(this.state.editor.getModel(), 'owner', markers);

                // Update error count UI
                if (errorCountEl) {
                    errorCountEl.classList.add('visible');
                    errorCountText.textContent = `${markers.length} error${markers.length > 1 ? 's' : ''}`;
                }

                // Show error details
                if (errorDetailsEl) {
                    errorDetailsEl.innerHTML = data.diagnostics.map(d => {
                        const fileName = d.file ? d.file.split('/').pop() : 'unknown';
                        return `<div class="error-item">
                            <span class="error-location">${fileName}:${d.line}:${d.col}</span>
                            <span class="error-message">${d.message}</span>
                        </div>`;
                    }).join('');
                    errorDetailsEl.style.display = 'block';
                }
            } else {
                // No errors
                if (errorCountEl) {
                    errorCountEl.classList.remove('visible');
                }
                if (errorDetailsEl) {
                    errorDetailsEl.style.display = 'none';
                    errorDetailsEl.innerHTML = '';
                }
            }

            // Reinit Lucide for dynamic content
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Diagnostic error:', e);
        }
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
                        <button class="icon-btn" onclick="app.addPage(${chIdx})" title="Add Page">
                            <i data-lucide="plus"></i>
                        </button>
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

    // Build page grid-based selection (TUI style)
    renderBuildHierarchy: async function () {
        const container = document.getElementById('build-grid');
        if (!container) return;

        // Load hierarchy if not loaded
        if (!this.state.hierarchy || this.state.hierarchy.length === 0) {
            try {
                const res = await fetch('/api/hierarchy');
                const data = await res.json();
                this.state.hierarchy = data.hierarchy || [];
            } catch (e) {
                console.error('Failed to load hierarchy:', e);
                container.innerHTML = '<p style="color: var(--text-muted);">Failed to load structure.</p>';
                return;
            }
        }

        // Initialize build selection state if needed
        if (!this.state.buildSelection) {
            this.state.buildSelection = {};
            this.state.hierarchy.forEach((ch, chIdx) => {
                this.state.buildSelection[chIdx] = {};
                (ch.pages || []).forEach((pg, pgIdx) => {
                    this.state.buildSelection[chIdx][pgIdx] = true; // Select all by default
                });
            });
        }

        container.innerHTML = '';

        this.state.hierarchy.forEach((chapter, chIdx) => {
            const pages = chapter.pages || [];
            const selectedCount = pages.filter((_, pgIdx) =>
                this.state.buildSelection[chIdx]?.[pgIdx]
            ).length;
            const allSelected = selectedCount === pages.length && pages.length > 0;

            // Create row
            const rowEl = document.createElement('div');
            rowEl.className = 'build-row';

            // Chapter label with toggle button
            const labelEl = document.createElement('div');
            labelEl.className = 'build-row-label';

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'btn btn-ghost btn-sm';
            toggleBtn.textContent = allSelected ? 'Deselect' : 'Select';
            toggleBtn.onclick = (e) => { e.stopPropagation(); this.toggleBuildChapter(chIdx); };

            const titleSpan = document.createElement('span');
            titleSpan.textContent = `Ch ${chIdx + 1}: ${chapter.title || 'Untitled'}`;

            labelEl.appendChild(titleSpan);
            labelEl.appendChild(toggleBtn);
            rowEl.appendChild(labelEl);

            // Page cells container
            const pagesEl = document.createElement('div');
            pagesEl.className = 'build-row-pages';

            pages.forEach((page, pgIdx) => {
                const isSelected = this.state.buildSelection[chIdx]?.[pgIdx];
                const cell = document.createElement('div');
                cell.className = 'build-cell' + (isSelected ? ' selected' : '');
                cell.title = page.title || `Page ${pgIdx + 1}`;
                cell.textContent = pgIdx + 1;
                cell.dataset.chapterIdx = chIdx;
                cell.dataset.pageIdx = pgIdx;
                cell.onclick = () => this.toggleBuildPage(chIdx, pgIdx);
                pagesEl.appendChild(cell);
            });

            rowEl.appendChild(pagesEl);
            container.appendChild(rowEl);
        });
    },

    toggleBuildChapter: function (chIdx) {
        const pages = this.state.hierarchy[chIdx]?.pages || [];
        if (!this.state.buildSelection[chIdx]) {
            this.state.buildSelection[chIdx] = {};
        }

        const allSelected = pages.every((_, pgIdx) =>
            this.state.buildSelection[chIdx][pgIdx]
        );

        pages.forEach((_, pgIdx) => {
            this.state.buildSelection[chIdx][pgIdx] = !allSelected;
        });

        this.renderBuildHierarchy();
    },

    toggleBuildPage: function (chIdx, pgIdx) {
        if (!this.state.buildSelection[chIdx]) {
            this.state.buildSelection[chIdx] = {};
        }
        this.state.buildSelection[chIdx][pgIdx] = !this.state.buildSelection[chIdx][pgIdx];
        this.renderBuildHierarchy();
    },

    toggleAllBuildPages: function () {
        if (!this.state.hierarchy || !this.state.buildSelection) return;

        // Check if all are selected
        let allSelected = true;
        for (let chIdx = 0; chIdx < this.state.hierarchy.length; chIdx++) {
            const pages = this.state.hierarchy[chIdx]?.pages || [];
            for (let pgIdx = 0; pgIdx < pages.length; pgIdx++) {
                if (!this.state.buildSelection[chIdx]?.[pgIdx]) {
                    allSelected = false;
                    break;
                }
            }
            if (!allSelected) break;
        }

        // Toggle all
        this.state.hierarchy.forEach((ch, chIdx) => {
            (ch.pages || []).forEach((_, pgIdx) => {
                this.state.buildSelection[chIdx][pgIdx] = !allSelected;
            });
        });

        this.renderBuildHierarchy();
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
        document.querySelectorAll('.build-cell.selected').forEach(cell => {
            targets.push({
                chapter: parseInt(cell.dataset.chapterIdx),
                page: parseInt(cell.dataset.pageIdx)
            });
        });

        const options = {
            frontmatter: (document.getElementById('build-opt-frontmatter') || document.getElementById('opt-frontmatter'))?.checked ?? true,
            covers: (document.getElementById('build-opt-covers') || document.getElementById('opt-covers'))?.checked ?? true
        };

        // Show progress - try Build page IDs first, fall back to modal IDs
        const progress = document.getElementById('build-progress-new') || document.getElementById('build-progress');
        const progressFill = document.getElementById('progress-fill-new') || document.getElementById('progress-fill');
        const progressPage = document.getElementById('progress-page-new') || document.getElementById('progress-page');
        const progressPercent = document.getElementById('progress-percent-new') || document.getElementById('progress-percent');
        const log = document.getElementById('build-log');
        const buildBtn = document.getElementById('build-btn-new') || document.getElementById('build-btn');

        if (progress) progress.style.display = 'block';
        if (log) log.style.display = 'none';
        if (buildBtn) {
            buildBtn.disabled = true;
            buildBtn.innerHTML = '<i data-lucide="loader"></i> Building...';
        }

        if (progressPage) progressPage.textContent = 'Preparing...';
        if (progressPercent) progressPercent.textContent = '0%';
        if (progressFill) progressFill.style.width = '0%';

        // Animated progress - simulate incremental updates
        let currentProgress = 0;
        const totalTargets = targets.length + (options.frontmatter ? 5 : 0); // Estimate total items
        const targetProgress = 90; // Will animate to 90% while building
        const progressInterval = setInterval(() => {
            if (currentProgress < targetProgress) {
                currentProgress += Math.random() * 5 + 1; // Random increment for realism
                if (currentProgress > targetProgress) currentProgress = targetProgress;
                if (progressFill) progressFill.style.width = `${currentProgress}%`;
                if (progressPercent) progressPercent.textContent = `${Math.round(currentProgress)}%`;

                // Update status text based on progress
                if (progressPage) {
                    if (currentProgress < 20) {
                        progressPage.textContent = 'Compiling frontmatter...';
                    } else if (currentProgress < 50) {
                        progressPage.textContent = `Building chapters...`;
                    } else if (currentProgress < 80) {
                        progressPage.textContent = 'Compiling pages...';
                    } else {
                        progressPage.textContent = 'Merging PDF...';
                    }
                }
            }
        }, 200);

        try {
            const res = await fetch('/api/build', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ targets, options })
            });
            const result = await res.json();

            // Stop animation and complete
            clearInterval(progressInterval);
            if (progressFill) progressFill.style.width = '100%';
            if (progressPercent) progressPercent.textContent = '100%';

            if (buildBtn) {
                buildBtn.disabled = false;
                buildBtn.innerHTML = '<i data-lucide="zap"></i> Build PDF';
            }

            if (result.success) {
                if (progressPage) progressPage.textContent = 'Build complete!';
                if (log) {
                    log.style.display = 'block';
                    log.textContent = 'Success! Downloading PDF...';
                    log.style.color = 'var(--success)';
                }
                // Create a temporary link with cache-busting timestamp
                const a = document.createElement('a');
                a.href = '/api/download/output.pdf?t=' + Date.now();
                a.download = 'output.pdf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                if (progressPage) progressPage.textContent = 'Build failed';
                if (log) {
                    log.style.display = 'block';
                    log.textContent = result.output || 'Unknown error';
                    log.style.color = 'var(--danger)';
                }
            }
        } catch (err) {
            clearInterval(progressInterval);
            if (progressPage) progressPage.textContent = 'Build failed';
            if (log) {
                log.style.display = 'block';
                log.textContent = err.message || 'Network error';
                log.style.color = 'var(--danger)';
            }
            if (buildBtn) {
                buildBtn.disabled = false;
                buildBtn.innerHTML = '<i data-lucide="zap"></i> Build PDF';
            }
        }

        if (window.lucide) lucide.createIcons();
    },

    // ============================================================
    // UNIFIED WEBSOCKET - Sync, Cursors, Preview, Diagnostics
    // ============================================================

    connectDocSocket: function () {
        if (this.state.wsRetryCount === undefined) {
            this.state.wsRetryCount = 0;
        }

        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const name = encodeURIComponent(this.state.sessionName);

            // Generate or retrieve persistent client ID
            let clientId = sessionStorage.getItem('noteworthy_client_id');
            if (!clientId) {
                clientId = Math.random().toString(36).substring(2, 15);
                sessionStorage.setItem('noteworthy_client_id', clientId);
            }

            this.state.docSocket = new WebSocket(`${protocol}//${window.location.host}/ws/doc?name=${name}&id=${clientId}`);

            this.state.docSocket.onopen = () => {
                console.log('[Doc] Connected');
                this.state.wsRetryCount = 0;

                // Rejoin current file if we have one
                if (this.state.activeFile) {
                    this.joinFile(this.state.activeFile);
                }
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
                // Initial connection - store user ID and populate online users
                this.state.userId = msg.userId;
                this.state.userColor = msg.color;
                console.log(`[Doc] Joined as ${msg.userId}`);

                // Initialize online users from server list
                if (msg.users && Array.isArray(msg.users)) {
                    this.state.onlineUsers = {};
                    msg.users.forEach(u => {
                        this.state.onlineUsers[u.id] = u;
                    });
                    this.renderOnlineUsers();
                }
                break;

            case 'init':
                // Received file content from server
                if (this.state.editor) {
                    this.state.applyingRemote = true;
                    const ext = this.state.activeFile?.split('.').pop() || 'typ';
                    const lang = ext === 'typ' ? 'markdown' : (ext === 'json' ? 'json' : 'plaintext');
                    monaco.editor.setModelLanguage(this.state.editor.getModel(), lang);
                    this.state.editor.setValue(msg.content);
                    this.state.applyingRemote = false;
                    document.getElementById('save-status').textContent = '';
                }
                break;

            case 'content':
                // Remote user edited the document
                if (msg.userId !== this.state.userId && this.state.editor) {
                    this.state.applyingRemote = true;
                    // Save cursor position
                    const pos = this.state.editor.getPosition();
                    this.state.editor.setValue(msg.content);
                    // Restore cursor position
                    if (pos) this.state.editor.setPosition(pos);
                    this.state.applyingRemote = false;
                }
                break;

            case 'cursor':
                // Remote user cursor update
                this.updateRemoteCursor(msg);
                break;

            case 'preview':
                // Preview updates
                this.updatePreview(msg.updates);
                break;

            case 'diagnostics':
                // LSP diagnostics from server
                this.applyDiagnostics(msg.diagnostics);
                break;

            case 'user_joined':
            case 'user_left':
            case 'user_updated':
                // User presence updates
                this.updateUserPresence(msg);
                break;

            case 'chat':
                // Chat message
                if (typeof CollaborationManager !== 'undefined' && this.collab) {
                    this.collab.addChatMessage(msg);
                } else {
                    this.addChatMessage(msg);
                }
                break;
        }
    },

    joinFile: function (path) {
        if (this.state.docSocket && this.state.docSocket.readyState === WebSocket.OPEN) {
            this.state.docSocket.send(JSON.stringify({
                type: 'join',
                path: path
            }));
        }
    },

    syncContent: function () {
        if (!this.state.activeFile || !this.state.editor) return;
        if (!this.state.docSocket || this.state.docSocket.readyState !== WebSocket.OPEN) return;

        const content = this.state.editor.getValue();
        this.state.docSocket.send(JSON.stringify({
            type: 'edit',
            path: this.state.activeFile,
            content: content
        }));

        // Mark as saved since server will save to disk
        document.getElementById('save-status').textContent = 'Synced';
        setTimeout(() => document.getElementById('save-status').textContent = '', 1500);
    },

    sendCursor: function (position) {
        if (!this.state.docSocket || this.state.docSocket.readyState !== WebSocket.OPEN) return;

        this.state.docSocket.send(JSON.stringify({
            type: 'cursor',
            line: position.lineNumber,
            column: position.column
        }));
    },

    updateRemoteCursor: function (msg) {
        // Remote cursor rendering via Monaco decorations
        if (!this.state.editor) return;

        // Store cursor positions for "follow user" feature
        if (!this.state.userCursors) this.state.userCursors = {};
        this.state.userCursors[msg.userId] = { line: msg.line, column: msg.column };

        // Store decorations by user ID
        if (!this.state.remoteCursors) this.state.remoteCursors = {};

        const decorations = [{
            range: new monaco.Range(msg.line, msg.column, msg.line, msg.column + 1),
            options: {
                className: `remote-cursor-${msg.userId}`,
                hoverMessage: { value: msg.name },
                beforeContentClassName: 'remote-cursor-line',
                stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges
            }
        }];

        // Add dynamic CSS for this user's cursor color
        this.addCursorStyle(msg.userId, msg.color);

        this.state.remoteCursors[msg.userId] = this.state.editor.deltaDecorations(
            this.state.remoteCursors[msg.userId] || [],
            decorations
        );
    },

    addCursorStyle: function (userId, color) {
        const styleId = `cursor-style-${userId}`;
        if (document.getElementById(styleId)) return;

        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .remote-cursor-${userId} {
                background-color: ${color}40;
                border-left: 2px solid ${color};
            }
        `;
        document.head.appendChild(style);
    },

    applyDiagnostics: function (diagnostics) {
        if (!this.state.editor) return;

        // Clear old markers
        monaco.editor.setModelMarkers(this.state.editor.getModel(), 'owner', []);

        const errorCountEl = document.getElementById('error-count');
        const errorCountText = document.getElementById('error-count-text');
        const errorDetailsEl = document.getElementById('error-details');

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

            // Error overlay removed per user request
            if (errorCountEl) errorCountEl.style.display = 'none';
        } else {
            if (errorCountEl) errorCountEl.style.display = 'none';
        }
    },

    updateUserPresence: function (msg) {
        // Track connected users
        if (!this.state.onlineUsers) this.state.onlineUsers = {};

        if (msg.type === 'user_joined') {
            this.state.onlineUsers[msg.user.id] = msg.user;
        } else if (msg.type === 'user_left') {
            delete this.state.onlineUsers[msg.userId];
            // Clean up their cursor decorations
            if (this.state.remoteCursors && this.state.remoteCursors[msg.userId]) {
                this.state.editor.deltaDecorations(this.state.remoteCursors[msg.userId], []);
                delete this.state.remoteCursors[msg.userId];
            }
        } else if (msg.type === 'user_updated' && msg.user) {
            this.state.onlineUsers[msg.user.id] = msg.user;
        }

        // Re-render user avatars
        this.renderOnlineUsers();
    },

    renderOnlineUsers: function () {
        const container = document.getElementById('online-users');
        if (!container) return;

        container.innerHTML = '';

        const users = Object.values(this.state.onlineUsers || {});
        users.forEach(user => {
            if (user.id === this.state.userId) return; // Skip self

            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.style.backgroundColor = user.color;
            avatar.style.cursor = 'pointer';

            // Show file path in tooltip if available
            const fileInfo = user.file ? `\n📄 ${user.file}` : '';
            avatar.title = `${user.name}${fileInfo}\nClick to follow`;
            avatar.textContent = user.name.charAt(0).toUpperCase();

            // Click to navigate to their file and cursor position
            avatar.onclick = () => {
                if (user.file) {
                    // Open their file
                    this.openFile(user.file);

                    // Jump to their cursor position after a short delay (for file to load)
                    if (this.state.userCursors && this.state.userCursors[user.id]) {
                        const cursor = this.state.userCursors[user.id];
                        setTimeout(() => {
                            if (this.state.editor) {
                                this.state.editor.revealLineInCenter(cursor.line);
                                this.state.editor.setPosition({ lineNumber: cursor.line, column: cursor.column });
                                this.state.editor.focus();
                            }
                        }, 200);
                    }
                }
            };

            container.appendChild(avatar);
        });
    },

    addChatMessage: function (msg) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = 'chat-message';
        div.innerHTML = `
            <span class="chat-user" style="color: ${msg.color}">${msg.name}</span>
            <span class="chat-text">${msg.text}</span>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;

        // Show unread indicator if chat is hidden
        const panel = document.getElementById('chat-panel');
        if (panel && panel.classList.contains('hidden')) {
            const badge = document.getElementById('chat-unread-badge');
            if (badge) badge.style.display = 'block';
        }
    },

    updatePreview: function (updates) {
        const container = document.getElementById('preview-container');
        if (!container) return;

        // Clear placeholder or loading skeleton
        if (container.querySelector('.preview-placeholder') || container.querySelector('.preview-loading')) {
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
        // Generate theme options from EDITOR_THEMES
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
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
                        This name will be visible to other users editing the same file. It is saved in your browser storage.
                    </p>
                </div>

                <div class="form-group">
                    <label>Editor Theme</label>
                    <select id="editor-theme-select" onchange="app.setEditorTheme(this.value)">
                        ${themeOptions}
                    </select>
                    <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px;">
                        Choose a color scheme for the code editor. Your preference is saved in your browser.
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

        document.getElementById('config-modal-overlay').classList.remove('active');
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

            // Clear unread badge
            const badge = document.getElementById('chat-unread-badge');
            if (badge) badge.style.display = 'none';
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

        if (this.state.docSocket && this.state.docSocket.readyState === WebSocket.OPEN) {
            this.state.docSocket.send(JSON.stringify({
                type: 'chat',
                text: text,
                timestamp: Date.now()
            }));
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


