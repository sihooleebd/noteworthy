import os
import sys
import json
import subprocess
import shutil
import argparse
import zipfile
import curses
from pathlib import Path

# Configuration
BUILD_DIR = Path("build")
OUTPUT_FILE = Path("output.pdf")
RENDERER_FILE = "templates/parser.typ"

def check_dependencies():
    if shutil.which("typst") is None:
        print("Error: 'typst' executable not found in PATH.")
        sys.exit(1)
    if shutil.which("pdfinfo") is None:
        print("Error: 'pdfinfo' executable not found in PATH.")
        print("Install with: brew install poppler")
        sys.exit(1)

def get_pdf_page_count(pdf_path):
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
        return 0
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting page count for {pdf_path}: {e}")
        return 0


def extract_hierarchy():
    print("Extracting document hierarchy...")
    
    temp_file = Path("extract_hierarchy.typ")
    temp_file.write_text('#import "config.typ": hierarchy\n#metadata(hierarchy) <hierarchy>')
    
    try:
        result = subprocess.run(
            ["typst", "query", str(temp_file), "<hierarchy>"],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return data[0]["value"]
    except subprocess.CalledProcessError as e:
        print(f"Error extracting hierarchy: {e.stderr}")
        sys.exit(1)
    finally:
        if temp_file.exists():
            temp_file.unlink()

def compile_target(target, output_path, page_offset=None, page_map=None, quiet=True, extra_flags=None, keyboard_check_callback=None):
    cmd = [
        "typst", "compile", 
        RENDERER_FILE, 
        str(output_path),
        "--root", ".",
        "--input", f"target={target}"
    ]
    
    if page_offset is not None:
        cmd.extend(["--input", f"page-offset={page_offset}"])
    
    if page_map is not None:
        # Pass JSON string without escaping quotes since we're using single quotes in shell
        page_map_json_str = json.dumps(page_map)
        cmd.extend(["--input", f"page-map={page_map_json_str}"])
    
    # Add extra flags if provided
    if extra_flags:
        cmd.extend(extra_flags)
    
    try:
        # Use Popen for non-blocking execution
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Poll the process while checking for keyboard input
        import time
        while process.poll() is None:
            if keyboard_check_callback:
                keyboard_check_callback()
            time.sleep(0.05)  # Check every 50ms
        
        # Get the output after process completes
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, output=stdout, stderr=stderr)
        
        return stderr if stderr else ""
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(f"Error compiling {target}:")
            print(e.stderr)
        raise

def merge_pdfs_with_command(pdf_files, output_path):
    # Filter out non-existent files
    existing_files = [str(pdf) for pdf in pdf_files if pdf.exists()]
    
    if not existing_files:
        print("No PDF files to merge!")
        return
    
    print(f"Merging {len(existing_files)} files into {output_path}...")
    
    # Try pdfunite first (from poppler-utils)
    if shutil.which("pdfunite"):
        cmd = ["pdfunite"] + existing_files + [str(output_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Successfully merged PDFs using pdfunite")
            return
        except subprocess.CalledProcessError as e:
            print(f"pdfunite failed: {e.stderr.decode()}")
    
    # Try ghostscript as fallback
    if shutil.which("gs"):
        cmd = [
            "gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
            f"-sOutputFile={output_path}"
        ] + existing_files
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Successfully merged PDFs using ghostscript")
            return
        except subprocess.CalledProcessError as e:
            print(f"ghostscript failed: {e.stderr.decode()}")
    
    # If both fail, print warning
    print("Warning: No PDF merge tool found (tried pdfunite and gs)")
    print("Individual PDFs are available in the build/ directory")
    print("To install a merge tool:")
    print("  - macOS: brew install poppler")
    print("  - Linux: apt-get install poppler-utils or ghostscript")

def zip_build_directory(build_dir, output_file="build_pdfs.zip"):
    print(f"Zipping build directory to {output_file}...")
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(build_dir.parent)
                zipf.write(file_path, arcname)
    print(f"Created {output_file}")

def create_pdf_metadata(hierarchy, page_map, output_file="bookmarks.txt"):
    print(f"Creating PDF bookmarks file: {output_file}...")
    
    bookmarks = []
    
    # Add cover and preface
    if "cover" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Cover")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['cover']}")
    
    if "preface" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Preface")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['preface']}")
    
    if "outline" in page_map:
        bookmarks.append(f"BookmarkBegin")
        bookmarks.append(f"BookmarkTitle: Table of Contents")
        bookmarks.append(f"BookmarkLevel: 1")
        bookmarks.append(f"BookmarkPageNumber: {page_map['outline']}")
    
    # Add chapters and pages
    for chapter in hierarchy:
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        # Chapter bookmark
        if f"chapter-{chapter_id}" in page_map:
            bookmarks.append(f"BookmarkBegin")
            bookmarks.append(f"BookmarkTitle: {chapter['title']}")
            bookmarks.append(f"BookmarkLevel: 1")
            bookmarks.append(f"BookmarkPageNumber: {page_map[f'chapter-{chapter_id}']}")
        
        # Page bookmarks (as sub-items of chapter)
        for page in chapter["pages"]:
            page_id = page["id"]
            if page_id in page_map:
                bookmarks.append(f"BookmarkBegin")
                bookmarks.append(f"BookmarkTitle: {page['title']}")
                bookmarks.append(f"BookmarkLevel: 2")
                bookmarks.append(f"BookmarkPageNumber: {page_map[page_id]}")
    
    # Write bookmarks file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bookmarks))
    
    print(f"✓ Created bookmarks file with {len(bookmarks)//4} entries")
    return output_file

