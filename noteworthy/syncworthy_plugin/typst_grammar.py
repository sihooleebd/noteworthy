"""A Monarch grammar for Typst, as plain data (it is sent to the browser as JSON).

Typst has three modes and the grammar models each as states:

* **markup** (the file's top level, and ``[...]`` content blocks): headings, lists,
  strong/emphasis, raw text, labels and references, ``#`` code embeds;
* **code** (after a ``#``, inside ``(...)`` argument lists and ``{...}`` blocks):
  keywords, strings, numbers with units, calls, ``[...]`` content arguments;
* **math** (``$ ... $``): symbols, calls, strings, ``#`` embeds.

Brackets nest by pushing and popping states, so ``#f(a)[ markup $math$ ]`` colours
every level correctly across lines.  Token names are the ones Monaco's themes
already style (comment, keyword, string, number, type, tag, strong, emphasis ...).
"""

KEYWORDS = ["let", "set", "show", "import", "include", "if", "else", "for", "while", "in", "not", "and",
            "or", "return", "break", "continue", "as", "context"]
CONSTANTS = ["true", "false", "none", "auto"]
IDENT = r"[a-zA-Z_][\w\-]*"
UNITS = r"(?:pt|mm|cm|in|em|fr|deg|rad|%)"
NUMBER = rf"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?{UNITS}?"


def _code_rules():
    """Tokens of code mode, shared by every code state."""
    return [
        {"include": "@comments"},
        [r'"', {"token": "string", "next": "@string"}],
        [r"\$", {"token": "string.math", "next": "@math"}],
        [r"`{3,}", {"token": "string.raw", "next": "@rawBlock"}],
        [r"`", {"token": "string.raw", "next": "@rawInline"}],
        [NUMBER, "number"],
        [r"<" + IDENT + r">", "tag"],                                   # label
        [rf"(?:{'|'.join(KEYWORDS)})(?![\w\-])", "keyword"],
        [rf"(?:{'|'.join(CONSTANTS)})(?![\w\-])", "constant"],
        [rf"({IDENT})(\s*)(:)(?!:)", ["variable.parameter", "", "delimiter"]],   # name: value
        [rf"{IDENT}(?=\s*[(\[])", "type.identifier"],                   # call
        [rf"\.{IDENT}(?=\s*[(\[])", "type.identifier"],
        [rf"\.{IDENT}", "identifier"],
        [IDENT, "identifier"],
        [r"\(", {"token": "delimiter.parenthesis", "next": "@parenCode"}],
        [r"\{", {"token": "delimiter.curly", "next": "@braceCode"}],
        [r"\[", {"token": "delimiter.square", "next": "@contentBlock"}],
        [r"==>|<==>|=>|->|<=|>=|==|!=|\.\.|[-+*/=<>]", "operator"],
        [r"[,;:.]", "delimiter"],
        [r"\s+", ""],
    ]


def _markup_rules():
    return [
        {"include": "@comments"},
        [r"^\s*=+(?=\s)", {"token": "keyword.heading", "next": "@heading"}],
        [r"^\s*(?:[-+]|\d+\.)(?=\s)", "keyword"],                      # list markers
        [r"^\s*/(?=\s)", "keyword"],                                   # term list
        [r"`{3,}", {"token": "string.raw", "next": "@rawBlock"}],
        [r"`", {"token": "string.raw", "next": "@rawInline"}],
        [r"\$", {"token": "string.math", "next": "@math"}],
        [r"#(?:let|set|show|import|include|if|else|for|while|return|break|continue|context)(?![\w\-])",
         {"token": "keyword", "next": "@statement"}],
        [r"#" + IDENT, {"token": "type.identifier", "next": "@hashTail"}],
        [r"#(?=[({\[])", {"token": "delimiter", "next": "@hashTail"}],
        [r"\\(?:u\{[0-9a-fA-F]+\}|.)", "string.escape"],
        [r"<" + IDENT + r">", "tag"],                                   # label
        [r"@" + IDENT, "tag"],                                          # reference
        [r"\*(?=\S)[^*\n]*\*", "strong"],
        [r"(?<![\w])_(?=\S)[^_\n]*_(?![\w])", "emphasis"],
        [r"\[", {"token": "delimiter.square", "next": "@contentBlock"}],
        [r"~|---|--|\.\.\.", "string.escape"],
    ]


