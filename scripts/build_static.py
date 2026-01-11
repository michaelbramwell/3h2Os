import shutil
import os
from pathlib import Path
import subprocess

def build_static():
    """
    Builds the static site version of the dashboard for GitHub Pages.
    1. Builds the TypeScript.
    2. Copies the index.html to the root.
    3. Copies the static assets to the root (excluding source files).
    """
    root = Path(__file__).parent.parent
    app_dir = root / "app"
    static_src = app_dir / "static"
    static_dst = root / "static"
    
    print(f"Building static site in {root}...")

    # 1. Build TypeScript
    print("Compiling TypeScript...")
    try:
        # Check if node_modules exists, if not install
        if not (static_src / "node_modules").exists():
            subprocess.run("npm install", cwd=static_src, check=True, shell=True)
        
        subprocess.run("npm run build", cwd=static_src, check=True, shell=True)
    except Exception as e:
        print(f"Warning: TypeScript build failed: {e}")
        print("Continuing with existing JS files...")

    # 2. Copy static assets
    print("Copying static assets...")
    if static_dst.exists():
        shutil.rmtree(static_dst)
    
    # Copy app/static to /static, ignoring dev files
    shutil.copytree(
        static_src, 
        static_dst, 
        ignore=shutil.ignore_patterns(
            "node_modules", 
            "ts", 
            "package.json", 
            "package-lock.json", 
            "tsconfig.json",
            ".gitignore"
        )
    )

    # 3. Copy and Transform Index HTML
    print("Generating root index.html...")
    src_html = app_dir / "templates" / "index.html"
    dst_html = root / "index.html"
    
    content = src_html.read_text()
    
    # Transform absolute paths to relative for GitHub Pages (Project site support)
    # /static/js/dashboard.js -> static/js/dashboard.js
    content = content.replace('src="/static/', 'src="static/')
    content = content.replace('href="/static/', 'href="static/')
    
    dst_html.write_text(content)
    
    # 4. Copy Data Files
    print("Copying data files to root...")
    data_dir = root / "data"
    for filename in ["plan.json", "context.json", "actuals.json"]:
        src = data_dir / filename
        dst = root / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"   - Copied {filename}")
        else:
            print(f"   ! Missing {filename}")
    
    print("Static site build complete.")
    print(f"   - {dst_html}")
    print(f"   - {static_dst}")

if __name__ == "__main__":
    build_static()
