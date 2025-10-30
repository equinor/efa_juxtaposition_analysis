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

If you don't already have python installed on your system, it is reccomende to use uv for installing the application and dependencies. However, you can also use pip if this is preferred.

Installation using uv:
This guide explains how to install python using uv, create an application folder and install dependencies for the application. If you already have installad python using uv, step  1 and 2 can be skipped.
More information abut installing python using uv can be found at the Equinor wiki. 

1. Open cmd and type or copy/paste:
   ```
   winget install --id=astral-sh.uv -e
   ```

   press 'Y' when asked. When it finishes, close the command-line interpreter window.

2. Open a new command-line interpreter window (cmd) and install the latest Python, type or copy/paste:
   uv python install

3. Navigate to c:/Appl and create application folder. If the Appl folder don't exist, create it. In command_line_interptreter (cmd), type or copy/paste:
   c:
   cd Appl
   uv init efa_uv_app

4. Navigate into the application folder, in cmd type or copy/paste:
   cd efa_uv_app

5. Install application dependencies, in cmd type or copy/paste:
   uv add numpy pandas matplotlib scipy shapely

6. Downlaod the application file .py and .bat file from GitHub and copy them into your application folder.

The application can now be launched by double-clicking the .bat file. A shortcut to the .bat file can also be made, and copied to e.g. your desktop.


Installation using pip

1. Ensure Python 3.x is installed
2. Install required dependencies:
   ```bash
   pip install tkinter matplotlib pandas numpy scipy shapely pillow
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