// ============================================================
// FILE TREE MODULE
// Handles the sidebar file tree, file operations (CRUD, rename, move)
// ============================================================

(function () {
    const FileTreeMixin = {
        refreshTree: async function () {
            const res = await fetch('/api/tree');
            const data = await res.json();
            this.state.treeData = data;

            const container = document.getElementById('file-tree');
            container.innerHTML = '';

            if (!this.state.expandedFolders) {
                this.state.expandedFolders = {};
            }

            container.appendChild(this.renderTreeItems(data.items, 0));

            if (window.lucide) lucide.createIcons();
        },

        toggleFolder: function (path) {
            if (!this.state.expandedFolders) this.state.expandedFolders = {};
            this.state.expandedFolders[path] = this.state.expandedFolders[path] === false ? true : false;
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
            const bottomFolders = ['assets', 'templates', 'config'];
            const sortedItems = [...items].sort((a, b) => {
                const aIsBottom = bottomFolders.includes(a.name);
                const bIsBottom = bottomFolders.includes(b.name);
                if (aIsBottom && !bIsBottom) return 1;
                if (!aIsBottom && bIsBottom) return -1;
                if (a.name === 'content' && b.name !== 'content') return -1;
                if (a.name !== 'content' && b.name === 'content') return 1;
                return a.name.localeCompare(b.name);
            });

            sortedItems.forEach(item => {
                const el = document.createElement('div');
                el.className = 'tree-item';
                el.style.paddingLeft = `${depth * 16 + 12}px`;
                el.dataset.path = item.path;

                // Top-level roots (content/config/templates) are pinned by the
                // server, so they can be drop targets but not drag sources.
                if (depth > 0) {
                    el.draggable = true;
                    el.addEventListener('dragstart', (e) => this.onTreeDragStart(e, item));
                    el.addEventListener('dragend', () => this.onTreeDragEnd());
                }
                el.addEventListener('dragover', (e) => this.onTreeDragOver(e, item));
                el.addEventListener('dragleave', (e) => this.onTreeDragLeave(e));
                el.addEventListener('drop', (e) => this.onTreeDrop(e, item));

                if (item.is_dir) {
                    const isBottomFolder = bottomFolders.includes(item.name);
                    const defaultExpanded = !isBottomFolder;
                    const isExpanded = this.state.expandedFolders?.[item.path] ?? defaultExpanded;

                    el.innerHTML = `<i data-lucide="${isExpanded ? 'chevron-down' : 'chevron-right'}" class="tree-arrow"></i><i data-lucide="folder" class="tree-folder"></i> <span class="tree-file-name">${item.name}</span>`;
                    el.onclick = (e) => { e.stopPropagation(); this.toggleFolder(item.path); };
                    if (depth > 0) {
                        el.oncontextmenu = (e) => this.showFileContextMenu(e, item.path, true);
                    }
                    div.appendChild(el);

                    if (item.children && isExpanded) {
                        const childDiv = this.renderTreeItems(item.children, depth + 1);
                        childDiv.dataset.folder = item.path;
                        div.appendChild(childDiv);
                    }
                } else {
                    const icon = this.getFileIcon(item.name);
                    if (icon.type === 'svg') {
                        el.innerHTML = `${icon.value} <span class="tree-file-name">${item.name}</span>`;
                    } else {
                        el.innerHTML = `<i data-lucide="${icon.value}" class="tree-file" style="fill: none; stroke-width: 2px;"></i> <span class="tree-file-name">${item.name}</span>`;
                    }
                    el.onclick = () => this.openFile(item.path, el);
                    el.oncontextmenu = (e) => this.showFileContextMenu(e, item.path, false);
                    div.appendChild(el);
                }
            });
            return div;
        },

        // --- Drag & drop moves ---

        _treeDropTargetDir: function (item) {
            // A folder receives drops into itself; a file row stands in for
            // its parent folder ("drop next to this file").
            if (item.is_dir) return item.path;
            const idx = item.path.lastIndexOf('/');
            return idx === -1 ? null : item.path.substring(0, idx);
        },

        _canDropInto: function (destDir) {
            const drag = this.state.treeDragItem;
            if (!drag || !destDir || destDir === drag.path) return false;
            // A folder can't move into its own subtree.
            if (drag.isDir && (destDir + '/').startsWith(drag.path + '/')) return false;
            // Dropping back into the current parent is a no-op.
            if (destDir === drag.path.substring(0, drag.path.lastIndexOf('/'))) return false;
            return true;
        },

        _canDropOn: function (item) {
            return this._canDropInto(this._treeDropTargetDir(item));
        },

        onTreeDragStart: function (e, item) {
            this.state.treeDragItem = { path: item.path, isDir: item.is_dir };
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', item.path);
            e.currentTarget.classList.add('dragging');
        },

        onTreeDragEnd: function () {
            this.state.treeDragItem = null;
            document.querySelectorAll('.tree-item.dragging, .tree-item.drop-target')
                .forEach(el => el.classList.remove('dragging', 'drop-target'));
        },

        onTreeDragOver: function (e, item) {
            if (!this._canDropOn(item)) return;
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            e.currentTarget.classList.add('drop-target');
        },

        onTreeDragLeave: function (e) {
            if (!e.currentTarget.contains(e.relatedTarget)) {
                e.currentTarget.classList.remove('drop-target');
            }
        },

        onTreeDrop: async function (e, item) {
            if (!this._canDropOn(item)) return;
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.remove('drop-target');
            const drag = this.state.treeDragItem;
            this.state.treeDragItem = null;
            const destDir = this._treeDropTargetDir(item);
            if (!this.state.expandedFolders) this.state.expandedFolders = {};
            this.state.expandedFolders[destDir] = true;
            await this._moveTreeItem(drag.path, `${destDir}/${drag.path.split('/').pop()}`);
        },

        _moveTreeItem: async function (path, newPath) {
            try {
                const res = await fetch('/api/rename', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, newName: newPath.split('/').pop(), newPath })
                });
                const result = await res.json();
                if (result.success) {
                    this.showSaveStatus('Moved');
                    await this._handlePathMoved(path, result.newPath || newPath);
                } else {
                    this.showSaveStatus(result.error || 'Move Failed');
                }
            } catch (e) {
                console.error('Move error:', e);
                this.showSaveStatus('Move Error');
            }
        },

        _handlePathMoved: async function (oldPath, newPath) {
            // Refresh the tree, and if the open file was the moved item (or
            // lived inside a moved folder), re-open it at its new path so the
            // editor reconnects to the Yjs room under the new room name —
            // a provider left on the old name would recreate the old path on
            // its next reconnect.
            const active = this.state.activeFile;
            let updated = null;
            if (active === oldPath) updated = newPath;
            else if (active && active.startsWith(oldPath + '/')) updated = newPath + active.substring(oldPath.length);
            await this.refreshTree();
            if (updated) {
                this.state.activeFile = null;
                const el = document.querySelector(`.tree-item[data-path="${updated}"]`);
                this.openFile(updated, el || undefined);
            }
        },

        showFileContextMenu: function (e, path, isDir) {
            e.preventDefault();
            e.stopPropagation();
            this.state.contextMenuFile = path;
            this.state.contextMenuIsDir = !!isDir;
            const menu = document.getElementById('file-context-menu');
            menu.style.left = `${e.clientX}px`;
            menu.style.top = `${e.clientY}px`;
            menu.classList.add('visible');
            if (window.lucide) lucide.createIcons();
            const closeMenu = () => {
                menu.classList.remove('visible');
                document.removeEventListener('click', closeMenu);
            };
            setTimeout(() => document.addEventListener('click', closeMenu), 0);
        },

        uploadFiles: function () {
            document.getElementById('file-upload-input').click();
        },

        handleFileUpload: async function (event) {
            const files = event.target.files;
            if (!files.length) return;

            const formData = new FormData();
            for (const file of files) formData.append('files', file);

            const dir = this.state.activeFile
                ? this.state.activeFile.substring(0, this.state.activeFile.lastIndexOf('/'))
                : '';
            formData.append('directory', dir);

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                this.showSaveStatus(res.ok ? 'Files Uploaded' : 'Upload Failed');
                if (res.ok) this.refreshTree();
            } catch (e) {
                console.error('Upload error:', e);
                this.showSaveStatus('Upload Error');
            }
            event.target.value = '';
        },

        toggleNewDropdown: function () {
            const menu = document.getElementById('new-dropdown-menu');
            if (menu) {
                menu.classList.toggle('visible');
                if (menu.classList.contains('visible')) {
                    setTimeout(() => {
                        const closeHandler = (e) => {
                            if (!e.target.closest('#new-dropdown')) {
                                menu.classList.remove('visible');
                                document.removeEventListener('click', closeHandler);
                            }
                        };
                        document.addEventListener('click', closeHandler);
                    }, 10);
                }
            }
            if (window.lucide) lucide.createIcons();
        },

        createNewFile: async function () {
            const menu = document.getElementById('new-dropdown-menu');
            if (menu) menu.classList.remove('visible');

            let parentDir = 'content';
            if (this.state.activeFile) {
                const parts = this.state.activeFile.split('/');
                parts.pop();
                if (parts.length > 0) parentDir = parts.join('/');
            }

            const filename = prompt('Enter filename:', 'new-file.typ');
            if (!filename) return;
            const path = `${parentDir}/${filename}`;

            try {
                const res = await fetch('/api/file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, content: '' })
                });
                if (res.ok) {
                    this.showSaveStatus('File Created');
                    await this.refreshTree();
                    this.openFile(path);
                } else {
                    this.showSaveStatus('Create Failed');
                }
            } catch (e) {
                console.error('Create file error:', e);
                this.showSaveStatus('Create Error');
            }
        },

        createNewFolder: async function () {
            const menu = document.getElementById('new-dropdown-menu');
            if (menu) menu.classList.remove('visible');

            let parentDir = 'content';
            if (this.state.activeFile) {
                const parts = this.state.activeFile.split('/');
                parts.pop();
                if (parts.length > 0) parentDir = parts.join('/');
            }

            const foldername = prompt('Enter folder name:', 'new-folder');
            if (!foldername) return;
            const path = `${parentDir}/${foldername}/.gitkeep`;

            try {
                const res = await fetch('/api/file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, content: '' })
                });
                this.showSaveStatus(res.ok ? 'Folder Created' : 'Create Failed');
                if (res.ok) await this.refreshTree();
            } catch (e) {
                console.error('Create folder error:', e);
                this.showSaveStatus('Create Error');
            }
        },

        renameFile: function () {
            const path = this.state.contextMenuFile;
            if (!path) return;

            const fileItem = document.querySelector(`.tree-item[data-path="${path}"]`);
            if (!fileItem) return;

            const filename = path.split('/').pop();
            const nameSpan = fileItem.querySelector('.tree-file-name') || fileItem.querySelector('span:last-child');
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'inline-rename-input';
            input.value = filename;
            input.style.cssText = `
                background: var(--glass-bg); border: 1px solid var(--accent);
                border-radius: 4px; color: var(--text-primary); font-size: 13px;
                padding: 2px 6px; width: 100%; outline: none;
            `;

            nameSpan.style.display = 'none';
            fileItem.appendChild(input);
            // Keep clicks inside the input from bubbling to the row, which
            // would toggle/open the item and re-render the tree mid-rename.
            input.addEventListener('click', (e) => e.stopPropagation());
            input.focus();
            input.select();

            const finishRename = async (save) => {
                const newName = input.value.trim();
                input.remove();
                nameSpan.style.display = '';

                if (save && newName && newName !== filename) {
                    try {
                        const res = await fetch('/api/rename', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ path, newName })
                        });
                        const result = await res.json();
                        if (result.success) {
                            this.showSaveStatus('Renamed');
                            await this._handlePathMoved(path, result.newPath);
                        } else {
                            this.showSaveStatus(result.error || 'Rename Failed');
                        }
                    } catch (e) {
                        console.error('Rename error:', e);
                        this.showSaveStatus('Rename Error');
                    }
                }
            };

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') { e.preventDefault(); finishRename(true); }
                else if (e.key === 'Escape') { e.preventDefault(); finishRename(false); }
            });
            input.addEventListener('blur', () => finishRename(true));
        },

        moveFile: async function () {
            const path = this.state.contextMenuFile;
            if (!path) return;
            const filename = path.split('/').pop();
            const newPath = prompt(`Move "${filename}" to new path:`, path);
            if (!newPath || newPath === path) return;
            await this._moveTreeItem(path, newPath);
        },

        deleteFile: async function () {
            const path = this.state.contextMenuFile;
            if (!path) return;
            const isDir = !!this.state.contextMenuIsDir;
            const message = isDir
                ? `Delete folder "${path}" and everything inside it?`
                : `Delete "${path}"?`;
            if (!confirm(message)) return;

            try {
                const res = await fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path })
                });
                const result = await res.json();
                if (res.ok && result.success !== false) {
                    this.showSaveStatus(isDir ? 'Folder Deleted' : 'File Deleted');
                    this.refreshTree();
                    const active = this.state.activeFile;
                    if (active && (active === path || active.startsWith(path + '/'))) {
                        this._closeActiveEditor();
                    }
                } else {
                    this.showSaveStatus(result.error || 'Delete Failed');
                }
            } catch (e) {
                console.error('Delete error:', e);
                this.showSaveStatus('Delete Error');
            }
        },

        _closeActiveEditor: function () {
            // Tear down the Yjs pipeline before clearing the editor. A binding
            // or provider left alive would reconnect after the server closes
            // the room and push the old document back, resurrecting the
            // deleted file.
            if (this.state.yjsBinding) { this.state.yjsBinding.destroy(); this.state.yjsBinding = null; }
            if (this.state.yjsProvider) { this.state.yjsProvider.destroy(); this.state.yjsProvider = null; }
            if (this.state.ydoc) { this.state.ydoc.destroy(); this.state.ydoc = null; }
            this.state.activeFile = null;
            document.getElementById('active-filename').textContent = 'Select a file';
            if (this.state.editor) {
                this.state.editor.setValue('');
                this.state.editor.updateOptions({ readOnly: true });
            }
        },
    };

    window._fileTreeMixin = FileTreeMixin;
})();
