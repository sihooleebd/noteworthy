# Noteworthy GUI

The graphical user interface for Noteworthy provides a modern, collaborative environment for editing Typst projects. It replaces the need for local TUI editors with a powerful web-based experience.

## Quick Start

```bash
python3 noteworthy.py --gui
```
The interface will be available at [`http://localhost:8000`](http://localhost:8000).

---

## Features

### 1. Live Preview & Editing
- **Instant Feedback**: See your changes compile in real-time.
- **Monaco Editor**: A fully-featured code editor with syntax highlighting for Typst.
- **Scroll Sync**: Clicking elements in the preview scrolls to the corresponding source code.

### 2. Real-time Collaboration
Work with others on the same document simultaneously.
- **Shared Cursors**: See where others are editing in real-time.
- **Global Chat**: Communicate via the built-in encrypted chat system.
- **Conflict-Free**: File-scoped edits ensure data integrity efficiently.
- **Identity**: Set a custom session nickname in the configuration tab.

### 3. Visual Configuration
- **Theme Selector**: Instantly switch between 15+ professionally designed color schemes.
- **Module Settings**: Configure module options (e.g., Block Design, Plotting Defaults) using a graphical interface.
- **Validation**: All inputs are validated against the module's `blueprint.json` schema.

### 4. Project Management
- **File Tree**: Navigate and manage your project structure visually.
- **Build Grid**: A powerful visual interface for selecting specific chapters and pages to compile.
- **Metadata Editor**: Edit project details (Title, Author) without touching JSON files.

---

## Remote Collaboration (ngrok)

To collaborate with users over the internet (outside your LAN), we recommend using **ngrok**. This provides a secure, encrypted tunnel to your local instance.

1.  **Start the GUI**:
    ```bash
    python3 noteworthy.py --gui
    ```
2.  **Expose Port**: In a separate terminal, run:
    ```bash
    ngrok http 8000
    ```
3.  **Share**: Copy the provided **HTTPS** URL (e.g., `https://xxxx-xx.ngrok-free.app`) and verify the connection.
    > **Note**: Your collaborators will access the **exact same session** as you.

