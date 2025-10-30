# EFA Juxtaposition Analysis - Setup Instructions

This document provides step-by-step instructions for cloning and setting up the EFA Juxtaposition Analysis application.

## Prerequisites

Before starting, ensure you have:
- Git installed on your system
- Internet connection for downloading dependencies

## Quick Setup (Recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/equinor/efa_juxtaposition_analysis.git
cd efa_juxtaposition_analysis
```

### 2. Run the Setup Script

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

### 3. Launch the Application

After successful setup, you can launch the application using:

**Option A: Using uv (Cross-platform)**
```bash
uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
```

**Option B: Using Batch Files (Windows)**
- Double-click `efa_juxtaposition_app/EFA_juxtaposition_launcher.bat`
- Or use the advanced launcher: `efa_juxtaposition_app/EFA_juxtaposition_launcher_advanced.bat`

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

**Copyright (C) 2025 John-Are Hansen**  
Licensed under GPL v3.0 - see LICENSE file for details