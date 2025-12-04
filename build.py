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

def compile_target(target, output_path, page_offset=None, page_map=None, quiet=True):
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
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(f"Error compiling {target}:")
            print(e.stderr.decode())
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
        self.draw_box(start_y, box_x, 5, box_width, "Options")
        
        # Debug mode toggle
        debug_status = "[ON] " if self.debug_mode else "[OFF]"
        debug_color = curses.color_pair(2) if self.debug_mode else curses.color_pair(6)
        self.safe_addstr(start_y + 1, box_x + 2, "Debug Mode: ", curses.color_pair(4))
        self.safe_addstr(start_y + 1, box_x + 14, debug_status, debug_color | curses.A_BOLD)
        self.safe_addstr(start_y + 1, box_x + 20, "(d)", curses.color_pair(4) | curses.A_DIM)
        
        # Frontmatter toggle
        fm_status = "[ON] " if self.include_frontmatter else "[OFF]"
        fm_color = curses.color_pair(2) if self.include_frontmatter else curses.color_pair(6)
        self.safe_addstr(start_y + 2, box_x + 2, "Frontmatter: ", curses.color_pair(4))
        self.safe_addstr(start_y + 2, box_x + 15, fm_status, fm_color | curses.A_BOLD)
        self.safe_addstr(start_y + 2, box_x + 21, "(f)", curses.color_pair(4) | curses.A_DIM)
        
        # Leave Individual toggle
        li_status = "[ON] " if self.leave_individual else "[OFF]"
        li_color = curses.color_pair(2) if self.leave_individual else curses.color_pair(6)
        self.safe_addstr(start_y + 3, box_x + 2, "Leave PDFs:  ", curses.color_pair(4))
        self.safe_addstr(start_y + 3, box_x + 15, li_status, li_color | curses.A_BOLD)
        self.safe_addstr(start_y + 3, box_x + 21, "(l)", curses.color_pair(4) | curses.A_DIM)
        
        # Chapter selection box
        chapter_box_y = start_y + 6
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
            
            self.refresh()


class BuildUI:
    def __init__(self, stdscr, debug_mode=False):
        self.stdscr = stdscr
        self.logs = []
        self.current_task = ""
        self.progress = 0
        self.total = 0
        self.phase = ""
        self.debug_mode = debug_mode
        
        # Setup curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # Title
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # Success
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Progress
        curses.init_pair(4, curses.COLOR_WHITE, -1)    # Normal
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Phase
        
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
        self.draw_box(9, box_x, log_height, box_width, "Build Log")
        
        # Show logs
        visible_logs = self.logs[-(log_height - 2):]
        for i, (msg, success) in enumerate(visible_logs):
            color = curses.color_pair(2) if success else curses.color_pair(4)
            prefix = "✓ " if success else "  "
            text = (prefix + msg)[:box_width - 4]
            try:
                self.stdscr.addstr(10 + i, box_x + 2, text, color)
            except curses.error:
                pass
        
        # Footer
        footer = "Press Ctrl+C to cancel"
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
        compile_target(target, output)
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
        compile_target(target, output)
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
        compile_target(target, output)
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
        compile_target(target, output, page_offset=current_page)
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
            compile_target(target, output, page_offset=current_page)
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
        compile_target(target, output, page_offset=page_map["outline"], page_map=page_map)
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
