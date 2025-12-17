import shutil
import subprocess
import os
import fcntl
import time
import json
import logging
from pathlib import Path
from ..config import BASE_DIR, BUILD_DIR, RENDERER_FILE

def get_pdf_page_count(pdf_path):
    try:
        result = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except:
        pass
    return 0

def compile_target(target, output, page_offset=None, page_map=None, extra_flags=None, callback=None, log_callback=None):
    cmd = ['typst', 'compile', str(RENDERER_FILE), str(output), '--root', str(BASE_DIR), '--input', f'target={target}']
    if page_offset:
        cmd.extend(['--input', f'page-offset={page_offset}'])
    if page_map:
        pm_file = BUILD_DIR / 'page_map.json'
        try:
            pm_file.write_text(json.dumps(page_map))
            logging.info(f'Wrote page_map to {pm_file} ({len(json.dumps(page_map))} bytes)')
            rel_path = pm_file.relative_to(BASE_DIR)
            cmd.extend(['--input', f'page-map-file=/{rel_path}'])
        except Exception as e:
            logging.error(f'Failed to write page_map file: {e}')
            cmd.extend(['--input', f'page-map={json.dumps(page_map)}'])
    if extra_flags:
        cmd.extend(extra_flags)
    logging.info(f'Executing typst for {target}')
    if log_callback:
        log_callback(f'[compile] {target} -> {output.name}\n')
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as e:
        logging.error(f'Popen failed for {target}: {e}')
        raise e
    all_output = []
    fd = proc.stderr.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    fd_out = proc.stdout.fileno()
    fl_out = fcntl.fcntl(fd_out, fcntl.F_GETFL)
    fcntl.fcntl(fd_out, fcntl.F_SETFL, fl_out | os.O_NONBLOCK)
    while proc.poll() is None:
        if callback and callback() is False:
            proc.terminate()
            raise Exception('Build cancelled')
        try:
            chunk = proc.stderr.read(4096)
            if chunk:
                all_output.append(chunk)
                if log_callback:
                    log_callback(chunk)
        except:
            pass
        try:
            chunk = proc.stdout.read(4096)
            if chunk:
                all_output.append(chunk)
                if log_callback:
                    log_callback(chunk)
        except:
            pass
        time.sleep(0.05)
    stdout, stderr = proc.communicate()
    if stderr:
        all_output.append(stderr)
        if log_callback:
            log_callback(stderr)
    if stdout:
        all_output.append(stdout)
        if log_callback:
            log_callback(stdout)
    if proc.returncode != 0:
        logging.error(f'Typst compilation failed for {target}. Return code: {proc.returncode}')
        logging.error(f"Output: {''.join(all_output)}")
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=''.join(all_output))
    if log_callback:
        log_callback(f'[done] {target}\n')
    return ''.join(all_output)

def merge_pdfs(pdf_files, output):
    files = [str(p) for p in pdf_files if p.exists()]
    logging.info(f"Merging {len(files)} files. First: {(files[0] if files else 'None')}")
    if not files:
        return False
    if shutil.which('pdfunite'):
        logging.info('Using pdfunite')
        try:
            subprocess.run(['pdfunite'] + files + [str(output)], check=True, capture_output=True)
            return 'pdfunite'
        except Exception as e:
            logging.error(f'pdfunite failed: {e}')
    elif shutil.which('gs'):
        logging.info('Using ghostscript')
        try:
            subprocess.run(['gs', '-dBATCH', '-dNOPAUSE', '-q', '-sDEVICE=pdfwrite', f'-sOutputFile={output}'] + files, check=True, capture_output=True)
            return 'ghostscript'
        except Exception as e:
            logging.error(f'ghostscript failed: {e}')
    return None

