import os
import sys
import json
import subprocess
import shutil
import argparse
import zipfile
import curses
from pathlib import Path

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
    temp_file.write_text('#import "templates/setup.typ": hierarchy\n#metadata(hierarchy) <hierarchy>')
    
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
        page_map_json_str = json.dumps(page_map)
        cmd.extend(["--input", f"page-map={page_map_json_str}"])
    
    if extra_flags:
        cmd.extend(extra_flags)
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        import time
        while process.poll() is None:
            if keyboard_check_callback:
                keyboard_check_callback()
            time.sleep(0.05)
        
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
    existing_files = [str(pdf) for pdf in pdf_files if pdf.exists()]
    
    if not existing_files:
        print("No PDF files to merge!")
        return
    
    print(f"Merging {len(existing_files)} files into {output_path}...")
    
    if shutil.which("pdfunite"):
        cmd = ["pdfunite"] + existing_files + [str(output_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"Successfully merged PDFs using pdfunite")
            return
        except subprocess.CalledProcessError as e:
            print(f"pdfunite failed: {e.stderr.decode()}")
    
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
    
    for chapter in hierarchy:
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
        if f"chapter-{chapter_id}" in page_map:
            bookmarks.append(f"BookmarkBegin")
            bookmarks.append(f"BookmarkTitle: {chapter['title']}")
            bookmarks.append(f"BookmarkLevel: 1")
            bookmarks.append(f"BookmarkPageNumber: {page_map[f'chapter-{chapter_id}']}")
        
        for page in chapter["pages"]:
            page_id = page["id"]
            if page_id in page_map:
                bookmarks.append(f"BookmarkBegin")
                bookmarks.append(f"BookmarkTitle: {page['title']}")
                bookmarks.append(f"BookmarkLevel: 2")
                bookmarks.append(f"BookmarkPageNumber: {page_map[page_id]}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bookmarks))
    
    print(f"✓ Created bookmarks file with {len(bookmarks)//4} entries")
    return output_file

def apply_pdf_metadata(pdf_path, bookmarks_file, title="Noteworthy Framework", author=""):
    temp_pdf = BUILD_DIR / "temp_with_metadata.pdf"
    
    if shutil.which("pdftk"):
        try:
            info_file = BUILD_DIR / "pdf_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"InfoBegin\n")
                f.write(f"InfoKey: Title\n")
                f.write(f"InfoValue: {title}\n")
                if author:
                    f.write(f"InfoKey: Author\n")
                    f.write(f"InfoValue: {author}\n")
            
            subprocess.run([
                "pdftk", str(pdf_path), "update_info", str(info_file), 
                "output", str(temp_pdf)
            ], check=True, capture_output=True)
            
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
    
    if shutil.which("gs"):
        try:
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

def show_error_screen(stdscr, error_message):
    import curses
    import traceback
    
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(6, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    
    sad_face = [
        "       __",
        "  _   / /",
        " (_) | | ",
        "     | | ",
        "  _  | | ",
        " (_) | | ",
        "      \\_\\",
    ]
    
    full_log = traceback.format_exc()
    if full_log.strip() == "NoneType: None":
        full_log = str(error_message)
    
    view_log = False
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        if view_log:
            stdscr.addstr(0, 2, "ERROR LOG (press 'v' to go back)", 
                         curses.color_pair(6) | curses.A_BOLD)
            stdscr.addstr(1, 0, "─" * width, curses.color_pair(4))
            
            log_lines = full_log.split('\n')
            for i, line in enumerate(log_lines):
                if i + 3 >= height - 1:
                    break
                try:
                    stdscr.addstr(i + 3, 2, line[:width - 4], curses.color_pair(4))
                except curses.error:
                    pass
        else:
            face_width = 9
            start_y = max(0, (height - len(sad_face) - 10) // 2)
            face_x = (width - face_width) // 2
            
            for i, line in enumerate(sad_face):
                try:
                    stdscr.addstr(start_y + i, face_x, line, curses.color_pair(6) | curses.A_BOLD)
                except curses.error:
                    pass
            
            msg_y = start_y + len(sad_face) + 2
            error_title = "BUILD FAILED"
            try:
                stdscr.addstr(msg_y, (width - len(error_title)) // 2, error_title, 
                             curses.color_pair(6) | curses.A_BOLD)
            except curses.error:
                pass
            
            error_str = str(error_message)
            max_error_len = width - 10
            if len(error_str) > max_error_len:
                error_str = error_str[:max_error_len - 3] + "..."
            try:
                stdscr.addstr(msg_y + 2, (width - len(error_str)) // 2, error_str, 
                             curses.color_pair(4))
            except curses.error:
                pass
            
            view_msg = "Press 'v' to view log  |  Press any other key to exit"
            try:
                stdscr.addstr(msg_y + 4, (width - len(view_msg)) // 2, view_msg, 
                             curses.color_pair(4) | curses.A_DIM)
            except curses.error:
                pass
        
        stdscr.refresh()
        stdscr.nodelay(False)
        key = stdscr.getch()
        
        if key == ord('v'):
            view_log = not view_log
        elif not view_log:
            break

class BuildMenu:
    def __init__(self, stdscr, hierarchy):
        self.stdscr = stdscr
        self.hierarchy = hierarchy
        self.debug_mode = False
        self.include_frontmatter = True
        self.leave_individual = False
        self.typst_flags = []
        self.scroll_offset = 0
        
        self.items = []
        self.selected = {}
        
        for ch_idx, chapter in enumerate(hierarchy):
            self.items.append(('chapter', ch_idx, None))
            self.selected[(ch_idx, None)] = True
            for art_idx, page in enumerate(chapter["pages"]):
                self.items.append(('article', ch_idx, art_idx))
                self.selected[(ch_idx, art_idx)] = True
        
        self.cursor = 0
        
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        
        self.stdscr.clear()
        self.height, self.width = stdscr.getmaxyx()
    
    def is_chapter_selected(self, ch_idx):
        chapter = self.hierarchy[ch_idx]
        return all(self.selected.get((ch_idx, art_idx), False) for art_idx in range(len(chapter["pages"])))
    
    def is_chapter_partial(self, ch_idx):
        chapter = self.hierarchy[ch_idx]
        selected_count = sum(1 for art_idx in range(len(chapter["pages"])) if self.selected.get((ch_idx, art_idx), False))
        return 0 < selected_count < len(chapter["pages"])
    
    def toggle_chapter(self, ch_idx):
        new_state = not self.is_chapter_selected(ch_idx)
        chapter = self.hierarchy[ch_idx]
        for art_idx in range(len(chapter["pages"])):
            self.selected[(ch_idx, art_idx)] = new_state
    
    def toggle_article(self, ch_idx, art_idx):
        self.selected[(ch_idx, art_idx)] = not self.selected.get((ch_idx, art_idx), False)
    
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
        
        logo_height = len(logo)
        options_box_height = 7
        min_chapter_rows = 3
        
        vertical_layout_min_height = logo_height + 2 + options_box_height + 1 + (min_chapter_rows + 2) + 2
        horizontal_layout_min_height = logo_height + 2 + options_box_height
        
        if self.height >= vertical_layout_min_height:
            layout = "vertical"
        elif self.height >= horizontal_layout_min_height and self.width >= 90:
            layout = "horizontal"
        elif self.width >= 90:
            layout = "ultra_compact"
        else:
            layout = "vertical"
        
        def render_items(box_y, box_x, box_width, max_rows):
            visible_rows = max_rows - 2
            
            if self.cursor < self.scroll_offset:
                self.scroll_offset = self.cursor
            elif self.cursor >= self.scroll_offset + visible_rows:
                self.scroll_offset = self.cursor - visible_rows + 1
            
            for row_idx in range(visible_rows):
                item_idx = self.scroll_offset + row_idx
                if item_idx >= len(self.items):
                    break
                
                item_type, ch_idx, art_idx = self.items[item_idx]
                row_y = box_y + 1 + row_idx
                
                is_cursor = item_idx == self.cursor
                if is_cursor:
                    self.safe_addstr(row_y, box_x + 2, "▶", curses.color_pair(3) | curses.A_BOLD)
                    attr = curses.A_BOLD
                else:
                    attr = 0
                
                if item_type == 'chapter':
                    chapter = self.hierarchy[ch_idx]
                    first_page = chapter["pages"][0]
                    chapter_id = first_page["id"][:2]
                    
                    if self.is_chapter_selected(ch_idx):
                        checkbox = "[✓]"
                        checkbox_color = curses.color_pair(2)
                    elif self.is_chapter_partial(ch_idx):
                        checkbox = "[~]"
                        checkbox_color = curses.color_pair(3)
                    else:
                        checkbox = "[ ]"
                        checkbox_color = curses.color_pair(4)
                    
                    self.safe_addstr(row_y, box_x + 4, checkbox, checkbox_color | attr)
                    chapter_text = f" Ch {chapter_id}: {chapter['title']}"[:box_width - 12]
                    self.safe_addstr(row_y, box_x + 7, chapter_text, curses.color_pair(1) | attr)
                
                else:
                    chapter = self.hierarchy[ch_idx]
                    page = chapter["pages"][art_idx]
                    page_id = page["id"]
                    
                    is_selected = self.selected.get((ch_idx, art_idx), False)
                    checkbox = "[✓]" if is_selected else "[ ]"
                    checkbox_color = curses.color_pair(2) if is_selected else curses.color_pair(4)
                    
                    self.safe_addstr(row_y, box_x + 6, checkbox, checkbox_color | attr)
                    article_text = f" {page_id}: {page['title']}"[:box_width - 14]
                    self.safe_addstr(row_y, box_x + 9, article_text, curses.color_pair(4) | attr)
        
        def render_options(start_y, box_x, box_width):
            debug_status = "[ON] " if self.debug_mode else "[OFF]"
            debug_color = curses.color_pair(2) if self.debug_mode else curses.color_pair(6)
            self.safe_addstr(start_y + 1, box_x + 2, "Debug Mode:   ", curses.color_pair(4))
            self.safe_addstr(start_y + 1, box_x + 16, debug_status, debug_color | curses.A_BOLD)
            self.safe_addstr(start_y + 1, box_x + 22, "(d)", curses.color_pair(4) | curses.A_DIM)
            
            fm_status = "[ON] " if self.include_frontmatter else "[OFF]"
            fm_color = curses.color_pair(2) if self.include_frontmatter else curses.color_pair(6)
            self.safe_addstr(start_y + 2, box_x + 2, "Frontmatter:  ", curses.color_pair(4))
            self.safe_addstr(start_y + 2, box_x + 16, fm_status, fm_color | curses.A_BOLD)
            self.safe_addstr(start_y + 2, box_x + 22, "(f)", curses.color_pair(4) | curses.A_DIM)
            
            li_status = "[ON] " if self.leave_individual else "[OFF]"
            li_color = curses.color_pair(2) if self.leave_individual else curses.color_pair(6)
            self.safe_addstr(start_y + 3, box_x + 2, "Leave PDFs:   ", curses.color_pair(4))
            self.safe_addstr(start_y + 3, box_x + 16, li_status, li_color | curses.A_BOLD)
            self.safe_addstr(start_y + 3, box_x + 22, "(l)", curses.color_pair(4) | curses.A_DIM)
            
            flags_display = " ".join(self.typst_flags) if self.typst_flags else "(none)"
            self.safe_addstr(start_y + 4, box_x + 2, "Typst Flags:  ", curses.color_pair(4))
            self.safe_addstr(start_y + 4, box_x + 16, flags_display[:box_width - 20],
                            curses.color_pair(5) if self.typst_flags else curses.color_pair(4) | curses.A_DIM)
            self.safe_addstr(start_y + 5, box_x + 16, "(c)", curses.color_pair(4) | curses.A_DIM)
        
        if layout == "ultra_compact":
            # === ULTRA-COMPACT LAYOUT (logo | options + chapters) ===
            left_col_width = 20
            right_col_width = min(50, self.width - left_col_width - 4)
            total_width = left_col_width + right_col_width + 2
            
            left_x = (self.width - total_width) // 2
            right_x = left_x + left_col_width + 2
            
            logo_start_y = max(0, (self.height - logo_height) // 2 - 1)
            logo_x = left_x + (left_col_width - 14) // 2
            for i, line in enumerate(logo):
                if logo_start_y + i < self.height - 1:
                    self.safe_addstr(logo_start_y + i, logo_x, line, curses.color_pair(1) | curses.A_BOLD)
            
            title = "NOTEWORTHY"
            title_y = logo_start_y + logo_height
            if title_y < self.height - 1:
                self.safe_addstr(title_y, left_x + (left_col_width - len(title)) // 2, title,
                                curses.color_pair(1) | curses.A_BOLD)
            
            options_y = 0
            self.draw_box(options_y, right_x, options_box_height, right_col_width, "Options")
            render_options(options_y, right_x, right_col_width)
            
            chapter_box_y = options_box_height + 1
            chapter_box_height = max(3, self.height - chapter_box_y - 2)
            self.draw_box(chapter_box_y, right_x, chapter_box_height, right_col_width, "Select Chapters")
            render_items(chapter_box_y, right_x, right_col_width, chapter_box_height)
            
            footer_y = self.height - 1
            controls = "↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  q:Quit"
            self.safe_addstr(footer_y, (self.width - len(controls)) // 2, controls,
                            curses.color_pair(4) | curses.A_DIM)
        
        elif layout == "horizontal":
            # === HORIZONTAL LAYOUT (side-by-side) ===
            left_box_width = min(40, (self.width - 6) // 2)
            right_box_width = min(50, (self.width - 6) // 2)
            total_content_width = left_box_width + right_box_width + 2
            
            left_x = (self.width - total_content_width) // 2
            right_x = left_x + left_box_width + 2
            
            left_col_height = logo_height + 2 + options_box_height
            
            logo_x = left_x + (left_box_width - 14) // 2
            for i, line in enumerate(logo):
                if i < self.height - 2:
                    self.safe_addstr(i, logo_x, line, curses.color_pair(1) | curses.A_BOLD)
            
            title = "NOTEWORTHY"
            title_y = logo_height
            self.safe_addstr(title_y, left_x + (left_box_width - len(title)) // 2, title,
                            curses.color_pair(1) | curses.A_BOLD)
            
            options_y = logo_height + 2
            self.draw_box(options_y, left_x, options_box_height, left_box_width, "Options")
            render_options(options_y, left_x, left_box_width)
            
            chapter_box_y = 0
            chapter_box_height = min(left_col_height, self.height - 2)
            if chapter_box_height > 2:
                self.draw_box(chapter_box_y, right_x, chapter_box_height, right_box_width, "Select Chapters")
                render_items(chapter_box_y, right_x, right_box_width, chapter_box_height)
            
            footer_y = self.height - 1
            controls = "↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  q:Quit"
            self.safe_addstr(footer_y, (self.width - len(controls)) // 2, controls,
                            curses.color_pair(4) | curses.A_DIM)
        
        else:
            # === VERTICAL LAYOUT (original stacked) ===
            logo_x = (self.width - 14) // 2
            for i, line in enumerate(logo):
                self.safe_addstr(i, logo_x, line, curses.color_pair(1) | curses.A_BOLD)
            
            title = "NOTEWORTHY"
            self.safe_addstr(logo_height + 1, (self.width - len(title)) // 2, title, 
                            curses.color_pair(1) | curses.A_BOLD)
            
            box_width = min(60, self.width - 4)
            box_x = (self.width - box_width) // 2
            start_y = logo_height + 3
            
            self.draw_box(start_y, box_x, options_box_height, box_width, "Options")
            render_options(start_y, box_x, box_width)
            
            chapter_box_y = start_y + 8
            chapter_box_height = min(len(self.items) + 2, self.height - chapter_box_y - 3)
            if chapter_box_height > 2:
                self.draw_box(chapter_box_y, box_x, chapter_box_height, box_width, "Select Chapters")
                render_items(chapter_box_y, box_x, box_width, chapter_box_height)
            
            footer_y = chapter_box_y + chapter_box_height + 1
            controls = "↑↓:Nav  Space:Toggle  a:All  n:None  Enter:Build  q:Quit"
            self.safe_addstr(footer_y, (self.width - len(controls)) // 2, controls,
                            curses.color_pair(4) | curses.A_DIM)
        
        self.stdscr.refresh()
    
    def configure_typst_flags(self):
        curses.echo()
        curses.curs_set(1)
        
        dialog_height = 12
        dialog_width = min(70, self.width - 4)
        dialog_y = (self.height - dialog_height) // 2
        dialog_x = (self.width - dialog_width) // 2
        
        dialog = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
        dialog.box()
        dialog.addstr(0, 2, " Configure Typst Flags ", curses.color_pair(1) | curses.A_BOLD)
        
        current = " ".join(self.typst_flags) if self.typst_flags else "(none)"
        dialog.addstr(2, 2, "Current: " + current[:dialog_width - 12])
        
        dialog.addstr(4, 2, "Common presets:", curses.color_pair(5))
        dialog.addstr(5, 2, "  1. --font-path /path/to/fonts")
        dialog.addstr(6, 2, "  2. --ppi 144")
        dialog.addstr(7, 2, "  3. Clear all flags")
        
        dialog.addstr(9, 2, "Enter flags (or preset number): ", curses.color_pair(4))
        dialog.refresh()
        
        curses.curs_set(1)
        input_str = dialog.getstr(9, 35, dialog_width - 37).decode('utf-8').strip()
        
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
            self.typst_flags = input_str.split()
        
        curses.noecho()
        curses.curs_set(0)
        self.refresh()
    
    def run(self):
        self.refresh()
        
        while True:
            key = self.stdscr.getch()
            
            if key == ord('q'):
                return None
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                selected_pages = []
                for ch_idx, chapter in enumerate(self.hierarchy):
                    for art_idx in range(len(chapter["pages"])):
                        if self.selected.get((ch_idx, art_idx), False):
                            selected_pages.append((ch_idx, art_idx))
                return {
                    'selected_pages': selected_pages,
                    'debug': self.debug_mode,
                    'frontmatter': self.include_frontmatter,
                    'leave_individual': self.leave_individual,
                    'typst_flags': self.typst_flags,
                }
            elif key == curses.KEY_UP or key == ord('k'):
                self.cursor = max(0, self.cursor - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                self.cursor = min(len(self.items) - 1, self.cursor + 1)
            elif key == ord(' '):
                item_type, ch_idx, art_idx = self.items[self.cursor]
                if item_type == 'chapter':
                    self.toggle_chapter(ch_idx)
                else:
                    self.toggle_article(ch_idx, art_idx)
            elif key == ord('a'):
                for ch_idx, chapter in enumerate(self.hierarchy):
                    for art_idx in range(len(chapter["pages"])):
                        self.selected[(ch_idx, art_idx)] = True
            elif key == ord('n'):
                for ch_idx, chapter in enumerate(self.hierarchy):
                    for art_idx in range(len(chapter["pages"])):
                        self.selected[(ch_idx, art_idx)] = False
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
        self.typst_logs = []
        self.current_task = ""
        self.progress = 0
        self.total = 0
        self.phase = ""
        self.debug_mode = debug_mode
        self.view_mode = "normal"
        self.typst_scroll_offset = 0
        
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        curses.init_pair(7, curses.COLOR_YELLOW, -1)
        
        self.stdscr.clear()
        self.height, self.width = stdscr.getmaxyx()
    
    def draw_box(self, y, x, h, w, title=""):
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
        if output:
            for line in output.split('\n'):
                if line.strip():
                    self.typst_logs.append(line)
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
        try:
            key = self.stdscr.getch()
            if key == ord('v'):
                self.view_mode = "typst" if self.view_mode == "normal" else "normal"
                self.typst_scroll_offset = 0
            elif self.view_mode == "typst":
                if key == curses.KEY_UP or key == ord('k'):
                    self.typst_scroll_offset = max(0, self.typst_scroll_offset - 1)
                    curses.flushinp()
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.typst_scroll_offset = min(len(self.typst_logs) - 1, self.typst_scroll_offset + 1)
                    curses.flushinp()
        except:
            pass
        
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        title = "NOTEWORTHY BUILD SYSTEM"
        if self.debug_mode:
            title += " [DEBUG]"
        self.stdscr.addstr(1, (self.width - len(title)) // 2, title, 
                          curses.color_pair(1) | curses.A_BOLD)
        
        box_width = min(60, self.width - 4)
        box_x = (self.width - box_width) // 2
        
        self.draw_box(3, box_x, 5, box_width, "Progress")
        
        if self.phase:
            phase_text = self.phase[:box_width - 6]
            self.stdscr.addstr(4, box_x + 2, phase_text, curses.color_pair(5))
        
        if self.current_task:
            task_text = self.current_task[:box_width - 6]
            self.stdscr.addstr(5, box_x + 2, f"→ {task_text}", curses.color_pair(4))
        
        self.draw_progress_bar(6, box_x + 2, box_width - 12, self.progress, self.total)
        
        log_height = min(15, self.height - 12)
        
        if self.view_mode == "typst" and self.typst_logs:
            box_title = "Typst Compiler Output (↑↓ or jk to scroll)"
            
            max_offset = max(0, len(self.typst_logs) - (log_height - 2))
            self.typst_scroll_offset = min(self.typst_scroll_offset, max_offset)
            
            start_idx = self.typst_scroll_offset
            end_idx = start_idx + (log_height - 2)
            visible_logs = self.typst_logs[start_idx:end_idx]
            
            log_items = []
            for msg in visible_logs:
                if 'error:' in msg.lower():
                    log_items.append((msg, False, 6))
                elif 'warning:' in msg.lower():
                    log_items.append((msg, False, 7))
                elif 'hint:' in msg.lower() or '= hint:' in msg:
                    log_items.append((msg, False, 1))
                elif msg.strip().startswith('┌─') or msg.strip().startswith('│') or '──' in msg:
                    log_items.append((msg, False, 5))
                else:
                    log_items.append((msg, False, 4))
        else:
            box_title = "Build Log"
            log_items = [(msg, success, 2 if success else 4) for msg, success in self.logs[-(log_height - 2):]]
        
        self.draw_box(9, box_x, log_height, box_width, box_title)
        
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
        
        footer = "Press Ctrl+C to cancel  |  Press 'v' to toggle view"
        try:
            self.stdscr.addstr(self.height - 1, (self.width - len(footer)) // 2, 
                              footer, curses.color_pair(4) | curses.A_DIM)
        except curses.error:
            pass
        
        self.stdscr.refresh()

def show_menu(stdscr):
    hierarchy = extract_hierarchy()
    menu = BuildMenu(stdscr, hierarchy)
    result = menu.run()
    return hierarchy, result

def run_build(stdscr, args, hierarchy, options):
    ui = BuildUI(stdscr, debug_mode=options['debug'])
    
    stdscr.nodelay(True)
    
    def keyboard_check():
        ui.refresh()
    
    ui.log("Checking dependencies...")
    ui.debug("Running dependency check...")
    check_dependencies()
    ui.log("Dependencies OK", success=True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    ui.log("Build directory prepared", success=True)
    
    selected_pages = options.get('selected_pages', [])
    
    selected_by_chapter = {}
    for ch_idx, art_idx in selected_pages:
        if ch_idx not in selected_by_chapter:
            selected_by_chapter[ch_idx] = []
        selected_by_chapter[ch_idx].append(art_idx)
    
    selected_chapter_indices = sorted(selected_by_chapter.keys())
    selected_chapters = [(i, hierarchy[i]) for i in selected_chapter_indices]
    
    total_selected_pages = len(selected_pages)
    ui.log(f"Building {total_selected_pages} pages from {len(selected_chapters)} chapters", success=True)
    
    total_sections = 0
    if options['frontmatter']:
        total_sections += 3
    for ch_idx, chapter in selected_chapters:
        total_sections += 1
        total_sections += len(selected_by_chapter[ch_idx])
    
    ui.set_phase("Compiling Sections")
    ui.set_progress(0, total_sections + 1)
    
    page_map = {}
    current_page = 1
    pdf_files = []
    progress = 0
    
    if options['frontmatter']:
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
    
    for ch_idx, chapter in selected_chapters:
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2]
        
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
        
        for art_idx in sorted(selected_by_chapter[ch_idx]):
            page = chapter["pages"][art_idx]
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
    
    page_map_file = BUILD_DIR / "page_map.json"
    with open(page_map_file, 'w') as f:
        json.dump(page_map, f, indent=2)
    ui.debug(f"Page map saved to {page_map_file}")
    
    ui.log(f"Total pages: {current_page - 1}", success=True)
    
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
    
    ui.set_phase("Adding Metadata")
    ui.set_task("Creating bookmarks")
    bookmarks_file = BUILD_DIR / "bookmarks.txt"
    chapters_for_metadata = [chapter for _, chapter in selected_chapters]
    create_pdf_metadata(chapters_for_metadata, page_map, bookmarks_file)
    
    ui.set_task("Applying PDF metadata")
    title = "Noteworthy Framework"
    author = "Sihoo Lee, Lee Hojun"
    apply_pdf_metadata(OUTPUT_FILE, bookmarks_file, title, author)
    ui.log("PDF metadata applied", success=True)
    
    ui.set_phase("Cleanup")
    
    if options['leave_individual']:
        ui.set_task("Archiving individual PDFs")
        zip_build_directory(BUILD_DIR)
        ui.log("Individual PDFs archived", success=True)
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        ui.log("Build directory cleaned", success=True)
    
    ui.set_phase("BUILD COMPLETE!")
    ui.set_task(f"Output: {OUTPUT_FILE}")
    ui.set_progress(total_sections + 1, total_sections + 1)
    ui.log(f"Created {OUTPUT_FILE} ({current_page - 1} pages)", success=True)
    
    stdscr.nodelay(False)
    stdscr.clear()
    
    confetti = [
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀",
        "⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡈⠀⡠⠀⠀⣤⡄⠀⠀",
        "⠀⠀⠀⠀⠒⢀⣴⠟⠛⠓⠀⠀⠓⠀⠀⠀⢠⠉⠡⠀⠀",
        "⠀⠀⠀⣴⡆⠘⠧⠶⠶⢦⠀⠀⠰⠇⠀⠀⣀⠀⠀⣀⠀",
        "⠀⠀⠀⠀⠀⡠⠤⢀⣀⣼⠀⠀⣀⣀⡀⣦⠉⠳⠆⠋⠀",
        "⠀⠀⠀⢀⠄⡁⠀⣠⠿⠃⢤⡀⢽⠈⠉⠁⣀⣀⠀⠀⠀",
        "⠀⠀⠀⣾⠜⢐⠀⠁⠀⠀⠙⠻⣎⠀⠀⠀⠙⠉⠀⡀⢄",
        "⠀⠀⠜⠋⣎⠀⠀⠠⠀⢀⣠⣤⣼⣦⣤⣤⣀⠀⠀⠐⠈",
        "⠀⣌⠎⠘⢿⣦⡀⠀⠈⠙⠥⢀⣀⠄⠀⠈⠉⠃⠀⣴⡀",
        "⢠⢿⣦⡀⠈⠻⣿⣦⣔⢀⠠⠂⠀⠀⠠⣾⠗⠀⠀⠈⠀",
        "⣏⠀⠙⣿⣦⡂⠄⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
        "⠈⠓⠂⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
    ]
    
    height, width = stdscr.getmaxyx()
    confetti_width = 17
    
    start_y = max(0, (height - len(confetti) - 8) // 2)
    confetti_x = (width - confetti_width) // 2
    
    for i, line in enumerate(confetti):
        try:
            stdscr.addstr(start_y + i, confetti_x, line, curses.color_pair(2))
        except curses.error:
            pass
    
    msg_y = start_y + len(confetti) + 2
    success_msg = "BUILD SUCCEEDED!"
    try:
        stdscr.addstr(msg_y, (width - len(success_msg)) // 2, success_msg, 
                     curses.color_pair(2) | curses.A_BOLD)
    except curses.error:
        pass
    
    output_msg = f"Created: {OUTPUT_FILE} ({current_page - 1} pages)"
    try:
        stdscr.addstr(msg_y + 2, (width - len(output_msg)) // 2, output_msg, 
                     curses.color_pair(4))
    except curses.error:
        pass
    
    exit_msg = "Press any key to exit..."
    try:
        stdscr.addstr(msg_y + 4, (width - len(exit_msg)) // 2, exit_msg, 
                     curses.color_pair(4) | curses.A_DIM)
    except curses.error:
        pass
    
    stdscr.refresh()
    stdscr.getch()
    
    return current_page - 1, len(selected_chapters)

def run_app(stdscr, args):
    hierarchy, options = show_menu(stdscr)
    
    if options is None:
        return
    
    if not options.get('selected_pages'):
        show_error_screen(stdscr, "No pages selected")
        return
    
    try:
        run_build(stdscr, args, hierarchy, options)
    except Exception as e:
        show_error_screen(stdscr, e)

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy framework documentation")
    parser.add_argument(
        "--leave-individual",
        action="store_true",
        help="Keep individual PDFs as a zip file instead of deleting them"
    )
    args = parser.parse_args()
    
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
        pass
    
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
