# Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Module Development Philosophy

Noteworthy follows a modular architecture designed to separate **logic** from **styling**.

### 1. Separation of Concerns
-   **Implementation Files** (`draw.typ`, `impl.typ`): These files usually contain the raw logic. They often accept a `theme` parameter but **should not** hardcode theme values (e.g., specific colors) unless absolutely necessary.
-   **Module Entry Point** (`mod.typ`): This file acts as the interface between the raw implementation and the rest of the system.
    -   It imports the `active-theme` from `core/setup.typ`.
    -   It wraps the raw functions to inject the themed values automatically.
    -   It exports these "themed wrappers" for the user to use.

### 2. File Structure
A typical module in `templates/module/` looks like this:

```text
templates/module/my-module/
├── mod.typ      # The entry point
├── draw.typ     # Drawing logic (if using CeTZ)
├── core.typ     # Pure data manipulation logic
└── ...
```

### 3. Creating a New Module

1.  **Create the directory**: `templates/module/new-module-name`.
2.  **Draft Implementation**: Write your raw functions in `impl.typ` (or `draw.typ`).
    ```typst
    // impl.typ
    #let my-raw-function(content, theme: (:)) = {
       let color = theme.at("primary", default: black)
       block(fill: color, content)
    }
    ```
3.  **Create `mod.typ`**:
    ```typst
    // mod.typ
    #import "../../core/setup.typ": active-theme
    #import "impl.typ": my-raw-function as my-raw-impl

    // Export the themed wrapper
    #let my-function(content) = my-raw-impl(content, theme: active-theme)
    ```
4.  **Register**: Import your module in `templates/templater.typ` so it's available globally.
    ```typst
    // templates/templater.typ
    #import "./module/new-module/mod.typ": *
    ```
5.  **Document**: Create a documentation file in `docs/modules/new-module.md`.

## 4. Verification & Safety
To ensure you are using the safe, malware-free version of Noteworthy:

1.  **Verify the Source:** Ensure you cloned this from `https://github.com/sihooleebd/noteworthy`.
2.  **Check Metadata:** PDFs generated with this tool automatically include a metadata link to the original repository.
3.  **Report Clones:** If you find this code hosted elsewhere without a direct link back to this repository, please report it to us immediately.
