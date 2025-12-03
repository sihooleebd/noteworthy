import os
import sys
import json
import subprocess
import shutil
import argparse
import zipfile
from pathlib import Path

# Configuration
BUILD_DIR = Path("build")
OUTPUT_FILE = Path("output.pdf")
RENDERER_FILE = "renderer.typ"

def check_dependencies():
    if shutil.which("typst") is None:
        print("Error: 'typst' executable not found in PATH.")
        sys.exit(1)

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

def compile_target(target, output_path):
    print(f"Compiling target: {target} -> {output_path}")
    
    cmd = [
        "typst", "compile", 
        RENDERER_FILE, 
        str(output_path),
        "--input", f"target={target}"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {target}:")
        print(e.stderr.decode())
        sys.exit(1)

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

def main():
    parser = argparse.ArgumentParser(description="Build Noteworthy framework documentation")
    parser.add_argument(
        "--leave-individual",
        action="store_true",
        help="Keep individual PDFs as a zip file instead of deleting them"
    )
    args = parser.parse_args()
    
    check_dependencies()
    
    # Clean build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir()
    
    hierarchy = extract_hierarchy()
    
    pdf_files = []
    
    # 1. Cover
    target = "cover"
    output = BUILD_DIR / "00_cover.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    
    # 2. Preface
    target = "preface"
    output = BUILD_DIR / "01_preface.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    
    # 3. Outline
    target = "outline"
    output = BUILD_DIR / "02_outline.pdf"
    compile_target(target, output)
    pdf_files.append(output)
    
    # 4. Chapters
    for i, chapter in enumerate(hierarchy):
        first_page = chapter["pages"][0]
        chapter_id = first_page["id"][:2] 
        
        # Chapter Cover
        target = f"chapter-{chapter_id}"
        output = BUILD_DIR / f"10_chapter_{chapter_id}_cover.pdf"
        compile_target(target, output)
        pdf_files.append(output)
        
        # Pages
        for page in chapter["pages"]:
            page_id = page["id"]
            target = page_id
            output = BUILD_DIR / f"20_page_{page_id}.pdf"
            compile_target(target, output)
            pdf_files.append(output)
            
    # Merge
    merge_pdfs_with_command(pdf_files, OUTPUT_FILE)
    print(f"Successfully created {OUTPUT_FILE}")
    
    # Cleanup or archive build directory
    if args.leave_individual:
        zip_build_directory(BUILD_DIR)
        print(f"Individual PDFs archived in build_pdfs.zip")
    
    # Always remove build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print("Build directory cleaned up")

if __name__ == "__main__":
    main()
