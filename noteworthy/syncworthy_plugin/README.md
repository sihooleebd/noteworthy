# Noteworthy as a Syncworthy plugin

`noteworthy -g` runs Syncworthy with `NoteworthyPlugin`; `noteworthy -g --old-gui` starts the previous built-in GUI (`noteworthy/gui/`, removed in a later phase).

Syncworthy is not published yet. Make it importable next to this checkout, any of:

- `nix develop` (the dev shell adds `../syncworthy` to PYTHONPATH; override with `SYNCWORTHY_SRC`)
- `pip install -e ../syncworthy` / `uv sync --extra gui` (see `[tool.uv.sources]`)
- `export PYTHONPATH=../syncworthy:$PYTHONPATH`

The entry point `syncworthy.plugins: noteworthy` is declared in pyproject.toml, so `syncworthy serve <project>` with `plugins = ["noteworthy"]` in `syncworthy.toml` works once the package is installed.
