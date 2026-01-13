# EFA Juxtaposition Analysis

Geology application to quicky analyze fault juxtaposition for single faults by creating throw profiles and juxtaposition (Allan) diagrams.

## Features

- Input Petrel Fault cuttof points or Cegal fault cuttof points in Petrel points with attribute format
- Single to multiple horizon input
- Supports horizon shifting
- Generates interactive throw profiles and juxtaposition diagrams
- Session save/load capabilities
- Figure to clip-borad support and saves figure to different formats
- CSV export functionality

## Installation

### Quick Setup (Recommended)

**Option 1: Clone Repository**
If you clone this repository, you can use the automated setup scripts:

**For Windows:**
```cmd
setup.bat
```

**For Linux/macOS:**
```bash
./setup.sh
```

**Option 2: Direct Installation (No Git Required)**

Download and run the installer script:
```bash
# Download the installer
curl -sSL https://raw.githubusercontent.com/equinor/efa_juxtaposition_analysis/main/install_efa.py -o install_efa.py

# Run the installer
python install_efa.py
```

**Option 3: Install as uv Tool**
```bash
uv tool install git+https://github.com/equinor/efa_juxtaposition_analysis.git
efa-juxtaposition  # Run the application
```

These scripts will:
- Check if `uv` is installed
- Install all required dependencies automatically
- Set up the virtual environment
- Install platform-specific dependencies (Windows clipboard support, etc.)

📖 **For detailed installation options (including methods without Git), see [SETUP.md](SETUP.md)**

### Manual Installation

#### Using uv (Recommended)

This guide explains how to install python using uv, create an application folder and install dependencies for the application. If you already have installed python using uv, step 1 and 2 can be skipped.
More information abut installing python using uv can be found at the Equinor wiki. 

1. Open cmd and type or copy/paste:
   ```
   winget install --id=astral-sh.uv -e
   ```

   press 'Y' when asked. When it finishes, close the command-line interpreter window.

2. Open a new command-line interpreter window (cmd) and install the latest Python, type or copy/paste:
   ```
   uv python install
   ```

3. Navigate to c:/Appl and create application folder. If the Appl folder don't exist, create it. In command_line_interptreter (cmd), type or copy/paste:
   ```
      c:
      cd \Appl
      uv init efa_uv_app
   ```

4. Navigate into the application folder, in cmd type or copy/paste:
   ```
   cd efa_uv_app
   ```

5. Install application dependencies, in cmd type or copy/paste:
   ```
   uv add numpy pandas matplotlib scipy shapely pywin32
   ```

6. Download the application files from GitHub:
   - [EFA_juxtaposition_v0p9p6.py](./efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py)
   - [EFA_juxtaposition_launcher.bat](./efa_juxtaposition_app/EFA_juxtaposition_launcher.bat)
   - [EFA_juxtaposition_launcher_advanced.bat](./efa_juxtaposition_app/EFA_juxtaposition_launcher_advanced.bat)
   
   Copy these files into your application folder (c:\Appl\efa_uv_app\). 

## Launching the Application

### Option 1: Using Batch File (Recommended)
The application can be launched by double-clicking one of the provided batch files:
- **EFA_juxtaposition_launcher.bat** - Basic launcher with dependency checks
- **EFA_juxtaposition_launcher_advanced.bat** - Advanced launcher with detailed reporting

Both batch files will:
- Check if uv is installed
- Verify the application directory exists
- Confirm the Python file is present
- Validate that all required libraries are installed
- Launch the application if all checks pass

### Option 2: Using Command Line
Alternatively, the application can be launched using cmd. Navigate to the application directory and run:
```cmd
cd c:\Appl\efa_uv_app
uv run EFA_juxtaposition_v0p9p6.py
```

### Creating a Desktop Shortcut
You can create a shortcut to either batch file and copy it to your desktop for easy access.

### Using the Repository Setup

If you've cloned this repository and have `pyproject.toml`, you can also run:

```cmd
# Install dependencies
uv sync

# Run the application
uv run python efa_juxtaposition_app/EFA_juxtaposition_v0p9p6.py
```

Or install with Windows-specific dependencies:
```cmd
uv sync --extra windows
```

#### Installation using pip

1. Ensure Python 3.x is installed
2. Install required dependencies:
   ```bash
   pip install matplotlib pandas numpy scipy shapely pywin32
   ```
3. Run the application:
   ```bash
   python EFA_juxtaposition_v0p93_u2.py
   ```

## Usage

Launch the application and use the tabbed interface to:
- Load geological data
- Create interactive plots
- Analyze juxtaposition relationships
- Export results


## Version

**Version:** 0.93  
**Build Date:** 2025-10-10  
**Author:** John-Are Hansen (jareh@equinor.com)

## License

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see [https://www.gnu.org/licenses/](https://www.gnu.org/licenses/).

### Why GPL v3.0?

The GNU General Public License v3.0 is a **copyleft** license that ensures:

- ✅ **Freedom to use** - Anyone can use the software for any purpose
- ✅ **Freedom to study** - Source code is always available
- ✅ **Freedom to modify** - Anyone can modify the software
- ✅ **Freedom to distribute** - Anyone can distribute the original or modified versions
- ✅ **Copyleft protection** - Any derivative works must also be GPL-licensed

This guarantees that the software and all its derivatives remain free and open source forever.



## Contributing

Contributions are welcome! Since this is GPL-licensed software:

1. Fork the repository
2. Make your changes
3. Ensure your contributions are also GPL-compatible
4. Submit a pull request

All contributions will be licensed under GPL v3.0.

## Support

For questions or support, contact: jareh@equinor.com

## Copyright

Copyright (C) 2025 John-Are Hansen

This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it under certain conditions as specified in the GPL v3.0 license.