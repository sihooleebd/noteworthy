{
  description = "Noteworthy — Typst document builder with TUI, CLI, and web GUI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (
        pkgs:
        let
          # External binaries the build pipeline shells out to
          # (noteworthy/core/deps.py, core/build.py, gui/preview.py).
          typstTools = [
            pkgs.typst # document compiler
            pkgs.tinymist # live preview + LSP (noteworthy/gui/preview.py spawns it)
            pkgs."poppler-utils" # pdfinfo, pdfunite
            pkgs.ghostscript # gs — pdfunite fallback + pdfmark metadata
          ];

          # Runtime imports found in noteworthy/ plus uvicorn[standard] extras.
          pythonDeps =
            ps: with ps; [
              fastapi
              uvicorn
              websockets
              uvloop
              httptools
              watchfiles
              pycrdt
              pycrdt-websocket
              pypdf
              python-multipart # multipart/form-data for /api/upload
            ];

          devDeps =
            ps: with ps; [
              pytest
              ruff
            ];

          pythonEnv = pkgs.python3.withPackages (ps: pythonDeps ps ++ devDeps ps);

          # `noteworthy` on PATH without installing anything; BASE_DIR in
          # noteworthy/config.py resolves to the checkout, so this must be run
          # from the repo root (PYTHONPATH is set by the shellHook).
          noteworthy = pkgs.writeShellScriptBin "noteworthy" ''
            exec ${pythonEnv}/bin/python -m noteworthy "$@"
          '';
        in
        {
          # Nix-managed Python — no `uv sync`, no .venv.
          default = pkgs.mkShell {
            name = "noteworthy-dev";

            packages = [
              pythonEnv
              noteworthy
            ]
            ++ typstTools;

            shellHook = ''
              root=$(${pkgs.git}/bin/git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
              export PYTHONPATH="$root''${PYTHONPATH:+:$PYTHONPATH}"
              export PYTHONDONTWRITEBYTECODE=1

              # Skip the banner when direnv sources this on every `cd`.
              if [ -z "''${DIRENV_IN_ENVRC:-}" ]; then
                echo "noteworthy dev shell"
                echo "  python  $(python --version | cut -d' ' -f2)"
                echo "  typst   $(typst --version | cut -d' ' -f2)"
                echo ""
                echo "  noteworthy          TUI"
                echo "  noteworthy -g       Studio (web GUI)"
                echo "  ./noteworthy_cli.py CLI builder"
                echo "  ruff check .        lint"
              fi
            '';
          };

          # Mirrors CONTRIBUTING.md (`uv sync` + .venv) for parity with other
          # contributors. Python comes from nixpkgs; uv only resolves wheels.
          uv = pkgs.mkShell {
            name = "noteworthy-uv";

            packages = [
              pkgs.python313
              pkgs.uv
            ]
            ++ typstTools;

            env = {
              # Never let uv fetch its own (non-NixOS-compatible) interpreter.
              UV_PYTHON_DOWNLOADS = "never";
              UV_PYTHON = "${pkgs.python313}/bin/python3.13";
              # Binary wheels (pycrdt, uvloop, ...) link against a plain libstdc++/libz.
              LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
                pkgs.stdenv.cc.cc.lib
                pkgs.zlib
              ];
            };

            shellHook = ''
              echo "noteworthy uv shell — run: uv sync && source .venv/bin/activate"
            '';
          };
        }
      );

      formatter = forAllSystems (pkgs: pkgs.nixfmt);
    };
}
