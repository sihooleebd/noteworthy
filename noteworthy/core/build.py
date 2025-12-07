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
    for key, title in [('cover', 'Cover'), ('preface', 'Preface'), ('outline', 'Table of Contents')]:
        if key in page_map:
            bookmarks.extend([f'BookmarkBegin', f'BookmarkTitle: {title}', f'BookmarkLevel: 1', f'BookmarkPageNumber: {page_map[key]}'])
    for ci, ch in chapters:
        ch_id = str(ch.get('number', ci + 1))
        if f'chapter-{ci + 1}' in page_map:
            bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {ch['title']}", f'BookmarkLevel: 1', f"BookmarkPageNumber: {page_map[f'chapter-{ci + 1}']}"])
        for ai, p in enumerate(ch['pages']):
            key = f'{ci}/{ai}'
            if key in page_map:
                bookmarks.extend([f'BookmarkBegin', f"BookmarkTitle: {p['title']}", f'BookmarkLevel: 2', f'BookmarkPageNumber: {page_map[key]}'])
    Path(output_file).write_text('\n'.join(bookmarks))

def apply_pdf_metadata(pdf, bookmarks_file, title, author):
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
        lines = Path(bookmarks_file).read_text().split('\n')
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