def create_pdf_metadata(chapters, page_map, output_file):
    bookmarks = []
    
    try:
        import pypdf
    except ImportError:
        logging.warning("pypdf not found, skipping deep bookmark extraction")
        pypdf = None

    def extract_bookmarks(pdf_path, base_level, start_page):
        if not pypdf or not pdf_path.exists():
            return []
        
        extracted = []
        try:
            reader = pypdf.PdfReader(pdf_path)
            
            def process_outline(outline_items, current_level):
                res = []
                for item in outline_items:
                    if isinstance(item, list):
                        res.extend(process_outline(item, current_level + 1))
                    elif hasattr(item, 'title'):
                        try:
                            pg = reader.get_page_number(item.page)
                            res.append({
                                'title': item.title,
                                'level': current_level,
                                'page': start_page + pg
                            })
                        except:
                            pass
                return res
                
            extracted = process_outline(reader.outline, base_level + 1)
            
        except Exception as e:
            logging.error(f"Failed to extract bookmarks from {pdf_path}: {e}")
            
        return extracted

    for key, title in [('cover', 'Cover'), ('preface', 'Preface'), ('outline', 'Table of Contents')]:
        if key in page_map:
            bookmarks.extend([f'BookmarkBegin', f'BookmarkTitle: {title}', f'BookmarkLevel: 1', f'BookmarkPageNumber: {page_map[key]}'])

    for ci, ch in chapters:
        ch_id = str(ch.get('number', ci + 1))
        ch_key = f'chapter-{ci + 1}'
        
        if ch_key in page_map:
            start_pg = page_map[ch_key]
            bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {ch['title']}", f'BookmarkLevel: 1', f"BookmarkPageNumber: {start_pg}"])
            
            pdf_path = BUILD_DIR / f'10_chapter_{ci}_cover.pdf'
            
            sub_marks = extract_bookmarks(pdf_path, 1, start_pg)
            for sm in sub_marks:
                bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {sm['title']}", f'BookmarkLevel: {sm["level"]}', f"BookmarkPageNumber: {sm['page']}"])

        for ai, p in enumerate(ch['pages']):
            key = f'{ci}/{ai}'
            if key in page_map:
                start_pg = page_map[key]
                bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {p['title']}", f'BookmarkLevel: 2', f"BookmarkPageNumber: {start_pg}"])
                
                pdf_path = BUILD_DIR / f'20_page_{ci}_{ai}.pdf'
                
                sub_marks = extract_bookmarks(pdf_path, 2, start_pg)
                for sm in sub_marks:
                    bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {sm['title']}", f'BookmarkLevel: {sm["level"]}', f"BookmarkPageNumber: {sm['page']}"])
                        
import concurrent.futures

