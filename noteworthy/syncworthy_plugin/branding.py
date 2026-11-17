"""Noteworthy's look: the ASCII welcome, the editor themes, the .typ defaults and icon.

Taken from the old GUI's app.js and utils.js unchanged; the plugin hands them to
Syncworthy as branding (see syncworthy/docs/PLUGINS.md for the keys).
"""

ASCII_LOGO = "         ,--. \n       ,--.'| \n   ,--,:  : | \n,`--.'`|  ' : \n|   :  :  | | \n:   |   \\ | : \n|   : '  '; | \n'   ' ;.    ; \n|   | | \\   | \n'   : |  ; .' \n|   | `--'   \n'   : |       \n;   |.'       \n'---'         "

TYP_ICON = "<svg width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" style=\"vertical-align:middle\"><rect x=\"2\" y=\"1\" width=\"12\" height=\"14\" rx=\"2\" fill=\"#4ECDC4\" opacity=\"0.2\" stroke=\"#4ECDC4\" stroke-width=\"1.2\"/><text x=\"8\" y=\"11\" text-anchor=\"middle\" font-size=\"7\" fill=\"#4ECDC4\" font-family=\"monospace\" font-weight=\"bold\">t</text></svg>"

THEMES = {
    "noteworthy-dark": {
        "label": "Noteworthy Dark",
        "base": "vs-dark",
        "colors": {
            "editor.background": "#0d0d0f",
            "editor.foreground": "#e8e8f0",
            "editor.lineHighlightBackground": "#16161a",
            "editor.selectionBackground": "#4ECDC430",
            "editor.inactiveSelectionBackground": "#4ECDC415",
            "editorCursor.foreground": "#4ECDC4",
            "editorLineNumber.foreground": "#3a3a4a",
            "editorLineNumber.activeForeground": "#4ECDC4",
            "editor.findMatchBackground": "#FFE66D30",
            "editor.findMatchHighlightBackground": "#FFE66D15",
            "scrollbar.shadow": "#00000000",
            "scrollbarSlider.background": "#4ECDC420",
            "scrollbarSlider.hoverBackground": "#4ECDC440",
            "scrollbarSlider.activeBackground": "#4ECDC460",
        },
    },
    "noteworthy-light": {
        "label": "Noteworthy Light",
        "base": "vs",
        "colors": {
            "editor.background": "#f5f5f7",
            "editor.foreground": "#1d1d1f",
            "editor.lineHighlightBackground": "#e8e8ec",
            "editor.selectionBackground": "#4ECDC440",
            "editorCursor.foreground": "#0066cc",
            "editorLineNumber.foreground": "#999aab",
            "editorLineNumber.activeForeground": "#0066cc",
        },
    },
}


def branding() -> dict:
    return {
        "name": "Noteworthy",
        "title": "Noteworthy Studio",
        "welcome_text": "NOTEWORTHY",
        "welcome_logo": ASCII_LOGO,
        "new_file_name": "new-file.typ",
        "new_file_dir": "content",
        "file_icons": {"typ": TYP_ICON},
        "tree_top": ["content"],
        "tree_bottom": ["assets", "templates", "config"],
        "themes": THEMES,
        "base_theme": "noteworthy-dark",
    }