def apply_pdf_metadata(pdf_path, bookmarks_file, title="Noteworthy Framework", author=""):
    temp_pdf = BUILD_DIR / "temp_with_metadata.pdf"
    
    # Try pdftk first (best quality)
    if shutil.which("pdftk"):
        try:
            # Update metadata
            info_file = BUILD_DIR / "pdf_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"InfoBegin\n")
                f.write(f"InfoKey: Title\n")
                f.write(f"InfoValue: {title}\n")
                if author:
                    f.write(f"InfoKey: Author\n")
                    f.write(f"InfoValue: {author}\n")
            
            # First add metadata
            subprocess.run([
                "pdftk", str(pdf_path), "update_info", str(info_file), 
                "output", str(temp_pdf)
            ], check=True, capture_output=True)
            
            # Then add bookmarks
            temp_pdf2 = BUILD_DIR / "temp_with_bookmarks.pdf"
            subprocess.run([
                "pdftk", str(temp_pdf), "update_info", str(bookmarks_file),
                "output", str(temp_pdf2)
            ], check=True, capture_output=True)
            
            shutil.move(temp_pdf2, pdf_path)
            print("✓ Applied PDF metadata and bookmarks using pdftk")
            return True
        except subprocess.CalledProcessError as e:
            print(f"pdftk failed: {e.stderr.decode()}")
    
    # Fallback: Try ghostscript with pdfmark
    if shutil.which("gs"):
        try:
            # Convert bookmarks to pdfmark format
            pdfmark_file = BUILD_DIR / "bookmarks.pdfmark"
            with open(bookmarks_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            pdfmarks = []
            pdfmarks.append("[ /Title (%s) /Author (%s) /DOCINFO pdfmark" % (title, author))
            
            i = 0
            while i < len(lines):
                if lines[i].strip() == "BookmarkBegin":
                    title_line = lines[i+1].strip()
                    level_line = lines[i+2].strip()
                    page_line = lines[i+3].strip()
                    
                    bm_title = title_line.split(": ", 1)[1] if ": " in title_line else ""
                    bm_level = level_line.split(": ", 1)[1] if ": " in level_line else "1"
                    bm_page = page_line.split(": ", 1)[1] if ": " in page_line else "1"
                    
                    pdfmarks.append(f"[ /Title ({bm_title}) /Page {bm_page} /Count 0 /OUT pdfmark")
                    i += 4
                else:
                    i += 1
            
            with open(pdfmark_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(pdfmarks))
            
            # Apply with ghostscript
            subprocess.run([
                "gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
                f"-sOutputFile={temp_pdf}",
                str(pdf_path),
                str(pdfmark_file)
            ], check=True, capture_output=True)
            
            shutil.move(temp_pdf, pdf_path)
            print("✓ Applied PDF metadata using ghostscript")
            return True
        except subprocess.CalledProcessError as e:
            print(f"ghostscript metadata failed: {e.stderr.decode()}")
    
    print("⚠ Warning: Could not apply PDF metadata (pdftk or gs required)")
    print("  Install with: brew install pdftk-java")
    return False



class BuildMenu:
    def __init__(self, stdscr, hierarchy):
        self.stdscr = stdscr
        self.hierarchy = hierarchy
        self.selected = [True] * len(hierarchy)  # All chapters selected by default
        self.cursor = 0
        self.debug_mode = False
        self.include_frontmatter = True
        self.leave_individual = False
        self.typst_flags = []  # Custom typst compiler flags
        
        # Setup curses
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # Title
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Selected
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Cursor
        curses.init_pair(4, curses.COLOR_WHITE, -1)    # Normal
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Option
        curses.init_pair(6, curses.COLOR_RED, -1)      # Disabled
        
        self.stdscr.clear()
        self.height, self.width = stdscr.getmaxyx()
    
    def draw_box(self, y, x, h, w, title=""):
        self.stdscr.addstr(y, x, "╔" + "═" * (w - 2) + "╗")
        for i in range(1, h - 1):
            self.stdscr.addstr(y + i, x, "║" + " " * (w - 2) + "║")
        self.stdscr.addstr(y + h - 1, x, "╚" + "═" * (w - 2) + "╝")
        if title:
            self.stdscr.addstr(y, x + 2, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
    
    def safe_addstr(self, y, x, text, attr=0):
        try:
            if y < self.height and x < self.width:
                self.stdscr.addstr(y, x, text[:self.width - x - 1], attr)
        except curses.error:
            pass
    
    def refresh(self):
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # ASCII Logo
        logo = [
            "         ,--. ",
            "       ,--.'| ",
            "   ,--,:  : | ",
            ",`--.'`|  ' : ",
            "|   :  :  | | ",
            ":   |   \\ | : ",
            "|   : '  '; | ",
            "'   ' ;.    ; ",
            "|   | | \\   | ",
            "'   : |  ; .' ",
            "|   | '`--'   ",
            "'   : |       ",
            ";   |.'       ",
            "'---'         ",
        ]
        
        logo_x = (self.width - 14) // 2
        for i, line in enumerate(logo):
            self.safe_addstr(i, logo_x, line, curses.color_pair(1) | curses.A_BOLD)
        
        # Title
        title = "NOTEWORTHY"
        self.safe_addstr(len(logo) + 1, (self.width - len(title)) // 2, title, 
                        curses.color_pair(1) | curses.A_BOLD)
        
        box_width = min(60, self.width - 4)
        box_x = (self.width - box_width) // 2
        start_y = len(logo) + 3
        
        # Options box
        self.draw_box(start_y, box_x, 7, box_width, "Options")
        
        # Debug mode toggle
        debug_status = "[ON] " if self.debug_mode else "[OFF]"
        debug_color = curses.color_pair(2) if self.debug_mode else curses.color_pair(6)
        self.safe_addstr(start_y + 1, box_x + 2, "Debug Mode:   ", curses.color_pair(4))
        self.safe_addstr(start_y + 1, box_x + 16, debug_status, debug_color | curses.A_BOLD)
        self.safe_addstr(start_y + 1, box_x + 22, "(d)", curses.color_pair(4) | curses.A_DIM)
        
        # Frontmatter toggle
        fm_status = "[ON] " if self.include_frontmatter else "[OFF]"
        fm_color = curses.color_pair(2) if self.include_frontmatter else curses.color_pair(6)
        self.safe_addstr(start_y + 2, box_x + 2, "Frontmatter:  ", curses.color_pair(4))
        self.safe_addstr(start_y + 2, box_x + 16, fm_status, fm_color | curses.A_BOLD)
        self.safe_addstr(start_y + 2, box_x + 22, "(f)", curses.color_pair(4) | curses.A_DIM)
        
        # Leave Individual toggle
        li_status = "[ON] " if self.leave_individual else "[OFF]"
        li_color = curses.color_pair(2) if self.leave_individual else curses.color_pair(6)
        self.safe_addstr(start_y + 3, box_x + 2, "Leave PDFs:   ", curses.color_pair(4))
        self.safe_addstr(start_y + 3, box_x + 16, li_status, li_color | curses.A_BOLD)
        self.safe_addstr(start_y + 3, box_x + 22, "(l)", curses.color_pair(4) | curses.A_DIM)
        
        # Typst Flags configuration
        flags_display = " ".join(self.typst_flags) if self.typst_flags else "(none)"
        self.safe_addstr(start_y + 4, box_x + 2, "Typst Flags:  ", curses.color_pair(4))
        self.safe_addstr(start_y + 4, box_x + 16, flags_display[:box_width - 30], 
                        curses.color_pair(5) if self.typst_flags else curses.color_pair(4) | curses.A_DIM)
        self.safe_addstr(start_y + 5, box_x + 16, "(c) to configure", curses.color_pair(4) | curses.A_DIM)
        
        # Chapter selection box
        chapter_box_y = start_y + 8
        chapter_box_height = min(len(self.hierarchy) + 2, self.height - chapter_box_y - 3)
        if chapter_box_height > 2:
            self.draw_box(chapter_box_y, box_x, chapter_box_height, box_width, "Select Chapters")
        
        # Chapter list
        for i, chapter in enumerate(self.hierarchy):
            if i >= chapter_box_height - 2:
                break
            
            first_page = chapter["pages"][0]
            chapter_id = first_page["id"][:2]
            
            # Checkbox
            checkbox = "[✓]" if self.selected[i] else "[ ]"
            checkbox_color = curses.color_pair(2) if self.selected[i] else curses.color_pair(4)
            
            # Cursor indicator
            row_y = chapter_box_y + 1 + i
            if i == self.cursor:
                self.safe_addstr(row_y, box_x + 2, "▶ ", curses.color_pair(3) | curses.A_BOLD)
                attr = curses.A_BOLD
            else:
                self.safe_addstr(row_y, box_x + 2, "  ", curses.color_pair(4))
                attr = 0
            
            self.safe_addstr(row_y, box_x + 4, checkbox, checkbox_color | attr)
            
            chapter_text = f" Chapter {chapter_id}: {chapter['title']}"[:box_width - 12]
            self.safe_addstr(row_y, box_x + 7, chapter_text, curses.color_pair(4) | attr)
        
        # Footer with controls
        footer_y = chapter_box_y + chapter_box_height + 1
        controls = "↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  q:Quit"
        self.safe_addstr(footer_y, (self.width - len(controls)) // 2, controls,
                        curses.color_pair(4) | curses.A_DIM)
        
        self.stdscr.refresh()
    
    def configure_typst_flags(self):
        """Popup dialog to configure typst flags"""
        curses.echo()
        curses.curs_set(1)
        
        dialog_height = 12
        dialog_width = min(70, self.width - 4)
        dialog_y = (self.height - dialog_height) // 2
        dialog_x = (self.width - dialog_width) // 2
        
        # Create a new window for the dialog
        dialog = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        dialog.box()
        dialog.addstr(0, 2, " Configure Typst Flags ", curses.color_pair(1) | curses.A_BOLD)
        
        # Show current flags
        current = " ".join(self.typst_flags) if self.typst_flags else "(none)"
        dialog.addstr(2, 2, "Current: " + current[:dialog_width - 12])
        
        # Show common presets
        dialog.addstr(4, 2, "Common presets:", curses.color_pair(5))
        dialog.addstr(5, 2, "  1. --font-path /path/to/fonts")
        dialog.addstr(6, 2, "  2. --ppi 144")
        dialog.addstr(7, 2, "  3. Clear all flags")
        
        dialog.addstr(9, 2, "Enter flags (or preset number): ", curses.color_pair(4))
        dialog.refresh()
        
        # Get input
        curses.curs_set(1)
        input_str = dialog.getstr(9, 35, dialog_width - 37).decode('utf-8').strip()
        
        # Process input
        if input_str == "1":
            dialog.addstr(10, 2, "Enter font path: ")
            dialog.refresh()
            font_path = dialog.getstr(10, 19, dialog_width - 21).decode('utf-8').strip()
            if font_path:
                self.typst_flags = ["--font-path", font_path]
        elif input_str == "2":
            self.typst_flags = ["--ppi", "144"]
        elif input_str == "3":
            self.typst_flags = []
        elif input_str:
            # Parse custom flags
            self.typst_flags = input_str.split()
        
        curses.noecho()
        curses.curs_set(0)
        self.refresh()
    
    def run(self):
        self.refresh()
        
        while True:
            key = self.stdscr.getch()
            
            if key == ord('q'):
                return None  # Quit
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                # Return selected chapters
                return {
                    'chapters': [i for i, sel in enumerate(self.selected) if sel],
                    'debug': self.debug_mode,
                    'frontmatter': self.include_frontmatter,
                    'leave_individual': self.leave_individual,
                    'typst_flags': self.typst_flags,
                }
            elif key == curses.KEY_UP or key == ord('k'):
                self.cursor = max(0, self.cursor - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                self.cursor = min(len(self.hierarchy) - 1, self.cursor + 1)
            elif key == ord(' '):
                self.selected[self.cursor] = not self.selected[self.cursor]
            elif key == ord('a'):
                self.selected = [True] * len(self.hierarchy)
            elif key == ord('n'):
                self.selected = [False] * len(self.hierarchy)
            elif key == ord('d'):
                self.debug_mode = not self.debug_mode
            elif key == ord('f'):
                self.include_frontmatter = not self.include_frontmatter
            elif key == ord('l'):
                self.leave_individual = not self.leave_individual
            elif key == ord('c'):
                self.configure_typst_flags()
            
            self.refresh()


class BuildUI:
    def __init__(self, stdscr, debug_mode=False):
        self.stdscr = stdscr
        self.logs = []
        self.typst_logs = []  # Raw typst compiler output
        self.current_task = ""
        self.progress = 0
        self.total = 0
        self.phase = ""
        self.debug_mode = debug_mode
        self.view_mode = "normal"  # "normal" or "typst"
        self.typst_scroll_offset = 0  # For scrolling through typst logs
        
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # Title
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Success
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Progress
        curses.init_pair(4, curses.COLOR_WHITE, -1)    # Normal
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Phase
        curses.init_pair(6, curses.COLOR_RED, -1)      # Error
        curses.init_pair(7, curses.COLOR_YELLOW, -1)   # Warning
        
        self.stdscr.clear()
        self.height, self.width = stdscr.getmaxyx()
    
    def draw_box(self, y, x, h, w, title=""):
        # Draw box borders
        self.stdscr.addstr(y, x, "╔" + "═" * (w - 2) + "╗")
        for i in range(1, h - 1):
            self.stdscr.addstr(y + i, x, "║" + " " * (w - 2) + "║")
        self.stdscr.addstr(y + h - 1, x, "╚" + "═" * (w - 2) + "╝")
        
        if title:
            self.stdscr.addstr(y, x + 2, f" {title} ", curses.color_pair(1) | curses.A_BOLD)
    
    def draw_progress_bar(self, y, x, width, progress, total):
        if total == 0:
            return
        
        bar_width = width - 2
        filled = int(bar_width * progress / total)
        empty = bar_width - filled
        
        bar = "█" * filled + "░" * empty
        percent = int(100 * progress / total)
        
        self.stdscr.addstr(y, x, bar, curses.color_pair(3))
        self.stdscr.addstr(y, x + bar_width + 2, f"{percent:3d}%", curses.color_pair(3) | curses.A_BOLD)
    
    def log(self, message, success=False):
        self.logs.append((message, success))
        if len(self.logs) > 20:
            self.logs.pop(0)
        self.refresh()
    
    def debug(self, message):
        if self.debug_mode:
            self.logs.append((f"[DEBUG] {message}", False))
            if len(self.logs) > 20:
                self.logs.pop(0)
            self.refresh()
    
    def log_typst(self, output):
        """Log raw typst compiler output"""
        if output:
            for line in output.split('\n'):
                if line.strip():
                    self.typst_logs.append(line)
            # Keep last 100 lines
            if len(self.typst_logs) > 100:
                self.typst_logs = self.typst_logs[-100:]
    
    def set_phase(self, phase):
        self.phase = phase
        self.refresh()
    
    def set_task(self, task):
        self.current_task = task
        self.refresh()
    
    def set_progress(self, progress, total):
        self.progress = progress
        self.total = total
        self.refresh()
    
    
    def refresh(self):
        # Check for keyboard input first (non-blocking)
        try:
            key = self.stdscr.getch()
            if key == ord('v'):
                self.view_mode = "typst" if self.view_mode == "normal" else "normal"
                self.typst_scroll_offset = 0  # Reset scroll when switching views
            elif self.view_mode == "typst":
                # Arrow keys and vim keys for scrolling
                if key == curses.KEY_UP or key == ord('k'):
                    self.typst_scroll_offset = max(0, self.typst_scroll_offset - 1)
                    # Flush keyboard buffer to stop immediately when key released
                    curses.flushinp()
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.typst_scroll_offset = min(len(self.typst_logs) - 1, self.typst_scroll_offset + 1)
                    # Flush keyboard buffer to stop immediately when key released
                    curses.flushinp()
        except:
            pass
        
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # Title
        title = "NOTEWORTHY BUILD SYSTEM"
        if self.debug_mode:
            title += " [DEBUG]"
        self.stdscr.addstr(1, (self.width - len(title)) // 2, title, 
                          curses.color_pair(1) | curses.A_BOLD)
        
        # Phase box
        box_width = min(60, self.width - 4)
        box_x = (self.width - box_width) // 2
        
        self.draw_box(3, box_x, 5, box_width, "Progress")
        
        # Phase label
        if self.phase:
            phase_text = self.phase[:box_width - 6]
            self.stdscr.addstr(4, box_x + 2, phase_text, curses.color_pair(5))
        
        # Current task
        if self.current_task:
            task_text = self.current_task[:box_width - 6]
            self.stdscr.addstr(5, box_x + 2, f"→ {task_text}", curses.color_pair(4))
        
        # Progress bar
        self.draw_progress_bar(6, box_x + 2, box_width - 12, self.progress, self.total)
        
        # Log box
        log_height = min(15, self.height - 12)
        
        # Determine which logs to show based on view_mode
        if self.view_mode == "typst" and self.typst_logs:
            box_title = "Typst Compiler Output (↑↓ or jk to scroll)"
            
            # Calculate visible range with scroll offset
            max_offset = max(0, len(self.typst_logs) - (log_height - 2))
            self.typst_scroll_offset = min(self.typst_scroll_offset, max_offset)
            
            start_idx = self.typst_scroll_offset
            end_idx = start_idx + (log_height - 2)
            visible_logs = self.typst_logs[start_idx:end_idx]
            
            # Create items with syntax highlighting info
            log_items = []
            for msg in visible_logs:
                # Determine color based on content
                if 'error:' in msg.lower():
                    log_items.append((msg, False, 6))  # Red for errors
                elif 'warning:' in msg.lower():
                    log_items.append((msg, False, 7))  # Yellow for warnings
                elif 'hint:' in msg.lower() or '= hint:' in msg:
                    log_items.append((msg, False, 1))  # Cyan for hints
                elif msg.strip().startswith('┌─') or msg.strip().startswith('│') or '──' in msg:
                    log_items.append((msg, False, 5))  # Magenta for file paths/structure
                else:
                    log_items.append((msg, False, 4))  # White for normal
        else:
            box_title = "Build Log"
            log_items = [(msg, success, 2 if success else 4) for msg, success in self.logs[-(log_height - 2):]]
        
        self.draw_box(9, box_x, log_height, box_width, box_title)
        
        # Show logs with appropriate colors
        for i, item in enumerate(log_items):
            if len(item) == 3:
                msg, success, color_pair = item
            else:
                msg, success = item
                color_pair = 2 if success else 4
            
            prefix = "✓ " if success and self.view_mode != "typst" else "  "
            text = (prefix + msg)[:box_width - 4]
            try:
                self.stdscr.addstr(10 + i, box_x + 2, text, curses.color_pair(color_pair))
            except curses.error:
                pass
        
        # Footer - always show toggle hint
        footer = "Press Ctrl+C to cancel  |  Press 'v' to toggle view"
        try:
            self.stdscr.addstr(self.height - 1, (self.width - len(footer)) // 2, 
                              footer, curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        
        self.stdscr.refresh()


def show_menu(stdscr):
    # First extract hierarchy for the menu
    hierarchy = extract_hierarchy()
    menu = BuildMenu(stdscr, hierarchy)
    result = menu.run()
    return hierarchy, result


def run_build(stdscr, args, hierarchy, options):
    ui = BuildUI(stdscr, debug_mode=options['debug'])
    
    # Enable non-blocking keyboard input for view toggling
    stdscr.nodelay(True)
    
    def keyboard_check():
        """Callback to refresh UI during compilation (keyboard input handled in refresh)"""
        ui.refresh()
    
    ui.log("Checking dependencies...")
    ui.debug("Running dependency check...")
    check_dependencies()
    ui.log("Dependencies OK", success=True)
    
    # Clean build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    ui.log("Build directory prepared", success=True)
    
    # Filter chapters based on selection
    selected_chapters = [hierarchy[i] for i in options['chapters']]
    ui.log(f"Building {len(selected_chapters)} of {len(hierarchy)} chapters", success=True)
    
    # Calculate total compilation tasks
    total_sections = 0
    if options['frontmatter']:
        total_sections += 3  # cover + preface + outline
    for chapter in selected_chapters:
        total_sections += 1 + len(chapter["pages"])
    
    ui.set_phase("Compiling Sections")
    ui.set_progress(0, total_sections + 1)
    
    # Page tracking
    page_map = {}
    current_page = 1
    pdf_files = []
    progress = 0
    
    if options['frontmatter']:
        # 1. Cover
        ui.set_task("Cover page")
        ui.debug("Compiling cover target")
        target = "cover"
        output = BUILD_DIR / "00_cover.pdf"
        typst_output = compile_target(target, output, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
        ui.log_typst(typst_output)
        pdf_files.append(output)
        page_map["cover"] = current_page
        page_count = get_pdf_page_count(output)
        ui.debug(f"Cover: {page_count} pages")
        current_page += page_count
        progress += 1
        ui.set_progress(progress, total_sections + 1)
        ui.log("Cover page compiled", success=True)
        
        # 2. Preface
        ui.set_task("Preface")
        ui.debug("Compiling preface target")
        target = "preface"
        output = BUILD_DIR / "01_preface.pdf"
        typst_output = compile_target(target, output, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
        ui.log_typst(typst_output)
        pdf_files.append(output)
        page_map["preface"] = current_page
        page_count = get_pdf_page_count(output)
        ui.debug(f"Preface: {page_count} pages")
        current_page += page_count
        progress += 1
        ui.set_progress(progress, total_sections + 1)
        ui.log("Preface compiled", success=True)
        
        # 3. TOC placeholder
        ui.set_task("Table of Contents")
        ui.debug("Compiling outline target (placeholder)")
        target = "outline"
        output = BUILD_DIR / "02_outline.pdf"
        typst_output = compile_target(target, output, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
        ui.log_typst(typst_output)
        pdf_files.append(output)
        page_map["outline"] = current_page
        page_count = get_pdf_page_count(output)
        ui.debug(f"TOC: {page_count} pages")
        current_page += page_count
        progress += 1
        ui.set_progress(progress, total_sections + 1)
        ui.log("TOC placeholder compiled", success=True)
    
    # 4. Chapters
    for chapter in selected_chapters:
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        # Chapter Cover
        ui.set_task(f"Chapter {chapter_id}: {chapter['title']}")
        ui.debug(f"Compiling chapter-{chapter_id} at page {current_page}")
        target = f"chapter-{chapter_id}"
        output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
        page_map[f"chapter-{chapter_id}"] = current_page
        typst_output = compile_target(target, output, page_offset=current_page, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
        ui.log_typst(typst_output)
        pdf_files.append(output)
        page_count = get_pdf_page_count(output)
        ui.debug(f"Chapter {chapter_id} cover: {page_count} pages")
        current_page += page_count
        progress += 1
        ui.set_progress(progress, total_sections + 1)
        
        # Pages
        for page in chapter["pages"]:
            page_id = page["id"]
            ui.set_task(f"Section {page_id}: {page['title']}")
            ui.debug(f"Compiling {page_id} at page {current_page}")
            target = page_id
            output = BUILD_DIR / f"20_page_{page_id}.pdf"
            page_map[page_id] = current_page
            typst_output = compile_target(target, output, page_offset=current_page, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
            ui.log_typst(typst_output)
            pdf_files.append(output)
            page_count = get_pdf_page_count(output)
            ui.debug(f"Section {page_id}: {page_count} pages")
            current_page += page_count
            progress += 1
            ui.set_progress(progress, total_sections + 1)
        
        ui.log(f"Chapter {chapter_id} compiled", success=True)
    
    # 5. Regenerate TOC (only if frontmatter included)
    if options['frontmatter']:
        ui.set_task("Regenerating TOC with page numbers")
        ui.debug(f"Regenerating TOC with page_map: {len(page_map)} entries")
        target = "outline"
        output = BUILD_DIR / "02_outline.pdf"
        typst_output = compile_target(target, output, page_offset=page_map["outline"], page_map=page_map, extra_flags=options.get('typst_flags', []), keyboard_check_callback=keyboard_check)
        ui.log_typst(typst_output)
        progress += 1
        ui.set_progress(progress, total_sections + 1)
        ui.log("TOC regenerated with page numbers", success=True)
    
    # Write page map
    page_map_file = BUILD_DIR / "page_map.json"
    with open(page_map_file, 'w') as f:
        json.dump(page_map, f, indent=2)
    ui.debug(f"Page map saved to {page_map_file}")
    
    ui.log(f"Total pages: {current_page - 1}", success=True)
    
    # Merge PDFs
    ui.set_phase("Merging PDFs")
    ui.set_task(f"Merging {len(pdf_files)} files")
    ui.debug(f"PDF files to merge: {[p.name for p in pdf_files]}")
    
    existing_files = [str(pdf) for pdf in pdf_files if pdf.exists()]
    
    if shutil.which("pdfunite"):
        cmd = ["pdfunite"] + existing_files + [str(OUTPUT_FILE)]
        ui.debug(f"Running: pdfunite with {len(existing_files)} files")
        subprocess.run(cmd, check=True, capture_output=True)
        ui.log("Merged with pdfunite", success=True)
    elif shutil.which("gs"):
        cmd = ["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
               f"-sOutputFile={OUTPUT_FILE}"] + existing_files
        ui.debug("Running: ghostscript merge")
        subprocess.run(cmd, check=True, capture_output=True)
        ui.log("Merged with ghostscript", success=True)
    
    # PDF Metadata
    ui.set_phase("Adding Metadata")
    ui.set_task("Creating bookmarks")
    bookmarks_file = BUILD_DIR / "bookmarks.txt"
    create_pdf_metadata(selected_chapters, page_map, bookmarks_file)
    
    ui.set_task("Applying PDF metadata")
    title = "Noteworthy Framework"
    author = "Sihoo Lee, Lee Hojun"
    apply_pdf_metadata(OUTPUT_FILE, bookmarks_file, title, author)
    ui.log("PDF metadata applied", success=True)
    
    # Cleanup
    ui.set_phase("Cleanup")
    
    if options['leave_individual']:
        ui.set_task("Archiving individual PDFs")
        zip_build_directory(BUILD_DIR)
        ui.log("Individual PDFs archived", success=True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        ui.log("Build directory cleaned", success=True)
    
    # Done
    ui.set_phase("BUILD COMPLETE!")
    ui.set_task(f"Output: {OUTPUT_FILE}")
    ui.set_progress(total_sections + 1, total_sections + 1)
    ui.log(f"Created {OUTPUT_FILE} ({current_page - 1} pages)", success=True)
    
    # Wait for user to see results
    stdscr.nodelay(False)  # Re-enable blocking mode for final keypress
    ui.stdscr.addstr(ui.height - 1, (ui.width - 25) // 2, 
                     "Press any key to exit...", curses.color_pair(4))
    ui.stdscr.refresh()
    ui.stdscr.getch()
    
    return current_page - 1, len(selected_chapters)


def run_app(stdscr, args):
    # Show menu first
    hierarchy, options = show_menu(stdscr)
    
    if options is None:
        return  # User quit
    
    if not options['chapters']:
        # No chapters selected
        stdscr.clear()
        stdscr.addstr(5, 10, "No chapters selected. Press any key to exit.", 
                     curses.color_pair(4))
        stdscr.refresh()
        stdscr.getch()
        return
    
    # Run the build
    run_build(stdscr, args, hierarchy, options)


def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy framework documentation")
    parser.add_argument(
        "--leave-individual",
        action="store_true",
        help="Keep individual PDFs as a zip file instead of deleting them"
    )
    args = parser.parse_args()
    
    # Check terminal size before starting curses
    try:
        import shutil as sh
        term_size = sh.get_terminal_size()
        min_lines, min_cols = 25, 60
        if term_size.lines < min_lines or term_size.columns < min_cols:
            print(f"Error: Terminal too small!")
            print(f"Current size: {term_size.lines} lines × {term_size.columns} columns")
            print(f"Required:     {min_lines} lines × {min_cols} columns")
            print(f"\nPlease resize your terminal window and try again.")
            sys.exit(1)
    except Exception:
        pass  # If we can't determine size, let curses handle it
    
    try:
        curses.wrapper(lambda stdscr: run_app(stdscr, args))
    except KeyboardInterrupt:
        print("\nBuild cancelled.")
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        sys.exit(1)
    except Exception as e:
        print(f"\nBuild failed: {e}")
        import traceback
        traceback.print_exc()
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        sys.exit(1)

if __name__ == "__main__":
    main()
