# EFA Juxtaposition Analysis - Setup Instructions

This document provides step-by-step instructions for cloning and setting up the EFA Juxtaposition Analysis application.

## Prerequisites

Before starting, ensure you have:
- Git installed on your system
- Internet connection for downloading dependencies

## Installation Options

### Option 1: Quick Setup with Git Clone (Recommended)

#### 1. Clone the Repository

```bash
git clone https://github.com/equinor/efa_juxtaposition_analysis.git
cd efa_juxtaposition_analysis
```

#### 2. Run the Setup Script

**For Windows:**
```cmd
setup.bat
```

**For Linux/macOS:**
```bash
./setup.sh
```

The setup script will automatically:
- ✅ Check if `uv` is installed (and guide you to install it if missing)
- ✅ Create a virtual environment
- ✅ Install all required Python dependencies
- ✅ Install platform-specific dependencies (Windows clipboard support, etc.)
- ✅ Verify the installation

#### 3. Launch the Application

After successful setup, you can launch the application using:

**Option A: Using uv (Cross-platform)**
```bash
uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
```

**Option B: Using Batch Files (Windows)**
- Double-click `efa_juxtaposition_app/EFA_juxtaposition_launcher.bat`
- Or use the advanced launcher: `efa_juxtaposition_app/EFA_juxtaposition_launcher_advanced.bat`

### Option 2: Clone Repository + Install with uv

If you want to install dependencies directly with uv after cloning:

```bash
git clone https://github.com/equinor/efa_juxtaposition_analysis.git
cd efa_juxtaposition_analysis

# Install dependencies
uv sync

# Optional: include Windows-specific dependencies
uv sync --extra windows

# Run the application
uv run python efa_juxtaposition_app/EFA_juxtaposition_app.py
```

### Option 3: Direct Installation from GitHub (No Git Required)

If you don't have Git installed or prefer not to clone the repository:

#### Method A: Install as Package from GitHub
```bash
# Install directly from GitHub repository
uv add git+https://github.com/equinor/efa_juxtaposition_analysis.git

# Run the application
uv run efa-juxtaposition
```

#### Method B: Download and Extract
1. **Download the repository:**
   - Go to https://github.com/equinor/efa_juxtaposition_analysis
   - Click "Code" → "Download ZIP"
   - Extract the ZIP file to your desired location

2. **Navigate to the extracted folder:**
   ```bash
   cd efa_juxtaposition_analysis-main
   ```

3. **Install dependencies:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
   ```

### Option 4: Manual Download of Files (Minimal Setup)

If you only need the core application files:

#### 1. Create a project directory:
```bash
mkdir efa_juxtaposition
cd efa_juxtaposition
uv init .
```

#### 2. Add dependencies:
```bash
uv add numpy pandas matplotlib scipy shapely pillow
```

#### 3. Download the main Python file:
- Go to https://github.com/equinor/efa_juxtaposition_analysis/blob/main/efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
- Click "Raw" and save the file to your project directory

#### 4. Run the application:
```bash
uv run python EFA_juxtaposition_v0p9p6.py
```

### Option 5: Using uv with Remote Execution

Run the application directly from GitHub without local installation:

```bash
# Create a temporary project
uv init temp_efa_project
cd temp_efa_project

# Add dependencies
uv add numpy pandas matplotlib scipy shapely pillow

# Download and run in one step
curl -sSL https://raw.githubusercontent.com/equinor/efa_juxtaposition_analysis/main/efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py -o EFA_juxtaposition.py
uv run python EFA_juxtaposition.py
```

### Option 6: Using uv Scripts (Advanced)

Create a standalone script that can be run anywhere:

#### 1. Create a script file `run_efa.py`:
```python
#!/usr/bin/env python
"""
EFA Juxtaposition Analysis Runner
Downloads and runs the application with proper dependencies
"""
import subprocess
import sys
import urllib.request
import os