TYPST_MONARCH = {
    "defaultToken": "",
    "tokenPostfix": ".typ",
    "tokenizer": {
        "root": _markup_rules(),

        "comments": [
            [r"//.*$", "comment"],
            [r"/\*", {"token": "comment", "next": "@blockComment"}],
        ],
        "blockComment": [
            [r"[^/*]+", "comment"],
            [r"/\*", {"token": "comment", "next": "@blockComment"}],
            [r"\*/", {"token": "comment", "next": "@pop"}],
            [r"[/*]", "comment"],
        ],

        # `= Heading text` up to the end of the line (markup inside it still shows).
        # (A state ends at the start of the next line: `^` + rematch; Monarch never
        # evaluates a rule at the end of a line that had text on it.)
        "heading": [
            [r"^", {"token": "@rematch", "next": "@pop"}],
            {"include": "@headingText"},
        ],
        "headingText": [
            [r"\$", {"token": "string.math", "next": "@math"}],
            [r"#" + IDENT, {"token": "type.identifier", "next": "@hashTail"}],
            [r"<" + IDENT + r">", "tag"],
            [r"\\.", "string.escape"],
            [r"[^$#<\\\n]+", "keyword.heading"],
            [r"[$#<\\]", "keyword.heading"],
        ],

        # `[ ... ]`: markup again, until its bracket closes.
        "contentBlock": [
            [r"\]", {"token": "delimiter.square", "next": "@pop"}],
            *_markup_rules(),
        ],

        # What may follow `#name`: `.field`, `(args)`, `[content]`, chained.
        "hashTail": [
            [rf"\.{IDENT}(?=[.(\[])", "type.identifier"],
            [rf"\.{IDENT}", "identifier"],
            [r"\(", {"token": "delimiter.parenthesis", "next": "@parenCode"}],
            [r"\[", {"token": "delimiter.square", "next": "@contentBlock"}],
            [r"\{", {"token": "delimiter.curly", "next": "@braceCode"}],
            [r"", {"token": "", "next": "@pop"}],
        ],

        # `#let x = ...`, `#set text(...)`, `#show: f`, `#import "x": *`: code to the end of the line.
        "statement": [
            [r"^", {"token": "@rematch", "next": "@pop"}],
            *_code_rules(),
        ],

        "parenCode": [[r"\)", {"token": "delimiter.parenthesis", "next": "@pop"}], *_code_rules()],
        "braceCode": [[r"\}", {"token": "delimiter.curly", "next": "@pop"}], *_code_rules()],

        "string": [
            [r'[^\\"]+', "string"],
            [r"\\(?:u\{[0-9a-fA-F]+\}|.)", "string.escape"],
            [r'"', {"token": "string", "next": "@pop"}],
        ],

        "rawInline": [[r"[^`]+", "string.raw"], [r"`", {"token": "string.raw", "next": "@pop"}]],
        "rawBlock": [[r"[^`]+", "string.raw"], [r"`{3,}", {"token": "string.raw", "next": "@pop"}],
                     [r"`", "string.raw"]],

        "math": [
            [r"\$", {"token": "string.math", "next": "@pop"}],
            {"include": "@comments"},
            [r'"', {"token": "string", "next": "@string"}],
            [r"#" + IDENT, {"token": "type.identifier", "next": "@hashTail"}],
            [r"\\(?:u\{[0-9a-fA-F]+\}|.)", "string.escape"],
            [NUMBER, "number"],
            [r"[a-zA-Z]+(?=\()", "type.identifier"],       # math identifiers are letters; _ and ^ are operators
            [r"[a-zA-Z]+", "identifier"],
            [r"==>|<==>|=>|->|<-|<=|>=|!=|:=|[-+*/=<>|^_&!]", "operator"],
            [r"[()\[\]{}]", "delimiter.bracket"],
            [r"[,;:.']", "delimiter"],
            [r"\s+", ""],
        ],
    },
}

TYPST_CONFIGURATION = {
    "comments": {"lineComment": "//", "blockComment": ["/*", "*/"]},
    "brackets": [["{", "}"], ["[", "]"], ["(", ")"]],
    "autoClosingPairs": [
        {"open": "{", "close": "}"}, {"open": "[", "close": "]"}, {"open": "(", "close": ")"},
        {"open": '"', "close": '"', "notIn": ["string", "comment"]},
        {"open": "$", "close": "$", "notIn": ["string", "comment"]},
        {"open": "`", "close": "`", "notIn": ["string", "comment"]},
    ],
    "surroundingPairs": [
        {"open": "{", "close": "}"}, {"open": "[", "close": "]"}, {"open": "(", "close": ")"},
        {"open": '"', "close": '"'}, {"open": "$", "close": "$"}, {"open": "*", "close": "*"},
        {"open": "_", "close": "_"}, {"open": "`", "close": "`"},
    ],
    "folding": {"markers": {"start": r"^\s*//\s*#?region\b", "end": r"^\s*//\s*#?endregion\b"}},
    "wordPattern": r"[a-zA-Z_][\w\-]*|-?\d*\.\d\w*|[^\s`~!@#%^&*()=+\[{\]}\\|;:'\",.<>/?$]+",
}
