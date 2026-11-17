"""Noteworthy as a Syncworthy plugin.

Everything Noteworthy-specific the old web GUI did lives here: the live Typst
preview (typst watch SVGs, tinymist), the ``/api/check`` diagnostics, the PDF
build, the settings pages (metadata, constants, structure, preface, snippets,
indexignore, schemes, modules), the ``render_document``/``check_document`` MCP
tools, the look (ASCII welcome, themes, .typ defaults and icon) and the
frontend bundle under ``static/``.

Register: ``[project.entry-points."syncworthy.plugins"] noteworthy =
"noteworthy.syncworthy_plugin:NoteworthyPlugin"`` (pyproject.toml), or hand an
instance to ``syncworthy.create_app(root, plugins=[NoteworthyPlugin()])``, which
is what ``noteworthy -g`` does.

A Noteworthy project is the checkout the ``noteworthy`` package lives in:
``noteworthy.config`` resolves every path from the package location, so the
project root Syncworthy serves has to be that checkout.
"""
import logging
from pathlib import Path

from syncworthy.plugins import Action, Language, Plugin, SettingsPage

from ..config import BASE_DIR
from . import branding as _branding
from . import mcp_tools, startup
from .diagnostics import NoteworthyDiagnostics
from .previewer import NoteworthyPreviewer
from .routes import build_router

log = logging.getLogger("noteworthy.syncworthy_plugin")

# The Settings tabs, in the order the old GUI had them.  All are custom: their
# forms are drawn by static/config.js and saved through settings_routes.py.
SETTINGS_PAGES = [
    ("metadata", "Metadata"),
    ("constants", "Theme & Display"),
    ("hierarchy", "Structure"),
    ("schemes", "Color Themes"),
    ("snippets", "Snippets"),
    ("preface", "Preface"),
    ("ignored", "Ignored"),
    ("modules", "Modules"),
    ("info", "Info"),
]

# A first cut at a Typst Monarch grammar, carried as data; the frontend does not
# use it until the language registry exists (Syncworthy phase 2).
TYPST_MONARCH = {
    "tokenizer": {
        "root": [
            [r"//.*$", "comment"],
            [r"/\*", "comment", "@comment"],
            [r"^\s*=+\s.*$", "keyword"],
            [r"#[a-zA-Z_][\w\-]*", "type.identifier"],
            [r"\$", "string", "@math"],
            [r'"([^"\\]|\\.)*"', "string"],
            [r"`[^`]*`", "string.raw"],
            [r"\*[^*\n]+\*", "strong"],
            [r"_[^_\n]+_", "emphasis"],
        ],
        "comment": [[r"[^/*]+", "comment"], [r"\*/", "comment", "@pop"], [r"[/*]", "comment"]],
        "math": [[r"[^$\\]+", "string"], [r"\\.", "string.escape"], [r"\$", "string", "@pop"]],
    }
}


class NoteworthyPlugin(Plugin):
    name = "noteworthy"
    version = "0.3.0"

    # An existing project keeps its CRDT identity, and the old GUI can still open it.
    state_dir = ".noteworthy-crdt"
    mcp_token_env = "NOTEWORTHY_MCP_TOKEN"

    # The tree shows what the old one showed: four roots, no dotfiles.
    roots = ["assets", "config", "content", "templates"]
    create_roots = True
    tree_ignore = [".*"]
    ignore = ["output", "dist"]     # what the old MCP listing skipped

    static_dir = Path(__file__).parent / "static"
    static_scripts = ["config.js", "build.js", "preview.js", "noteworthy.js"]

    def __init__(self):
        self.ctx = None
        self.previewer = NoteworthyPreviewer()
        self.diagnostics = NoteworthyDiagnostics()

    # ---- lifecycle -----------------------------------------------------------
    def configure(self, ctx):
        self.ctx = ctx
        if ctx.root.resolve() != BASE_DIR.resolve():
            log.warning("serving %s, but this noteworthy package lives in %s: builds, previews and "
                        "settings use the package's project directory", ctx.root, BASE_DIR)

    async def on_startup(self, ctx):
        startup.validate_modules_json()
        startup.ensure_preface()
        startup.sync_imports()

    # ---- features ------------------------------------------------------------------
    def actions(self):
        from .build import run_build
        return [Action(id="build", label="Build PDF", run=run_build, icon="package",
                       description="Build the selected chapters and pages into output.pdf",
                       custom_ui=True)]

    def settings_pages(self):
        return [SettingsPage(id=i, title=t, custom=True) for i, t in SETTINGS_PAGES]

    def mcp_tools(self):
        return mcp_tools.tools()

    def languages(self):
        return [Language(id="typst", extensions=[".typ"], aliases=["Typst"],
                         monarch=TYPST_MONARCH,
                         configuration={"comments": {"lineComment": "//",
                                                     "blockComment": ["/*", "*/"]},
                                        "brackets": [["{", "}"], ["[", "]"], ["(", ")"]]})]

    def routers(self):
        return [build_router(self)]

    def branding(self):
        return _branding.branding()

    def status(self, ctx):
        return self.previewer.status()


# Entry point alias
plugin = NoteworthyPlugin