def main():
    # Ensure we have uv
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("uv is not installed. Please install it first:")
        print("Windows: winget install --id=astral-sh.uv -e")
        print("Unix: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    # Create temp directory
    os.makedirs("temp_efa", exist_ok=True)
    os.chdir("temp_efa")
    
    # Initialize project if needed
    if not os.path.exists("pyproject.toml"):
        subprocess.run(["uv", "init", "."], check=True)
        subprocess.run(["uv", "add", "numpy", "pandas", "matplotlib", "scipy", "shapely", "pillow"], check=True)
    
    # Download application if needed
    if not os.path.exists("EFA_juxtaposition.py"):
        url = "https://raw.githubusercontent.com/equinor/efa_juxtaposition_analysis/main/efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py"
        urllib.request.urlretrieve(url, "EFA_juxtaposition.py")
    
    # Run application
    subprocess.run(["uv", "run", "python", "EFA_juxtaposition.py"])

if __name__ == "__main__":
    main()
```

#### 2. Run the script:
```bash
python run_efa.py
```

### Comparison of Methods

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Git Clone** | Full repository, easy updates, includes test data | Requires Git | Developers, regular users |
| **Clone + uv sync** | Full repository with explicit dependency control | More manual steps than setup scripts | Users who want transparent installs |
| **Direct GitHub Install** | Simple one-liner | Less control over versions | Quick testing |
| **Download ZIP** | No Git required, full repository | Manual updates | Users without Git |
| **Manual Download** | Minimal footprint | Missing extras (test data, launchers) | Minimal installations |
| **Remote Execution** | No local storage | Requires internet each time | One-time usage |
| **uv Scripts** | Automated setup | More complex | Advanced users |

## Manual Setup Instructions

If you prefer to set up manually or the automated scripts don't work:

### Step 1: Install uv (if not already installed)

**Windows:**
```cmd
winget install --id=astral-sh.uv -e
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Step 2: Clone and Navigate

```bash
git clone https://github.com/equinor/efa_juxtaposition_analysis.git
cd efa_juxtaposition_analysis
```

### Step 3: Install Dependencies

**Basic installation:**
```bash
uv sync
```

**With Windows-specific features:**
```bash
uv sync --extra windows
```

**With development tools:**
```bash
uv sync --extra dev
```

**With all optional dependencies:**
```bash
uv sync --extra all
```

### Step 4: Verify Installation

Test that the application can start:
```bash
uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py --help
```

## Alternative Installation Methods

### Using pip (Not Recommended)

If you prefer to use pip instead of uv:

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   
   # Activate it:
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pillow  # For image support
   
   # Windows only (for clipboard support):
   pip install pywin32
   ```

3. **Run the application:**
   ```bash
   python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
   ```

## Troubleshooting

### Common Issues and Solutions

**1. "uv: command not found"**
- Solution: Install uv following the instructions in Step 1 above
- Make sure to restart your terminal after installation

**2. "Permission denied" on Linux/macOS**
- Solution: Make the setup script executable:
  ```bash
  chmod +x setup.sh
  ./setup.sh
  ```

**3. "Python not found"**
- Solution: Install Python first, then install uv:
  ```bash
  uv python install  # This installs the latest Python via uv
  ```

**4. Import errors when running the application**
- Solution: Ensure you're running from the project directory and using the virtual environment:
  ```bash
  cd efa_juxtaposition_analysis
  uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
  ```

**5. GUI doesn't appear**
- Solution: Ensure tkinter is available. On some Linux systems:
  ```bash
  sudo apt-get install python3-tk  # Ubuntu/Debian
  sudo yum install tkinter         # CentOS/RHEL
  ```

**6. Windows clipboard features not working**
- Solution: Install Windows-specific dependencies:
  ```bash
  uv sync --extra windows
  ```

### Getting Help

If you encounter issues not covered here:

1. Check the main [README.md](README.md) for additional information
2. Review the error messages carefully - they often contain helpful information
3. Contact support: jareh@equinor.com
4. Create an issue on the GitHub repository

## Development Setup

If you plan to contribute to the project:

1. **Fork the repository** on GitHub

2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/efa_juxtaposition_analysis.git
   cd efa_juxtaposition_analysis
   ```

3. **Install with development dependencies:**
   ```bash
   uv sync --extra dev
   ```

4. **Install pre-commit hooks (optional):**
   ```bash
   uv run pre-commit install
   ```

5. **Run tests:**
   ```bash
   uv run pytest
   ```

## Next Steps

After successful installation:

1. **Read the User Guide** in the main README.md
2. **Try the test data** included in `efa_juxtaposition_app/test_data/`
3. **Create a desktop shortcut** to the launcher for easy access
4. **Explore the features** using the tabbed interface

## System Requirements

- **Operating System:** Windows 10+, macOS 10.14+, or Linux
- **Python:** 3.8 or higher (automatically handled by uv)
- **Memory:** 4GB RAM minimum, 8GB recommended
- **Disk Space:** 500MB for application and dependencies
- **Display:** 1280x800 minimum resolution

---

**Copyright (C) 2025 Equinor ASA**  
Licensed under the MIT License - see LICENSE file for details