class BuildManager:
    def __init__(self, build_dir):
        self.build_dir = build_dir
        self.cache_file = build_dir / 'page_cache.json'
        self.page_counts = self.load_cache()
        self.page_map = {}
        self.current_offset = 1
        import threading
        self.lock = threading.Lock()
        
    def load_cache(self):
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text())
            except:
                pass
        return {}
        
    def save_cache(self):
        try:
            self.cache_file.write_text(json.dumps(self.page_counts))
        except:
            pass
            
    def get_predicted_count(self, key):
        return self.page_counts.get(key, 1)
        
    def update_count(self, key, count):
        with self.lock:
            self.page_counts[key] = count
            
    def build_parallel(self, chapters, config, opts, callbacks):
        max_workers = opts.get('threads', os.cpu_count() or 1)
        flags = opts.get('typst_flags', [])
        
        tasks = []
        
        if opts['frontmatter']:
            if config.get('display-cover', True):
                tasks.append(('cover', 'front', 'cover', self.build_dir / '00_cover.pdf', 'Cover'))
            tasks.append(('preface', 'front', 'preface', self.build_dir / '01_preface.pdf', 'Preface'))
            if config.get('display-outline', True):
                tasks.append(('outline', 'front', 'outline', self.build_dir / '02_outline.pdf', 'TOC'))
                
        for ci, ch in chapters:
            ch_id = str(ch.get('number', ci + 1))
            ch_key = f'chapter-{ci + 1}'
            if config.get('display-chap-cover', True):
                tasks.append((ch_key, 'chapter', f'chapter-{ci}', self.build_dir / f'10_chapter_{ci}_cover.pdf', f"Chapter {ch_id}"))
            
            for ai, p in enumerate(ch['pages']):
                key = f'{ci}/{ai}'
                pg_num = p.get('number', ai + 1)
                tasks.append((key, 'section', key, self.build_dir / f'20_page_{ci}_{ai}.pdf', f"Section {pg_num}: {p['title']}"))

        task_map = {t[0]: t for t in tasks}
        projected_offsets = {}
        ordered_keys = [t[0] for t in tasks]
        
        current = 1
        for key in ordered_keys:
            projected_offsets[key] = current
            current += self.get_predicted_count(key)
            
        iteration = 0
        while True:
            iteration += 1
            callbacks.get('on_log', lambda m, o: None)(f"Build Pass {iteration}...", True)
            
            to_run = []
            for key in ordered_keys:
                 to_run.append(key)
            
            if iteration > 1:
                new_offsets = {}
                curr = 1
                dirty_index = -1
                
                for idx, key in enumerate(ordered_keys):
                    new_offsets[key] = curr
                    actual = self.get_predicted_count(key)
                    curr += actual
                    
                    if dirty_index == -1:
                        if new_offsets[key] != projected_offsets[key]:
                            dirty_index = idx
                            
                if dirty_index == -1:
                    break
                    
                projected_offsets = new_offsets
                to_run = ordered_keys[dirty_index:]
                callbacks.get('on_log', lambda m, o: None)(f"Detected layout shift at {ordered_keys[dirty_index]}. Recompiling {len(to_run)} tasks.", True)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_key = {}
                for key in to_run:
                    t_data = task_map[key]
                    offset = projected_offsets[key]
                    
                    f = executor.submit(
                        compile_target, 
                        t_data[2],
                        t_data[3],
                        page_offset=offset,
                        extra_flags=flags,
                        log_callback=lambda m: None 
                    )
                    future_to_key[f] = key
                    
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_key):
                    key = future_to_key[future]
                    try:
                        res = future.result()
                        path = task_map[key][3]
                        count = get_pdf_page_count(path)
                        
                        self.update_count(key, count)
                        
                        completed_count += 1
                        if callbacks.get('on_progress'):
                            callbacks['on_progress']()
                            
                    except Exception as e:
                        callbacks.get('on_log', lambda m, o: None)(f"Task {key} failed: {e}", False)
                        raise e 
                        
            if iteration > 3:
                callbacks.get('on_log', lambda m, o: None)("Max retries reached. Pagination might be unstable.", False)
                break
                
        self.save_cache()
        self.page_map = projected_offsets
        return [task_map[k][3] for k in ordered_keys]

def create_pdf_metadata(chapters, page_map, output_file):
    bookmarks = []
    
    try:
        import pypdf
    except ImportError:
        logging.warning("pypdf not found, skipping deep bookmark extraction")
        pypdf = None

    def extract_bookmarks(pdf_path, base_level, start_page):
        if not pypdf or not pdf_path.exists():
            return []
        
        extracted = []
        try:
            reader = pypdf.PdfReader(pdf_path)
            
            def process_outline(outline_items, current_level):
                res = []
                for item in outline_items:
                    if isinstance(item, list):
                        res.extend(process_outline(item, current_level + 1))
                    elif hasattr(item, 'title'):
                        try:
                            pg = reader.get_page_number(item.page)
                            res.append({
                                'title': item.title,
                                'level': current_level,
                                'page': start_page + pg
                            })
                        except:
                            pass
                return res
                
            extracted = process_outline(reader.outline, base_level + 1)
            
        except Exception as e:
            logging.error(f"Failed to extract bookmarks from {pdf_path}: {e}")
            
        return extracted

    for key, title in [('cover', 'Cover'), ('preface', 'Preface'), ('outline', 'Table of Contents')]:
        if key in page_map:
            bookmarks.extend([f'BookmarkBegin', f'BookmarkTitle: {title}', f'BookmarkLevel: 1', f'BookmarkPageNumber: {page_map[key]}'])

    for ci, ch in chapters:
        ch_id = str(ch.get('number', ci + 1))
        ch_key = f'chapter-{ci + 1}'
        
        if ch_key in page_map:
            start_pg = page_map[ch_key]
            bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {ch['title']}", f'BookmarkLevel: 1', f"BookmarkPageNumber: {start_pg}"])
            
            pdf_path = BUILD_DIR / f'10_chapter_{ci}_cover.pdf'
            
            sub_marks = extract_bookmarks(pdf_path, 1, start_pg)
            for sm in sub_marks:
                bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {sm['title']}", f'BookmarkLevel: {sm["level"]}', f"BookmarkPageNumber: {sm['page']}"])

        for ai, p in enumerate(ch['pages']):
            key = f'{ci}/{ai}'
            if key in page_map:
                start_pg = page_map[key]
                bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {p['title']}", f'BookmarkLevel: 2', f"BookmarkPageNumber: {start_pg}"])
                
                pdf_path = BUILD_DIR / f'20_page_{ci}_{ai}.pdf'
                
                sub_marks = extract_bookmarks(pdf_path, 2, start_pg)
                for sm in sub_marks:
                    bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {sm['title']}", f'BookmarkLevel: {sm["level"]}', f"BookmarkPageNumber: {sm['page']}"])
                        
    Path(output_file).write_text('\n'.join(bookmarks))
    return bookmarks

