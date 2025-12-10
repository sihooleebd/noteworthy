import curses
import json
import shutil
from pathlib import Path
from ..base import TUI
from ...config import SCHEMES_FILE, BASE_DIR

class SchemesWizard:

    def __init__(self, scr):
        self.scr = scr

    def run(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        bw, bh = (min(60, w - 4), 8)
        bx, by = ((w - bw) // 2, (h - bh) // 2)
        TUI.draw_box(self.scr, by, bx, bh, bw, 'SCHEMES SETUP')
        TUI.safe_addstr(self.scr, by + 2, bx + 2, 'Schemes configuration is missing.', curses.color_pair(4))
        TUI.safe_addstr(self.scr, by + 3, bx + 2, 'Restore default color themes?', curses.color_pair(1) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, by + 5, bx + 2, 'Press Enter to Restore  |  Esc to Cancel', curses.color_pair(4) | curses.A_DIM)
        self.scr.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return None
            k = self.scr.getch()
            if k == 27:
                return None
            elif k in (ord('\n'), 10, curses.KEY_ENTER):
                break
        try:
            minimal_schemes = {
    "noteworthy-dark": {
        "page-fill": "#262323",
        "text-main": "#d8d0cc",
        "text-heading": "#ddbfa1",
        "text-muted": "#8f8582",
        "text-accent": "#d49c93",
        "blocks": {
            "definition": {
                "fill": "#2f332e",
                "stroke": "#9cb095",
                "title": "Definition"
            },
            "equation": {
                "fill": "#33302a",
                "stroke": "#d1c29b",
                "title": "Equation"
            },
            "example": {
                "fill": "#332b28",
                "stroke": "#d4aa8e",
                "title": "Example"
            },
            "solution": {
                "fill": "#2e282d",
                "stroke": "#bba3b8",
                "title": "Solution"
            },
            "proof": {
                "fill": "#302626",
                "stroke": "#c48378",
                "title": "Proof"
            },
            "note": {
                "fill": "#332729",
                "stroke": "#d6999e",
                "title": "Note"
            },
            "notation": {
                "fill": "#262e2e",
                "stroke": "#8caeb0",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#262a30",
                "stroke": "#8ea4b8",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#333028",
                "stroke": "#e0cda6",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#ddbfa1",
            "highlight": "#d4aa8e",
            "grid-opacity": 0.15
        }
    },
    "rose-pine": {
        "page-fill": "#191724",
        "text-main": "#e0def4",
        "text-heading": "#ebbcba",
        "text-muted": "#908caa",
        "text-accent": "#c4a7e7",
        "blocks": {
            "definition": {
                "fill": "#1f1d2e",
                "stroke": "#31748f",
                "title": "Definition"
            },
            "equation": {
                "fill": "#26233a",
                "stroke": "#f6c177",
                "title": "Equation"
            },
            "example": {
                "fill": "#1f1d2e",
                "stroke": "#ebbcba",
                "title": "Example"
            },
            "solution": {
                "fill": "#26233a",
                "stroke": "#c4a7e7",
                "title": "Solution"
            },
            "proof": {
                "fill": "#1f1d2e",
                "stroke": "#eb6f92",
                "title": "Proof"
            },
            "note": {
                "fill": "#26233a",
                "stroke": "#9ccfd8",
                "title": "Note"
            },
            "notation": {
                "fill": "#1f1d2e",
                "stroke": "#908caa",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#26233a",
                "stroke": "#31748f",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#1f1d2e",
                "stroke": "#f6c177",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#ebbcba",
            "highlight": "#31748f",
            "grid-opacity": 0.15
        }
    },
    "noteworthy-light": {
        "page-fill": "#fcf6e3",
        "text-main": "#4a4545",
        "text-heading": "#8f6f5e",
        "text-muted": "#a39896",
        "text-accent": "#c48378",
        "blocks": {
            "definition": {
                "fill": "#e6ece9",
                "stroke": "#94a187",
                "title": "Definition"
            },
            "equation": {
                "fill": "#f2edd8",
                "stroke": "#c4b28a",
                "title": "Equation"
            },
            "example": {
                "fill": "#f7ebe9",
                "stroke": "#cf9c8e",
                "title": "Example"
            },
            "solution": {
                "fill": "#f0eaf0",
                "stroke": "#a69aa6",
                "title": "Solution"
            },
            "proof": {
                "fill": "#ebe9e6",
                "stroke": "#a38f85",
                "title": "Proof"
            },
            "note": {
                "fill": "#f5e6e8",
                "stroke": "#d6999e",
                "title": "Note"
            },
            "notation": {
                "fill": "#e6eef0",
                "stroke": "#8fa6ac",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#e8f0f5",
                "stroke": "#94aab8",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#f5f0dc",
                "stroke": "#d1b679",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#8f6f5e",
            "highlight": "#31748f",
            "grid-opacity": 0.15
        }
    },
    "nord": {
        "page-fill": "#2e3440",
        "text-main": "#eceff4",
        "text-heading": "#88c0d0",
        "text-muted": "#4c566a",
        "text-accent": "#81a1c1",
        "blocks": {
            "definition": {
                "fill": "#3b4252",
                "stroke": "#a3be8c",
                "title": "Definition"
            },
            "equation": {
                "fill": "#3b4252",
                "stroke": "#ebcb8b",
                "title": "Equation"
            },
            "example": {
                "fill": "#3b4252",
                "stroke": "#d08770",
                "title": "Example"
            },
            "solution": {
                "fill": "#434c5e",
                "stroke": "#b48ead",
                "title": "Solution"
            },
            "proof": {
                "fill": "#434c5e",
                "stroke": "#bf616a",
                "title": "Proof"
            },
            "note": {
                "fill": "#3b4252",
                "stroke": "#5e81ac",
                "title": "Note"
            },
            "notation": {
                "fill": "#434c5e",
                "stroke": "#8fbcbb",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#3b4252",
                "stroke": "#88c0d0",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#434c5e",
                "stroke": "#ebcb8b",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#88c0d0",
            "highlight": "#81a1c1",
            "grid-opacity": 0.15
        }
    },
    "dracula": {
        "page-fill": "#282a36",
        "text-main": "#f8f8f2",
        "text-heading": "#bd93f9",
        "text-muted": "#6272a4",
        "text-accent": "#ff79c6",
        "blocks": {
            "definition": {
                "fill": "#343746",
                "stroke": "#50fa7b",
                "title": "Definition"
            },
            "equation": {
                "fill": "#343746",
                "stroke": "#f1fa8c",
                "title": "Equation"
            },
            "example": {
                "fill": "#343746",
                "stroke": "#ffb86c",
                "title": "Example"
            },
            "solution": {
                "fill": "#44475a",
                "stroke": "#bd93f9",
                "title": "Solution"
            },
            "proof": {
                "fill": "#44475a",
                "stroke": "#ff5555",
                "title": "Proof"
            },
            "note": {
                "fill": "#343746",
                "stroke": "#8be9fd",
                "title": "Note"
            },
            "notation": {
                "fill": "#44475a",
                "stroke": "#50fa7b",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#343746",
                "stroke": "#ff79c6",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#44475a",
                "stroke": "#f1fa8c",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#bd93f9",
            "highlight": "#ff79c6",
            "grid-opacity": 0.15
        }
    },
    "gruvbox": {
        "page-fill": "#282828",
        "text-main": "#ebdbb2",
        "text-heading": "#fabd2f",
        "text-muted": "#928374",
        "text-accent": "#fe8019",
        "blocks": {
            "definition": {
                "fill": "#32302f",
                "stroke": "#b8bb26",
                "title": "Definition"
            },
            "equation": {
                "fill": "#32302f",
                "stroke": "#fabd2f",
                "title": "Equation"
            },
            "example": {
                "fill": "#32302f",
                "stroke": "#fe8019",
                "title": "Example"
            },
            "solution": {
                "fill": "#3c3836",
                "stroke": "#d3869b",
                "title": "Solution"
            },
            "proof": {
                "fill": "#3c3836",
                "stroke": "#fb4934",
                "title": "Proof"
            },
            "note": {
                "fill": "#32302f",
                "stroke": "#83a598",
                "title": "Note"
            },
            "notation": {
                "fill": "#3c3836",
                "stroke": "#8ec07c",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#32302f",
                "stroke": "#fabd2f",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#3c3836",
                "stroke": "#d79921",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#fabd2f",
            "highlight": "#fe8019",
            "grid-opacity": 0.15
        }
    },
    "catppuccin-mocha": {
        "page-fill": "#1e1e2e",
        "text-main": "#cdd6f4",
        "text-heading": "#89b4fa",
        "text-muted": "#6c7086",
        "text-accent": "#f5c2e7",
        "blocks": {
            "definition": {
                "fill": "#313244",
                "stroke": "#a6e3a1",
                "title": "Definition"
            },
            "equation": {
                "fill": "#313244",
                "stroke": "#f9e2af",
                "title": "Equation"
            },
            "example": {
                "fill": "#313244",
                "stroke": "#fab387",
                "title": "Example"
            },
            "solution": {
                "fill": "#45475a",
                "stroke": "#cba6f7",
                "title": "Solution"
            },
            "proof": {
                "fill": "#45475a",
                "stroke": "#f38ba8",
                "title": "Proof"
            },
            "note": {
                "fill": "#313244",
                "stroke": "#89dceb",
                "title": "Note"
            },
            "notation": {
                "fill": "#45475a",
                "stroke": "#94e2d5",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#313244",
                "stroke": "#89b4fa",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#45475a",
                "stroke": "#f9e2af",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#89b4fa",
            "highlight": "#f5c2e7",
            "grid-opacity": 0.15
        }
    },
    "catppuccin-latte": {
        "page-fill": "#eff1f5",
        "text-main": "#4c4f69",
        "text-heading": "#1e66f5",
        "text-muted": "#9ca0b0",
        "text-accent": "#ea76cb",
        "blocks": {
            "definition": {
                "fill": "#e6e9ef",
                "stroke": "#40a02b",
                "title": "Definition"
            },
            "equation": {
                "fill": "#e6e9ef",
                "stroke": "#df8e1d",
                "title": "Equation"
            },
            "example": {
                "fill": "#e6e9ef",
                "stroke": "#fe640b",
                "title": "Example"
            },
            "solution": {
                "fill": "#dce0e8",
                "stroke": "#8839ef",
                "title": "Solution"
            },
            "proof": {
                "fill": "#dce0e8",
                "stroke": "#d20f39",
                "title": "Proof"
            },
            "note": {
                "fill": "#e6e9ef",
                "stroke": "#04a5e5",
                "title": "Note"
            },
            "notation": {
                "fill": "#dce0e8",
                "stroke": "#179299",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#e6e9ef",
                "stroke": "#1e66f5",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#dce0e8",
                "stroke": "#df8e1d",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#1e66f5",
            "highlight": "#ea76cb",
            "grid-opacity": 0.15
        }
    },
    "solarized-dark": {
        "page-fill": "#002b36",
        "text-main": "#839496",
        "text-heading": "#268bd2",
        "text-muted": "#586e75",
        "text-accent": "#d33682",
        "blocks": {
            "definition": {
                "fill": "#073642",
                "stroke": "#859900",
                "title": "Definition"
            },
            "equation": {
                "fill": "#073642",
                "stroke": "#b58900",
                "title": "Equation"
            },
            "example": {
                "fill": "#073642",
                "stroke": "#cb4b16",
                "title": "Example"
            },
            "solution": {
                "fill": "#073642",
                "stroke": "#6c71c4",
                "title": "Solution"
            },
            "proof": {
                "fill": "#073642",
                "stroke": "#dc322f",
                "title": "Proof"
            },
            "note": {
                "fill": "#073642",
                "stroke": "#2aa198",
                "title": "Note"
            },
            "notation": {
                "fill": "#073642",
                "stroke": "#268bd2",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#073642",
                "stroke": "#268bd2",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#073642",
                "stroke": "#b58900",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#268bd2",
            "highlight": "#d33682",
            "grid-opacity": 0.15
        }
    },
    "solarized-light": {
        "page-fill": "#fdf6e3",
        "text-main": "#657b83",
        "text-heading": "#268bd2",
        "text-muted": "#93a1a1",
        "text-accent": "#d33682",
        "blocks": {
            "definition": {
                "fill": "#eee8d5",
                "stroke": "#859900",
                "title": "Definition"
            },
            "equation": {
                "fill": "#eee8d5",
                "stroke": "#b58900",
                "title": "Equation"
            },
            "example": {
                "fill": "#eee8d5",
                "stroke": "#cb4b16",
                "title": "Example"
            },
            "solution": {
                "fill": "#eee8d5",
                "stroke": "#6c71c4",
                "title": "Solution"
            },
            "proof": {
                "fill": "#eee8d5",
                "stroke": "#dc322f",
                "title": "Proof"
            },
            "note": {
                "fill": "#eee8d5",
                "stroke": "#2aa198",
                "title": "Note"
            },
            "notation": {
                "fill": "#eee8d5",
                "stroke": "#268bd2",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#eee8d5",
                "stroke": "#268bd2",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#eee8d5",
                "stroke": "#b58900",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#268bd2",
            "highlight": "#d33682",
            "grid-opacity": 0.15
        }
    },
    "tokyo-night": {
        "page-fill": "#1a1b26",
        "text-main": "#c0caf5",
        "text-heading": "#7aa2f7",
        "text-muted": "#565f89",
        "text-accent": "#bb9af7",
        "blocks": {
            "definition": {
                "fill": "#24283b",
                "stroke": "#9ece6a",
                "title": "Definition"
            },
            "equation": {
                "fill": "#24283b",
                "stroke": "#e0af68",
                "title": "Equation"
            },
            "example": {
                "fill": "#24283b",
                "stroke": "#ff9e64",
                "title": "Example"
            },
            "solution": {
                "fill": "#292e42",
                "stroke": "#bb9af7",
                "title": "Solution"
            },
            "proof": {
                "fill": "#292e42",
                "stroke": "#f7768e",
                "title": "Proof"
            },
            "note": {
                "fill": "#24283b",
                "stroke": "#7dcfff",
                "title": "Note"
            },
            "notation": {
                "fill": "#292e42",
                "stroke": "#2ac3de",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#24283b",
                "stroke": "#7aa2f7",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#292e42",
                "stroke": "#e0af68",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#7aa2f7",
            "highlight": "#bb9af7",
            "grid-opacity": 0.15
        }
    },
    "everforest": {
        "page-fill": "#2d353b",
        "text-main": "#d3c6aa",
        "text-heading": "#a7c080",
        "text-muted": "#859289",
        "text-accent": "#e69875",
        "blocks": {
            "definition": {
                "fill": "#343f44",
                "stroke": "#a7c080",
                "title": "Definition"
            },
            "equation": {
                "fill": "#343f44",
                "stroke": "#dbbc7f",
                "title": "Equation"
            },
            "example": {
                "fill": "#343f44",
                "stroke": "#e69875",
                "title": "Example"
            },
            "solution": {
                "fill": "#3d484d",
                "stroke": "#d699b6",
                "title": "Solution"
            },
            "proof": {
                "fill": "#3d484d",
                "stroke": "#e67e80",
                "title": "Proof"
            },
            "note": {
                "fill": "#343f44",
                "stroke": "#83c092",
                "title": "Note"
            },
            "notation": {
                "fill": "#3d484d",
                "stroke": "#7fbbb3",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#343f44",
                "stroke": "#a7c080",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#3d484d",
                "stroke": "#dbbc7f",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#a7c080",
            "highlight": "#e69875",
            "grid-opacity": 0.15
        }
    },
    "moonlight": {
        "page-fill": "#212337",
        "text-main": "#c8d3f5",
        "text-heading": "#82aaff",
        "text-muted": "#7a88cf",
        "text-accent": "#c099ff",
        "blocks": {
            "definition": {
                "fill": "#2f334d",
                "stroke": "#c3e88d",
                "title": "Definition"
            },
            "equation": {
                "fill": "#2f334d",
                "stroke": "#ffc777",
                "title": "Equation"
            },
            "example": {
                "fill": "#2f334d",
                "stroke": "#ff966c",
                "title": "Example"
            },
            "solution": {
                "fill": "#3b3f5c",
                "stroke": "#c099ff",
                "title": "Solution"
            },
            "proof": {
                "fill": "#3b3f5c",
                "stroke": "#ff757f",
                "title": "Proof"
            },
            "note": {
                "fill": "#2f334d",
                "stroke": "#86e1fc",
                "title": "Note"
            },
            "notation": {
                "fill": "#3b3f5c",
                "stroke": "#4fd6be",
                "title": "Notation"
            },
            "analysis": {
                "fill": "#2f334d",
                "stroke": "#82aaff",
                "title": "Analysis"
            },
            "theorem": {
                "fill": "#3b3f5c",
                "stroke": "#ffc777",
                "title": "Theorem"
            }
        },
        "plot": {
            "stroke": "#82aaff",
            "highlight": "#c099ff",
            "grid-opacity": 0.15
        }
    }
}
            default_src = BASE_DIR / 'templates/config/schemes.json'
            if default_src.exists() and default_src != SCHEMES_FILE:
                shutil.copy(default_src, SCHEMES_FILE)
            else:
                SCHEMES_FILE.parent.mkdir(parents=True, exist_ok=True)
                SCHEMES_FILE.write_text(json.dumps(minimal_schemes, indent=4))
            return True
        except:
            return None