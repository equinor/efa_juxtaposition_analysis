#!/usr/bin/env python3
"""
EFA Juxtaposition Analysis - Quick Installer
Downloads and installs the application using uv without requiring git clone

Usage:
    python install_efa.py


"""

import subprocess
import sys
import urllib.request
import os
import tempfile
import shutil
from pathlib import Path

def check_uv():
    """Check if uv is installed"""
    try:
        result = subprocess.run(["uv", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ uv is installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ uv is not installed")
        print("\nPlease install uv first:")
        print("Windows: winget install --id=astral-sh.uv -e")
        print("Unix/Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def install_from_github():
    """Install directly from GitHub repository"""
    print("🔄 Installing EFA Juxtaposition Analysis from GitHub...")
    
    try:
        # Try to install as a package
        subprocess.run([
            "uv", "tool", "install", 
            "git+https://github.com/equinor/efa_juxtaposition_analysis.git"
        ], check=True)
        print("✅ Installed as uv tool")
        print("\nTo run the application:")
        print("    efa-juxtaposition")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Tool installation failed, trying alternative method...")
        return False

def manual_setup():
    """Manual setup by downloading files"""
    print("🔄 Setting up manually...")
    
    # Create installation directory
    install_dir = Path.home() / "efa_juxtaposition_analysis"
    install_dir.mkdir(exist_ok=True)
    
    os.chdir(install_dir)
    print(f"📁 Working in: {install_dir}")
    
    # Initialize uv project
    if not (install_dir / "pyproject.toml").exists():
        print("🔧 Initializing uv project...")
        subprocess.run(["uv", "init", "."], check=True)
    
    # Add dependencies
    print("📦 Installing dependencies...")
    subprocess.run([
        "uv", "add", 
        "numpy", "pandas", "matplotlib", "scipy", "shapely", "pillow"
    ], check=True)
    
    # Create app directory
    app_dir = install_dir / "efa_juxtaposition_app"
    app_dir.mkdir(exist_ok=True)
    
    # Download main application file
    print("⬇️  Downloading application file...")
    app_url = "https://raw.githubusercontent.com/equinor/efa_juxtaposition_analysis/main/efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py"
    app_file = app_dir / "EFA_juxtaposition_v0p9p6.py"
    
    urllib.request.urlretrieve(app_url, app_file)
    
    # Create __init__.py
    (app_dir / "__init__.py").touch()
    
    # Create launcher script
    launcher_content = '''#!/usr/bin/env python3
"""EFA Juxtaposition Analysis Launcher"""
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "efa_juxtaposition_app"
sys.path.insert(0, str(app_dir))

# Import and run the application
from EFA_juxtaposition_v0p9p6 import main

if __name__ == "__main__":
    main()
'''
    
    launcher_file = install_dir / "run_efa.py"
    launcher_file.write_text(launcher_content)
    launcher_file.chmod(0o755)
    
    print("✅ Manual setup complete!")
    print(f"\nInstallation directory: {install_dir}")
    print("\nTo run the application:")
    print(f"    cd {install_dir}")
    print("    uv run python run_efa.py")
    print("\nOr directly:")
    print(f"    uv run --directory {install_dir} python run_efa.py")
    
    return True

def create_desktop_shortcut(install_dir):
    """Create desktop shortcut (Windows only)"""
    if sys.platform != "win32":
        return
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, "EFA Juxtaposition Analysis.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{install_dir}/run_efa.py"'
        shortcut.WorkingDirectory = str(install_dir)
        shortcut.IconLocation = sys.executable
        shortcut.save()
        
        print(f"🖥️  Desktop shortcut created: {shortcut_path}")
    except ImportError:
        print("ℹ️  To create a desktop shortcut, install: pip install winshell pywin32")

def main():
    print("=" * 50)
    print("EFA Juxtaposition Analysis - Quick Installer")
    print("=" * 50)
    print()
    
    # Check prerequisites
    if not check_uv():
        sys.exit(1)
    
    print("\nChoose installation method:")
    print("1. Install as uv tool (recommended)")
    print("2. Manual setup with local files")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            if install_from_github():
                break
            else:
                print("Falling back to manual setup...")
                if manual_setup():
                    break
        elif choice == "2":
            if manual_setup():
                break
        elif choice == "3":
            print("Installation cancelled.")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
    
    print("\n🎉 Installation completed successfully!")
    print("\nFor help and documentation, visit:")
    print("https://github.com/equinor/efa_juxtaposition_analysis")

if __name__ == "__main__":
    main()