def apply_metadata_pypdf(pdf, bookmarks_list, title, author):
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf)
        writer = pypdf.PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.add_metadata({
            '/Title': title,
            '/Author': author,
            '/Creator': 'Typst Noteworthy'
        })
        
        parents = {0: None}
        
        i = 0
        while i < len(bookmarks_list):
            line = bookmarks_list[i]
            if line == 'BookmarkBegin':
                try:
                    t = bookmarks_list[i+1].split(': ', 1)[1]
                    l = int(bookmarks_list[i+2].split(': ', 1)[1])
                    pg = int(bookmarks_list[i+3].split(': ', 1)[1])
                    
                    parent = parents.get(l - 1, None)
                    
                    parents[l] = writer.add_outline_item(t, pg - 1, parent)
                    
                    i += 4
                except:
                    i += 1
            else:
                i += 1
                
        writer.write(pdf)
        return True
    except Exception as e:
        logging.error(f"pypdf metadata application failed: {e}")
        return False

def apply_pdf_metadata(pdf, bookmarks_file, title, author, bookmarks_list=None):
    lines = bookmarks_list if bookmarks_list else Path(bookmarks_file).read_text().split('\n')
    
    if apply_metadata_pypdf(pdf, lines, title, author):
        return True

    temp = BUILD_DIR / 'temp.pdf'
    if shutil.which('pdftk'):
        info = BUILD_DIR / 'info.txt'
        info.write_text(f'InfoBegin\nInfoKey: Title\nInfoValue: {title}\nInfoKey: Author\nInfoValue: {author}\n')
        subprocess.run(['pdftk', str(pdf), 'update_info', str(info), 'output', str(temp)], check=True, capture_output=True)
        temp2 = BUILD_DIR / 'temp2.pdf'
        subprocess.run(['pdftk', str(temp), 'update_info', str(bookmarks_file), 'output', str(temp2)], check=True, capture_output=True)
        shutil.move(temp2, pdf)
        return True
    elif shutil.which('gs'):
        pdfmark = BUILD_DIR / 'bookmarks.pdfmark'
        marks = [f'[ /Title ({title}) /Author ({author}) /DOCINFO pdfmark']
        i = 0
        while i < len(lines):
            if lines[i].strip() == 'BookmarkBegin':
                t = lines[i + 1].split(': ', 1)[1] if ': ' in lines[i + 1] else ''
                pg = lines[i + 3].split(': ', 1)[1] if ': ' in lines[i + 3] else '1'
                marks.append(f'[ /Title ({t}) /Page {pg} /Count 0 /OUT pdfmark')
                i += 4
            else:
                i += 1
        pdfmark.write_text('\n'.join(marks))
        subprocess.run(['gs', '-dBATCH', '-dNOPAUSE', '-q', '-sDEVICE=pdfwrite', f'-sOutputFile={temp}', str(pdf), str(pdfmark)], check=True, capture_output=True)
        shutil.move(temp, pdf)
        return True
    return False

def zip_build_directory(build_dir, output='build_pdfs.zip'):
    import zipfile
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(build_dir):
            for f in files:
                path = Path(root) / f
                z.write(path, path.relative_to(build_dir.parent))