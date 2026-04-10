#!/usr/bin/env python3
"""
EFA Juxtaposition Analysis - fault displacement and zone juxtaposition analysis

Copyright (C) 2025 Equinor ASA

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, StringVar, IntVar, BooleanVar, colorchooser
import matplotlib.pyplot as plt
import matplotlib
# Configure matplotlib to manage figure memory better
matplotlib.rcParams['figure.max_open_warning'] = 0  # Suppress the warning
plt.ioff()  # Turn off interactive mode to prevent figure accumulation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import pandas as pd
import numpy as np
from io import StringIO
from scipy import interpolate
from shapely.geometry import Polygon
# import efa_app_functions as efa  # Functions moved to Backend section
import matplotlib.colors as mcolors
import warnings
import pickle
from PIL import Image, ImageTk
import io

# Optional Windows clipboard support
try:
    import win32clipboard
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False



class EFA_juxtaposition(tk.Tk):
    VERSION = "1.0.1"
    BUILD_DATE = "2026-02-19"
    AUTHOR = "John-Are Hansen"

    def __init__(self):
        super().__init__()
        self.title(f"EFA Juxtaposition Analysis v{self.VERSION}")
        
        # Set icon if available, otherwise continue without it
        try:
            self.iconbitmap("help_images/efa_icon.ico")
        except (FileNotFoundError, tk.TclError):
            # Icon file not found or invalid - continue without icon
            pass
        
        self.geometry("1400x900")
        self.state('zoomed')  # Maximize window on Windows
        
        # Initialize variables from both apps
        self.datadict = {}
        self.innfiles = []
        self.z_select = StringVar(value='Z')
        self.num_horizons = IntVar(value=1)
        self.plot_name = StringVar(value="Fault")
        self.width = IntVar(value=12)
        self.height = IntVar(value=6)
        self.gridlines = BooleanVar(value=False)
        self.linewidth = tk.DoubleVar(value=1.0)
        self.pointid = BooleanVar(value=False)
        self.file_format = StringVar(value='Petrel_FC')
        
        # Data processing variables
        self.ld_dict = None
        self.fv_df = None
        self.hv_df = None
        self.nfv_df = None
        self.nhv_df = None
        self.nh_list = None
        self.strike = None
        self.dip = None
        self.shift_df = None
        self.color_df = None
        self.ztype_df = None
        self.ezcolor_df = None
        self.ecolor_df = None
        self.eztype_df = None
        self.unit_xy = 'm'
        self.unit_depth = 'm'
        
        # Enhanced color and alias management from juxtaposition_app
        self.horizon_colors = {}
        self.horizon_aliases = {}
        self.zone_colors = {}
        self.zone_lithology = {
            'Undefined': "azure",
            'Good': "yellow",
            'Poor': "orange", 
            'No Res': "black",
            'SR': "red"
        }
        self.zone_names_aliases = {}
        self.zone_unit_colors = {}
        
        # Initialize legend sidebar references
        self.legend_sidebar_throw = None
        self.legend_sidebar_juxt = None
        self.legend_sidebar_scenario = None
        
        # Store current figure references for clipboard copying
        self.current_throw_fig = None
        self.current_juxt_fig = None
        self.current_scenario_fig = None
        self.current_legend_fig = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Save Session...", command=self.save_session)
        file_menu.add_command(label="Load Session...", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Export All Plots...", command=self.copy_all_plots_to_files)
        file_menu.add_separator()
        file_menu.add_command(label="Reset Application", command=self.reset_application)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        # Edit menu with clipboard options
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy Throw Plot to Clipboard", 
                             command=self.copy_throw_plot_to_clipboard)
        edit_menu.add_command(label="Copy Juxtaposition Plot to Clipboard", 
                             command=self.copy_juxt_plot_to_clipboard)
        edit_menu.add_command(label="Copy Scenario Plot to Clipboard", 
                             command=self.copy_scenario_plot_to_clipboard)
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy Legend to Clipboard", 
                             command=self.copy_legend_to_clipboard)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All Plots", command=self.refresh_all_plots)
        view_menu.add_separator()
        view_menu.add_command(label="About", command=self.show_about)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create frames for each tab - combining the best of both apps
        self.data_input_frame = ttk.Frame(self.notebook)
        self.data_manipulation_frame = ttk.Frame(self.notebook)
        self.plot_settings_frame = ttk.Frame(self.notebook)
        self.throw_profile_frame = ttk.Frame(self.notebook)
        self.juxtaposition_unit_frame = ttk.Frame(self.notebook)
        self.juxtaposition_plot_frame = ttk.Frame(self.notebook)
        self.scenario_plot_frame = ttk.Frame(self.notebook)
        self.output_tables_frame = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.data_input_frame, text='Data Input')
        self.notebook.add(self.data_manipulation_frame, text='Data Manipulation')
        self.notebook.add(self.plot_settings_frame, text='Plot Settings')
        self.notebook.add(self.throw_profile_frame, text='Throw Profile Plot')
        self.notebook.add(self.juxtaposition_unit_frame, text='Zone Juxtaposition Plot')
        self.notebook.add(self.juxtaposition_plot_frame, text='Lithology Juxtaposition Plot')
        self.notebook.add(self.scenario_plot_frame, text='Juxtaposition Scenario Plot')
        self.notebook.add(self.output_tables_frame, text='Output Tables')
        
        # Setup each tab
        self.setup_data_input_tab()
        self.setup_data_manipulation_tab()
        self.setup_plot_settings_tab()
        self.setup_throw_profile_tab()
        self.setup_juxtaposition_unit_tab()
        self.setup_juxtaposition_plot_tab()
        self.setup_scenario_plot_tab()
        self.setup_output_tables_tab()
        
        # Initialize color settings display
        self.update_color_settings_display()
        
        # Set up proper cleanup when window is closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_data_input_tab(self):
        """Enhanced data input tab combining features from both apps"""
        # Create horizontal layout
        main_frame = ttk.Frame(self.data_input_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create sidebar frame (left side)
        sidebar = ttk.Frame(main_frame, width=300)
        sidebar.pack(side='left', fill='y', padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Add a separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)
        
        # Create data display frame (right side)
        self.data_display_frame = ttk.Frame(main_frame)
        self.data_display_frame.pack(side='left', fill='both', expand=True)
        
        # Setup sidebar content
        ttk.Label(sidebar, text="Juxtaposition Analysis", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Instructions
        instructions = tk.Text(sidebar, height=3, width=40, wrap=tk.WORD)
        instructions.insert('1.0', 'Add files ordered from shallowest to deepest horizon - files need to be in "Petrel_points_w_attributes" format')
        instructions.config(state='disabled')
        instructions.pack(pady=5)
        
        # File format selection
        ttk.Label(sidebar, text="File input format:").pack(pady=5)
        file_format_options = ['Petrel_FC', 'Cegal_FC']
        ttk.Combobox(sidebar, textvariable=self.file_format, 
                    values=file_format_options, width=15).pack()
        
        # File selection buttons
        load_btn = ttk.Button(sidebar, text="Select Horizon Files", command=self.add_files)
        load_btn.pack(fill='x', pady=5)
        
        sort_btn = ttk.Button(sidebar, text="Sort File Order", command=self.edit_file_order)
        sort_btn.pack(fill='x', pady=5)
        
        # Listbox to display added datafiles
        ttk.Label(sidebar, text="Selected Files:").pack(pady=(10,5))
        self.datafiles_listbox = tk.Listbox(sidebar, height=8)
        self.datafiles_listbox.pack(fill='both', expand=True, pady=5)
        
        # Load data button
        ttk.Button(sidebar, text="Load Data to Database", 
                  command=self.load_data).pack(pady=10)
        
        # Session management buttons
        session_frame = ttk.LabelFrame(sidebar, text="Session Management")
        session_frame.pack(fill='x', pady=10)
        
        ttk.Button(session_frame, text="Save Session", 
                  command=self.save_session).pack(fill='x', padx=5, pady=2)
        ttk.Button(session_frame, text="Load Session", 
                  command=self.load_session).pack(fill='x', padx=5, pady=2)
        
        # Setup data display area
        ttk.Label(self.data_display_frame, 
                 text='Data Preview - Loaded files will be displayed here',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Create scrollable text widget for data display
        data_text_frame = ttk.Frame(self.data_display_frame)
        data_text_frame.pack(fill='both', expand=True, pady=10)
        
        self.data_text = tk.Text(data_text_frame, wrap=tk.WORD)
        data_scrollbar = ttk.Scrollbar(data_text_frame, orient='vertical', command=self.data_text.yview)
        self.data_text.configure(yscrollcommand=data_scrollbar.set)
        
        self.data_text.pack(side='left', fill='both', expand=True)
        data_scrollbar.pack(side='right', fill='y')
    
    def add_files(self):
        """Enhanced file selection from juxtaposition_app"""
        file_paths = filedialog.askopenfilenames(
            title="Select Horizon Data Files",
            filetypes=(("All Files", "*.*"), ("CSV Files", "*.csv"), ("Text Files", "*.txt"))
        )
        for file_path in file_paths:
            self.innfiles.append(file_path)
        
        # Update the listbox
        self.datafiles_listbox.delete(0, tk.END)
        for fname in self.innfiles:
            display_name = fname.split('/')[-1] if '/' in fname else fname.split('\\')[-1]
            self.datafiles_listbox.insert(tk.END, display_name)
    
    def edit_file_order(self):
        """Enhanced file order editing from juxtaposition_app"""
        if not self.innfiles:
            messagebox.showwarning("Edit Files", "No files loaded to edit.")
            return

        edit_win = tk.Toplevel(self)
        edit_win.title("Edit File Order")
        try:
            edit_win.iconbitmap("help_images/efa_icon.ico")
        except (FileNotFoundError, tk.TclError):
            # Icon file not found or invalid - continue without icon
            pass
        edit_win.geometry("400x400")

        listbox = tk.Listbox(edit_win, selectmode=tk.SINGLE)
        listbox.pack(fill='both', expand=True, padx=10, pady=10)

        for fname in self.innfiles:
            display_name = fname.split('/')[-1] if '/' in fname else fname.split('\\')[-1]
            listbox.insert(tk.END, display_name)

        def move_up():
            sel = listbox.curselection()
            if not sel or sel[0] == 0:
                return
            idx = sel[0]
            # Move in both listbox and innfiles
            fname = self.innfiles.pop(idx)
            self.innfiles.insert(idx-1, fname)
            # Update listbox
            display_name = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx-1, display_name)
            listbox.selection_set(idx-1)

        def move_down():
            sel = listbox.curselection()
            if not sel or sel[0] == listbox.size()-1:
                return
            idx = sel[0]
            # Move in both listbox and innfiles
            fname = self.innfiles.pop(idx)
            self.innfiles.insert(idx+1, fname)
            # Update listbox
            display_name = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx+1, display_name)
            listbox.selection_set(idx+1)

        def remove_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            self.innfiles.pop(idx)
            listbox.delete(idx)

        def apply_changes():
            self.datafiles_listbox.delete(0, tk.END)
            for fname in self.innfiles:
                display_name = fname.split('/')[-1] if '/' in fname else fname.split('\\')[-1]
                self.datafiles_listbox.insert(tk.END, display_name)
            edit_win.destroy()

        btn_frame = ttk.Frame(edit_win)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="Move Up", command=move_up).pack(side='left', expand=True, fill='x', padx=2)
        ttk.Button(btn_frame, text="Move Down", command=move_down).pack(side='left', expand=True, fill='x', padx=2)
        ttk.Button(btn_frame, text="Remove", command=remove_selected).pack(side='left', expand=True, fill='x', padx=2)
        ttk.Button(edit_win, text="Apply Changes", command=apply_changes).pack(pady=5)
    
    def load_data(self):
        """Enhanced data loading from juxtaposition_app"""
        if not self.innfiles:
            messagebox.showwarning("Load Data", "No files selected.")
            return

        self.datadict.clear()
        # Following reads data in Petrel points with attributes format
        for file_path in self.innfiles:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                
                # Parse the file similar to the Streamlit version
                data_str = StringIO(content)
                lines = data_str.readlines()
                
                # Get unit_xy from second line, example from Petrel export: line 2: # Unit in X and Y direction: m
                if len(lines) > 1 and '# Unit in X and Y direction' in lines[1]:
                    unit_line = lines[1]
                    if 'm' in unit_line:
                        self.unit_xy = 'm'
                    elif 'ft' in unit_line:
                        self.unit_xy = 'ft'
                    elif 'ftUS' in unit_line:
                        self.unit_xy = 'ftUS'

                # Get unit_depth from third line, example from Petrel export: line 3:# Unit in depth: m: m
                if len(lines) > 2 and '# Unit in depth' in lines[2]:
                    unit_line = lines[2]
                    if 'm' in unit_line:
                        self.unit_depth = 'm'
                    elif 'ft' in unit_line:
                        self.unit_depth = 'ft'
                    elif 'ftUS' in unit_line:
                        self.unit_depth = 'ftUS'

                # Find header boundaries
                bh = eh = None
                for index, line in enumerate(lines):
                    if line.strip() == 'BEGIN HEADER':
                        bh = index
                    if line.strip() == 'END HEADER':
                        eh = index
                        break
                
                if bh is not None and eh is not None:
                    # Extract header
                    head = []
                    for i in range(eh - bh - 1):
                        hline = lines[bh + i + 1]
                        if len(hline.split(',')) == 1:
                            head.append(hline.strip())
                        else:
                            head.append(hline.split(',')[1].strip())
                    
                    # Read data
                    data = pd.read_csv(StringIO(content), sep=r'\s+', 
                                     skiprows=eh + 1, names=head)
                    
                    # Store in datadict
                    filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                    if filename in self.datadict:
                        filename = filename + '_duplicate'
                    self.datadict[filename] = data
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}:\n{e}")
                return

        # Display loaded data
        self.display_loaded_data()
        #messagebox.showinfo("Success", f"Successfully loaded {len(self.datadict)} files.")
    
    def display_loaded_data(self):
        """Display loaded data in the text widget"""
        self.data_text.delete('1.0', tk.END)
        
        for filename, data in self.datadict.items():
            self.data_text.insert(tk.END, f"\n{filename} (Shape: {data.shape})\n")
            self.data_text.insert(tk.END, "="*60 + "\n")
            self.data_text.insert(tk.END, data.head().to_string())
            self.data_text.insert(tk.END, "\n\n")
    
    def setup_data_manipulation_tab(self):
        """Enhanced data manipulation tab from juxtaposition_app"""
        # Create horizontal layout
        main_frame = ttk.Frame(self.data_manipulation_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create sidebar frame (left side)
        sidebar = ttk.Frame(main_frame, width=250)
        sidebar.pack(side='left', fill='y', padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Add a separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)
        
        # Create main area (right side) with sub-tabs
        self.manipulation_display_frame = ttk.Frame(main_frame)
        self.manipulation_display_frame.pack(side='left', fill='both', expand=True)
        
        # Setup sidebar content
        ttk.Label(sidebar, text="Data Manipulation", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Z-value selection
        ttk.Label(sidebar, text="Z-value field:").pack(pady=5)
        z_options = ['Z', 'TWT auto', 'Depth 1']
        ttk.Combobox(sidebar, textvariable=self.z_select, 
                    values=z_options, width=15).pack()
        
        # Data processing buttons
        ttk.Button(sidebar, text="Convert to Length/Depth", 
                  command=self.xyz_to_length_depth).pack(fill='x', pady=5)
        
        ttk.Button(sidebar, text="Edit Horizon Shift", 
                  command=self.horizon_shift).pack(fill='x', pady=5)
        
        ttk.Button(sidebar, text="Execute Shift", 
                  command=self.execute_shift).pack(fill='x', pady=5)
        
        # Create sub-notebook for data display tabs
        self.data_sub_notebook = ttk.Notebook(self.manipulation_display_frame)
        self.data_sub_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create frames for each sub-tab
        self.length_depth_frame = ttk.Frame(self.data_sub_notebook)
        self.shifted_data_frame = ttk.Frame(self.data_sub_notebook)
        self.mapped_data_frame = ttk.Frame(self.data_sub_notebook)
        self.qc_plot_frame = ttk.Frame(self.data_sub_notebook)
        
        # Add sub-tabs to notebook
        self.data_sub_notebook.add(self.length_depth_frame, text='Length/Depth Data')
        self.data_sub_notebook.add(self.shifted_data_frame, text='Shifted Data')
        self.data_sub_notebook.add(self.mapped_data_frame, text='Mapped Data')
        self.data_sub_notebook.add(self.qc_plot_frame, text='QC Plot')
        
        # Setup each sub-tab content
        self.setup_length_depth_tab()
        self.setup_shifted_data_tab()
        self.setup_mapped_data_tab()
        self.setup_qc_plot_tab()

    def setup_length_depth_tab(self):
        """Setup tab 1: Display fv_df and hv_df from xyz_to_length_depth"""
        # Create main container with label
        ttk.Label(self.length_depth_frame, text="Length/Depth Converted Data", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Create scrollable container
        self.ld_scroll_frame = ttk.Frame(self.length_depth_frame)
        self.ld_scroll_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Initial message
        self.ld_initial_label = ttk.Label(self.ld_scroll_frame, 
                                         text="Run 'Convert to Length/Depth' to see results here")
        self.ld_initial_label.pack(pady=50)
    
    def setup_shifted_data_tab(self):
        """Setup tab 2: Display nfv_df and nhv_df from execute_shift"""
        # Create main container with label
        ttk.Label(self.shifted_data_frame, text="Horizon Shifted Data", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Create scrollable container
        self.shifted_scroll_frame = ttk.Frame(self.shifted_data_frame)
        self.shifted_scroll_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Initial message
        self.shifted_initial_label = ttk.Label(self.shifted_scroll_frame, 
                                              text="Run 'Execute Shift' to see results here")
        self.shifted_initial_label.pack(pady=50)
    
    def setup_mapped_data_tab(self):
        """Setup tab 3: Display original mapped data from ld_dict"""
        # Create main container with label
        ttk.Label(self.mapped_data_frame, text="Original Mapped Data", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Create scrollable container
        self.mapped_scroll_frame = ttk.Frame(self.mapped_data_frame)
        self.mapped_scroll_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Initial message
        self.mapped_initial_label = ttk.Label(self.mapped_scroll_frame, 
                                             text="Run 'Convert to Length/Depth' to see mapped data here")
        self.mapped_initial_label.pack(pady=50)
    
    def setup_qc_plot_tab(self):
        """Setup tab 4: QC Plot placeholder"""
        # Create main container with label
        ttk.Label(self.qc_plot_frame, text="Lithology Control Plot", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Placeholder for QC plot
        #self.qc_plot_placeholder = ttk.Label(self.qc_plot_frame, 
                                            #text="QC Plot will be displayed here after processing")
        #self.qc_plot_placeholder.pack(pady=50)
        


    def setup_qc_plot(self):
        """Generate QC plot and display in qc_plot_frame"""
        try:
            # Check prerequisites
            if not hasattr(self, 'ld_dict') or self.ld_dict is None:
                messagebox.showwarning("Warning", "No length/depth data available. Please convert data first.")
                return
            
            # Clear ALL previous widgets from the frame
            print("Clearing previous QC plot...")
            for widget in self.qc_plot_frame.winfo_children():
                widget.destroy()
            
            # Generate QC plot figure
            print("Generating QC plot...")
            fig_qc = self.qc_plot_method(title='Quality Control Plot')
            print(f"QC plot generated, figure type: {type(fig_qc)}")
            
            # Create canvas and display in frame
            print("Creating canvas...")
            canvas = FigureCanvasTkAgg(fig_qc, master=self.qc_plot_frame)
            print("Drawing canvas...")
            canvas.draw()
            print("Packing canvas...")
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            print("QC plot displayed successfully!")
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Error in setup_qc_plot: {error_detail}")
            messagebox.showerror("Error", f"Failed to display QC plot: {str(e)}\n\nSee console for details.")

    def xyz_to_length_depth(self):
        """Convert XYZ data to length/depth format"""
        if not self.datadict:
            messagebox.showwarning("Warning", "No horizon files loaded!")
            return
        
        try:
            # Process horizons using efa functions
            self.ld_dict, self.strike, self.dip = xyz2ld(self.datadict, z=self.z_select.get(), data_format=self.file_format.get())
            #self.fv_df, self.hv_df = ld_res2df(self.ld_dict)
            self.fv_df, self.hv_df = ld_org2df(self.ld_dict) # Added new interpolation routine for testing
            
            # Setup horizon shift df - preserve existing shift values if they exist
            if self.shift_df is None or self.shift_df.empty:
                # Create new shift table only if none exists
                self.shift_df = horizon_shift_input(self.datadict)
                self.shift_df['sh1'] = 0.0  # set first column to 0 as numeric
            else:
                # Shift table already exists - preserve it and update only if new horizons were added
                existing_shift_df = self.shift_df.copy()
                new_shift_df = horizon_shift_input(self.datadict)
                
                # Preserve existing shift values for horizons that still exist
                for horizon in existing_shift_df.index:
                    if horizon in new_shift_df.index:
                        # Copy all shift values from existing table
                        for col in existing_shift_df.columns:
                            if col in new_shift_df.columns:
                                new_shift_df.loc[horizon, col] = existing_shift_df.loc[horizon, col]
                
                # Update with the merged shift table
                self.shift_df = new_shift_df
                self.shift_df['sh1'] = self.shift_df['sh1'].fillna(0.0)  # ensure sh1 is numeric
            
            # Display results in tab 1 and tab 3
            self.display_length_depth_results()
            self.display_mapped_data_results()
            # display qc plot
            self.setup_qc_plot()
            
            messagebox.showinfo("Success", "Data converted to length/depth format!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert data: {str(e)}")
    
    def display_length_depth_results(self):
        """Display fv_df and hv_df in tab 1 (Length/Depth Data) with color highlighting"""
        # Clear previous widgets
        for widget in self.ld_scroll_frame.winfo_children():
            widget.destroy()
        
        if self.fv_df is not None or self.hv_df is not None:
            # Create container for both datasets
            container = ttk.Frame(self.ld_scroll_frame)
            container.pack(fill='both', expand=True)
            
            # Add informational label
            info_label = ttk.Label(container, 
                                 text="Color coding: Green = Correct depth order, Red = Out of order across horizons in row, Orange = NaN values",
                                 font=('Arial', 9), foreground='blue')
            info_label.pack(pady=5)
            
            # Display footwall data with styling
            if self.fv_df is not None:
                create_styled_text_widget(container, self.fv_df, "Footwall Data (FW)")
            
            # Display hangingwall data with styling
            if self.hv_df is not None:
                create_styled_text_widget(container, self.hv_df, "Hanging wall Data (HW)")
        else:
            ttk.Label(self.ld_scroll_frame, text="No length/depth data available").pack(pady=50)
    
    def display_shifted_data_results(self):
        """Display nfv_df and nhv_df in tab 2 (Shifted Data) with color highlighting"""
        # Clear previous widgets
        for widget in self.shifted_scroll_frame.winfo_children():
            widget.destroy()
        
        if self.nfv_df is not None or self.nhv_df is not None:
            # Create container for both datasets
            container = ttk.Frame(self.shifted_scroll_frame)
            container.pack(fill='both', expand=True)
            
            # Add informational label
            info_label = ttk.Label(container, 
                                 text="Color coding: Green = Correct depth order, Red = Out of order across horizons in row, Orange = NaN values",
                                 font=('Arial', 9), foreground='blue')
            info_label.pack(pady=5)
            
            # Display shifted footwall data with styling
            if self.nfv_df is not None:
                create_styled_text_widget(container, self.nfv_df, "Shifted Footwall Data (FW)")
            
            # Display shifted hangingwall data with styling
            if self.nhv_df is not None:
                create_styled_text_widget(container, self.nhv_df, "Shifted Hanging wall Data (HW)")
        else:
            ttk.Label(self.shifted_scroll_frame, text="No shifted data available").pack(pady=50)
    
    def display_mapped_data_results(self):
        """Display original mapped data from ld_dict in tab 3 (Mapped Data)"""
        # Clear previous widgets
        for widget in self.mapped_scroll_frame.winfo_children():
            widget.destroy()
        
        if self.ld_dict is not None:
            # Create container for mapped data
            container = ttk.Frame(self.mapped_scroll_frame)
            container.pack(fill='both', expand=True)
            
            # Create text widget with scrollbars to display ld_dict
            mapped_frame = ttk.LabelFrame(container, text="Complete ld_dict Contents - All Data")
            mapped_frame.pack(fill='both', expand=True, padx=5, pady=5)
            
            text_frame = ttk.Frame(mapped_frame)
            text_frame.pack(fill='both', expand=True, padx=5, pady=5)
            
            text_widget = tk.Text(text_frame, height=20, wrap=tk.NONE, font=('Courier', 9))
            scrollbar_y = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
            scrollbar_x = ttk.Scrollbar(text_frame, orient='horizontal', command=text_widget.xview)
            text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
            
            # Recursive function to display all data
            def format_data_recursive(data, prefix="", level=0):
                """Recursively format all data types in the dictionary"""
                result = ""
                indent = "  " * level
                
                if isinstance(data, dict):
                    result += f"{indent}{prefix}Dictionary with {len(data)} items:\n"
                    for key, value in data.items():
                        result += f"{indent}├─ Key: '{key}'\n"
                        if isinstance(value, pd.DataFrame):
                            result += f"{indent}│  Type: DataFrame, Shape: {value.shape}\n"
                            result += f"{indent}│  Columns: {list(value.columns)}\n"
                            result += f"{indent}│  Data:\n"
                            # Add DataFrame content with proper indentation
                            df_lines = value.to_string().split('\n')
                            for df_line in df_lines:
                                result += f"{indent}│    {df_line}\n"
                            result += f"{indent}│\n"
                        elif isinstance(value, dict):
                            result += format_data_recursive(value, f"Sub-dictionary '{key}': ", level + 1)
                        elif isinstance(value, (list, tuple)):
                            result += f"{indent}│  Type: {type(value).__name__}, Length: {len(value)}\n"
                            result += f"{indent}│  Contents: {value}\n"
                        elif isinstance(value, np.ndarray):
                            result += f"{indent}│  Type: NumPy Array, Shape: {value.shape}, dtype: {value.dtype}\n"
                            result += f"{indent}│  Data:\n{indent}│    {value}\n"
                        else:
                            result += f"{indent}│  Type: {type(value).__name__}\n"
                            result += f"{indent}│  Value: {value}\n"
                        result += f"{indent}│\n"
                elif isinstance(data, pd.DataFrame):
                    result += f"{indent}{prefix}DataFrame, Shape: {data.shape}\n"
                    result += f"{indent}Columns: {list(data.columns)}\n"
                    result += f"{indent}Data:\n"
                    df_lines = data.to_string().split('\n')
                    for df_line in df_lines:
                        result += f"{indent}  {df_line}\n"
                elif isinstance(data, (list, tuple)):
                    result += f"{indent}{prefix}{type(data).__name__}, Length: {len(data)}\n"
                    result += f"{indent}Contents: {data}\n"
                elif isinstance(data, np.ndarray):
                    result += f"{indent}{prefix}NumPy Array, Shape: {data.shape}, dtype: {data.dtype}\n"
                    result += f"{indent}Data:\n{indent}  {data}\n"
                else:
                    result += f"{indent}{prefix}{type(data).__name__}: {data}\n"
                
                return result
            
            # Format ld_dict for display with complete data
            dict_str = "=== COMPLETE LD_DICT CONTENTS ===\n"
            dict_str += f"Total top-level keys: {len(self.ld_dict)}\n\n"
            
            for i, (key, value) in enumerate(self.ld_dict.items(), 1):
                dict_str += f"[{i}] TOP-LEVEL KEY: '{key}'\n"
                dict_str += "=" * 60 + "\n"
                dict_str += format_data_recursive(value, f"", 0)
                dict_str += "=" * 60 + "\n\n"
            
            text_widget.insert('end', dict_str)
            text_widget.config(state='disabled')
            
            text_widget.grid(row=0, column=0, sticky='nsew')
            scrollbar_y.grid(row=0, column=1, sticky='ns')
            scrollbar_x.grid(row=1, column=0, sticky='ew')
            text_frame.grid_rowconfigure(0, weight=1)
            text_frame.grid_columnconfigure(0, weight=1)
        else:
            ttk.Label(self.mapped_scroll_frame, text="No mapped data available").pack(pady=50)
    
    def horizon_shift(self):
        """Enhanced horizon shift editor from juxtaposition_app"""
        if self.shift_df is None:
            messagebox.showwarning("Warning", "No shift DataFrame available. Please run length/depth conversion first.")
            return

        win = tk.Toplevel(self)
        win.title("Horizon Shift Settings")
        try:
            win.iconbitmap("help_images/efa_icon.ico")
        except (FileNotFoundError, tk.TclError):
            # Icon file not found or invalid - continue without icon
            pass
        win.geometry("800x500")

        frame = ttk.Frame(win)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Add index as a column for display
        display_df = self.shift_df.copy()
        display_df.insert(0, "Index", display_df.index)

        cols = list(display_df.columns)
        tree = ttk.Treeview(frame, columns=cols, show='headings', selectmode='browse')
        
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # Insert data with original index as iid
        for idx, row in display_df.iterrows():
            tree.insert('', 'end', iid=str(idx), values=list(row))
        
        tree.pack(fill='both', expand=True)

        # Add entry widgets for editing
        edit_frame = ttk.Frame(win)
        edit_frame.pack(fill='x', pady=5)
        
        entry_vars = [StringVar() for _ in cols]
        entries = []
        
        for i, col in enumerate(cols):
            ttk.Label(edit_frame, text=col).grid(row=0, column=i, padx=2)
            e = ttk.Entry(edit_frame, textvariable=entry_vars[i], width=12)
            e.grid(row=1, column=i, padx=2)
            entries.append(e)
            if col == "Index":
                e.config(state='readonly')

        def on_select(event):
            selected = tree.selection()
            if selected:
                values = tree.item(selected[0], 'values')
                for i, val in enumerate(values):
                    entry_vars[i].set(val)

        tree.bind('<<TreeviewSelect>>', on_select)

        def update_row():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select Row", "Please select a row to update.")
                return
            new_values = [v.get() for v in entry_vars]
            new_values[0] = tree.item(selected[0], 'values')[0]  # Keep original index
            tree.item(selected[0], values=new_values)

        ttk.Button(edit_frame, text="Update Row", command=update_row).grid(row=2, column=0, columnspan=len(cols), pady=5)

        def save_changes():
            # Update self.shift_df from the Treeview
            new_data = []
            new_indices = []
            for iid in tree.get_children():
                row = tree.item(iid)['values']
                new_indices.append(row[0])
                # Convert string values to proper numeric types or NaN
                row_data = []
                for val in row[1:]:  # Exclude the Index column
                    if val == '' or val is None:
                        row_data.append(np.nan)
                    else:
                        try:
                            row_data.append(float(val))
                        except (ValueError, TypeError):
                            row_data.append(np.nan)
                new_data.append(row_data)
            
            self.shift_df = pd.DataFrame(new_data, columns=cols[1:], index=new_indices)
            messagebox.showinfo("Saved", "Horizon shift settings updated.")
            win.destroy()

        ttk.Button(win, text="Save Changes", command=save_changes).pack(pady=10)
    
    def execute_shift(self):
        """Execute horizon shifting"""
        if self.shift_df is None:
            messagebox.showwarning("Warning", "No shift DataFrame available. Please run length/depth conversion first.")
            return
        
        try:
            # Execute horizon shift using the efa function
            #print('fv_df', self.fv_df)
            #print('hv_df', self.hv_df)
            #print('shift_df', self.shift_df)
            self.nfv_df, self.nhv_df, self.nh_list = horizon_shift_execute_v2(self.fv_df, self.hv_df, self.shift_df)
            
            # Initialize color and alias dictionaries
            for nh in self.nh_list:
                if nh not in self.horizon_colors:
                    self.horizon_colors[nh] = '#000000'
                if nh not in self.horizon_aliases:
                    self.horizon_aliases[nh] = nh
            
            # Create zone names - preserve existing aliases if they exist
            # First, get the current zone names from horizons
            current_zones = []
            for i in range(len(self.nh_list)-1):
                zone_name = f"{self.nh_list[i]}-{self.nh_list[i+1]}"
                current_zones.append(zone_name)
            
            # Remove old zones that no longer exist
            zones_to_remove = [zone for zone in self.zone_names_aliases.keys() if zone not in current_zones]
            for zone in zones_to_remove:
                if zone in self.zone_names_aliases:
                    del self.zone_names_aliases[zone]
                if zone in self.zone_colors:
                    del self.zone_colors[zone]
            
            # Add new zones, preserving existing aliases
            for zone_name in current_zones:
                if zone_name not in self.zone_names_aliases:
                    self.zone_names_aliases[zone_name] = zone_name  # Default alias is the zone name
                # Initialize zone color to default 'Undefined' if not already set
                if zone_name not in self.zone_colors:
                    self.zone_colors[zone_name] = self.zone_lithology.get('Undefined', '#CCCCCC')
            
            # Sort zone_names_aliases to match the order of zones in nh_list
            sorted_zone_aliases = {}
            sorted_zone_colors = {}
            for zone_name in current_zones:
                if zone_name in self.zone_names_aliases:
                    sorted_zone_aliases[zone_name] = self.zone_names_aliases[zone_name]
                if zone_name in self.zone_colors:
                    sorted_zone_colors[zone_name] = self.zone_colors[zone_name]
            
            # Replace the dictionaries with sorted versions
            self.zone_names_aliases = sorted_zone_aliases
            self.zone_colors = sorted_zone_colors
            
            # Display updated results in tab 2
            self.display_shifted_data_results()
            
            # Update color settings display in plot tab
            self.update_color_settings_display()
            
            messagebox.showinfo("Success", "Horizon shift executed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to execute horizon shift: {str(e)}")
    

    
    def setup_plot_settings_tab(self):
        """Enhanced plot settings tab"""
        # Create horizontal layout
        main_frame = ttk.Frame(self.plot_settings_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create sidebar frame (left side)
        sidebar = ttk.Frame(main_frame, width=250)
        sidebar.pack(side='left', fill='y', padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Add a separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)
        
        # Create settings area (right side)
        settings_area = ttk.Frame(main_frame)
        settings_area.pack(side='left', fill='both', expand=True)
        
        # Setup sidebar content
        ttk.Label(sidebar, text="Plot Settings", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Plot name input
        ttk.Label(sidebar, text="Plot name:").pack(pady=5)
        ttk.Entry(sidebar, textvariable=self.plot_name, width=25).pack(pady=5)
        
        # Generate plots button
        ttk.Button(sidebar, text="Generate All Plots", 
                  command=self.generate_plots).pack(fill='x', pady=10)
        
        # Setup settings area
        ttk.Label(settings_area, text="Plot Configuration", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Plot settings frame
        settings_frame = ttk.LabelFrame(settings_area, text="Plot Dimensions & Style")
        settings_frame.pack(fill='x', padx=10, pady=10)
        
        # Width and height sliders
        ttk.Label(settings_frame, text="Plot width:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Scale(settings_frame, from_=1, to=25, variable=self.width, orient='horizontal').grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(settings_frame, textvariable=self.width).grid(row=0, column=2, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Plot height:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Scale(settings_frame, from_=1, to=25, variable=self.height, orient='horizontal').grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(settings_frame, textvariable=self.height).grid(row=1, column=2, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Line width:").grid(row=2, column=0, sticky='w', padx=5, pady=2)
        ttk.Scale(settings_frame, from_=0.1, to=2.0, variable=self.linewidth, orient='horizontal').grid(row=2, column=1, sticky='ew', padx=5, pady=2)
        ttk.Label(settings_frame, textvariable=self.linewidth).grid(row=2, column=2, padx=5, pady=2)
        
        # Checkboxes
        #ttk.Checkbutton(settings_frame, text="Gridlines", variable=self.gridlines).grid(row=3, column=0, sticky='w', padx=5, pady=2)
        #ttk.Checkbutton(settings_frame, text="Display point ID", variable=self.pointid).grid(row=3, column=1, sticky='w', padx=5, pady=2)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Color settings display area
        self.color_settings_frame = ttk.LabelFrame(settings_area, text="Horizon & Zone Settings")
        self.color_settings_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create scrollable frame for color settings
        self.color_canvas = tk.Canvas(self.color_settings_frame)
        self.color_scrollbar = ttk.Scrollbar(self.color_settings_frame, orient="vertical", command=self.color_canvas.yview)
        self.color_scrollable_frame = ttk.Frame(self.color_canvas)
        
        self.color_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.color_canvas.configure(scrollregion=self.color_canvas.bbox("all"))
        )
        
        self.color_canvas.create_window((0, 0), window=self.color_scrollable_frame, anchor="nw")
        self.color_canvas.configure(yscrollcommand=self.color_scrollbar.set)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.color_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.color_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.color_canvas.pack(side="left", fill="both", expand=True)
        self.color_scrollbar.pack(side="right", fill="y")
        
        # Initial message
        self.initial_message_label = ttk.Label(self.color_scrollable_frame, 
                 text="Execute horizon shift first, then configure colors and generate plots.")
        self.initial_message_label.pack(pady=20)
    
    def update_color_settings_display(self):
        """Update the color settings display with inline editing capabilities"""
        # Clear existing widgets
        for widget in self.color_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.nh_list:
            # More informative initial message
            message_frame = ttk.Frame(self.color_scrollable_frame)
            message_frame.pack(pady=20, padx=10, fill='x')
            
            ttk.Label(message_frame, text="Setup Steps:", font=('Arial', 10, 'bold')).pack(anchor='w')
            ttk.Label(message_frame, text="1. Load horizon files in 'Data Input' tab").pack(anchor='w', padx=20)
            ttk.Label(message_frame, text="2. Run 'XYZ to Length/Depth' in 'Data Manipulation' tab").pack(anchor='w', padx=20)
            ttk.Label(message_frame, text="3. Execute 'Horizon Shift' in 'Data Manipulation' tab").pack(anchor='w', padx=20)
            ttk.Label(message_frame, text="4. Configure horizon colors and zone lithology here").pack(anchor='w', padx=20)
            ttk.Label(message_frame, text="5. Generate plots in new tabs").pack(anchor='w', padx=20)
            
            return
            
        # Horizon Colors Section
        horizon_frame = ttk.LabelFrame(self.color_scrollable_frame, text="Horizon Aliases & Colors")
        horizon_frame.pack(fill='x', padx=5, pady=5)
        
        self.horizon_alias_vars = {}
        self.horizon_color_vars = {}
        
        for i, horizon in enumerate(self.nh_list):
            row_frame = ttk.Frame(horizon_frame)
            row_frame.pack(fill='x', padx=5, pady=2)
            
            # Horizon name
            ttk.Label(row_frame, text=horizon[:30], width=30).pack(side='left', padx=2)
            
            # Alias entry
            alias_var = StringVar(value=self.horizon_aliases.get(horizon, horizon))
            self.horizon_alias_vars[horizon] = alias_var
            alias_entry = ttk.Entry(row_frame, textvariable=alias_var, width=20)
            alias_entry.pack(side='left', padx=2)
            alias_entry.bind('<FocusOut>', lambda e, h=horizon: self.update_horizon_alias(h))
            alias_entry.bind('<Return>', lambda e, h=horizon: self.update_horizon_alias(h))
            
            # Color button
            color = self.horizon_colors.get(horizon, '#000000')
            color_var = StringVar(value=color)
            self.horizon_color_vars[horizon] = color_var
            
            color_btn = tk.Button(row_frame, width=3, relief='raised', bg=color)
            color_btn.pack(side='left', padx=2)
            
            def make_horizon_color_callback(h=horizon, v=color_var, b=color_btn):
                def callback():
                    current_color = v.get()
                    # Use a bright blue default if current color is too dark (like black)
                    display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#4A90E2'
                    chosen = colorchooser.askcolor(color=display_color, title=f"Choose color for {h}")[1]
                    if chosen:
                        v.set(chosen)
                        self.horizon_colors[h] = chosen
                        b.config(bg=chosen, activebackground=chosen)
                        self.setup_legend_plot()  # Update legend immediately
                return callback
            
            color_btn.config(command=make_horizon_color_callback())
            
            # Color hex display
            ttk.Label(row_frame, textvariable=color_var, width=8, font=('Courier', 8)).pack(side='left', padx=2)
        
        # Zone Lithology Section
        if self.zone_names_aliases:
            zone_frame = ttk.LabelFrame(self.color_scrollable_frame, text="Zone Aliases, Lithology & Colors")
            zone_frame.pack(fill='x', padx=5, pady=5)
            
            self.zone_alias_vars = {}
            self.zone_lithology_vars = {}
            self.zone_unit_color_vars = {}
            
            lithology_options = list(self.zone_lithology.keys())
            
            for zone in self.zone_names_aliases.keys():
                row_frame = ttk.Frame(zone_frame)
                row_frame.pack(fill='x', padx=5, pady=2)
                
                # Zone name
                ttk.Label(row_frame, text=zone[:30], width=40).pack(side='left', padx=2)
                
                # Alias entry
                alias_var = StringVar(value=self.zone_names_aliases.get(zone, zone))
                self.zone_alias_vars[zone] = alias_var
                alias_entry = ttk.Entry(row_frame, textvariable=alias_var, width=20)
                alias_entry.pack(side='left', padx=2)
                alias_entry.bind('<FocusOut>', lambda e, z=zone: self.update_zone_alias(z))
                alias_entry.bind('<Return>', lambda e, z=zone: self.update_zone_alias(z))
                
                # Lithology combobox
                current_lithology = 'Undefined'
                for lith, color in self.zone_lithology.items():
                    if self.zone_colors.get(zone, None) == color:
                        current_lithology = lith
                        break
                        
                lithology_var = StringVar(value=current_lithology)
                self.zone_lithology_vars[zone] = lithology_var
                combo = ttk.Combobox(row_frame, textvariable=lithology_var, values=lithology_options, width=12)
                combo.pack(side='left', padx=2)
                combo.bind('<<ComboboxSelected>>', lambda e, z=zone: self.update_zone_lithology(z))
                
                # Color button - uses zone alias as key in self.zone_unit_colors
                zone_alias = self.zone_names_aliases.get(zone, zone)
                color = self.zone_unit_colors.get(zone_alias, '#ffffff')
                color_var = StringVar(value=color)
                self.zone_unit_color_vars[zone] = color_var
                
                color_btn = tk.Button(row_frame, width=3, relief='raised', bg=color)
                color_btn.pack(side='left', padx=2)
                
                def make_zone_color_callback(z=zone, v=color_var, b=color_btn):
                    def callback():
                        current_color = v.get()
                        # Use a bright color default if current color is too dark
                        display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#ffffff'
                        chosen = colorchooser.askcolor(color=display_color, title=f"Choose color for {z}")[1]
                        if chosen:
                            v.set(chosen)
                            # Store using zone alias as key
                            zone_alias = self.zone_names_aliases.get(z, z)
                            self.zone_unit_colors[zone_alias] = chosen
                            b.config(bg=chosen, activebackground=chosen)
                            self.setup_legend_plot()  # Update legend immediately
                    return callback
                
                color_btn.config(command=make_zone_color_callback())
                
                # Color hex display
                ttk.Label(row_frame, textvariable=color_var, width=8, font=('Courier', 8)).pack(side='left', padx=2)
        
        # Add horizontal lines section
        line_frame = ttk.LabelFrame(self.color_scrollable_frame, text="Horizontal Lines Settings")
        line_frame.pack(fill='x', padx=5, pady=5)
        
        # Add placeholder content inside the frame
        info_label = ttk.Label(line_frame, text="Add horizontal reference lines to display on plots")
        info_label.pack(padx=10, pady=5)

        # Add text entry for line name, followed by number entry for line elevation and store in varialbes
        # Add name and elevation inputs for horizontal lines 1
        line_input_frame = ttk.Frame(line_frame)
        line_input_frame.pack(fill='x', padx=10, pady=5)

        # Line name label and entry
        ttk.Label(line_input_frame, text="Name:").pack(side='left', padx=(0, 5))
        if not hasattr(self, 'hline_name_var'):
            self.hline_name_var = StringVar(value="")
        line_name_entry = ttk.Entry(line_input_frame, textvariable=self.hline_name_var, width=20)
        line_name_entry.pack(side='left', padx=5)

        # Line elevation label and entry
        ttk.Label(line_input_frame, text="Elevation:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline_elevation_var'):
            self.hline_elevation_var = tk.DoubleVar(value=0.0)
        line_elevation_entry = ttk.Entry(line_input_frame, textvariable=self.hline_elevation_var, width=10)
        line_elevation_entry.pack(side='left', padx=5)

        # Line minimum x value label and entry
        ttk.Label(line_input_frame, text="X min:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline_xmin_var'):
            self.hline_xmin_var = tk.DoubleVar(value=self.fv_df['length'].min() if self.fv_df is not None else 0.0)
        line_xmin_entry = ttk.Entry(line_input_frame, textvariable=self.hline_xmin_var, width=10)
        line_xmin_entry.pack(side='left', padx=5)

        # Line maximum x value label and entry
        ttk.Label(line_input_frame, text="X max:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline_xmax_var'):
            self.hline_xmax_var = tk.DoubleVar(value=self.fv_df['length'].max() if self.fv_df is not None else 0.0)
        line_xmax_entry = ttk.Entry(line_input_frame, textvariable=self.hline_xmax_var, width=10)
        line_xmax_entry.pack(side='left', padx=5)

        # Line style drop down entry
        ttk.Label(line_input_frame, text="Style:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline_style_var'):
            self.hline_style_var = StringVar(value="solid")
        line_style_options = ["solid", "dashed", "dashdot", "dotted"]
        line_style_menu = ttk.OptionMenu(line_input_frame, self.hline_style_var, self.hline_style_var.get(), *line_style_options)
        line_style_menu.pack(side='left', padx=5)

        # Line color selection button
        if not hasattr(self, 'hline_color_var'):
            self.hline_color_var = StringVar(value="#FF0000")  # Default to red
        def choose_hline_color():
            current_color = self.hline_color_var.get()
            display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#FF0000'
            chosen = colorchooser.askcolor(color=display_color, title="Choose color for horizontal line")[1]
            if chosen:
                self.hline_color_var.set(chosen)
                hline_color_btn.config(bg=chosen, activebackground=chosen)  
   

        hline_color_btn = tk.Button(line_input_frame, text="Color", command=choose_hline_color, bg=self.hline_color_var.get(), activebackground=self.hline_color_var.get())
        hline_color_btn.pack(side='left', padx=5)

        # Add checkbox to enable/disable the horizontal line
        if not hasattr(self, 'hline_enabled_var'):
            self.hline_enabled_var = tk.BooleanVar(value=False)
        hline_enabled_check = ttk.Checkbutton(line_input_frame, text="Enable", variable=self.hline_enabled_var)
        hline_enabled_check.pack(side='left', padx=5)

 # Add name and elevation inputs for horizontal lines 2
        line_input_frame = ttk.Frame(line_frame)
        line_input_frame.pack(fill='x', padx=10, pady=5)

        # Line name label and entry
        ttk.Label(line_input_frame, text="Name:").pack(side='left', padx=(0, 5))
        if not hasattr(self, 'hline2_name_var'):
            self.hline2_name_var = StringVar(value="")
        line_name_entry = ttk.Entry(line_input_frame, textvariable=self.hline2_name_var, width=20)
        line_name_entry.pack(side='left', padx=5)

        # Line elevation label and entry
        ttk.Label(line_input_frame, text="Elevation:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline2_elevation_var'):
            self.hline2_elevation_var = tk.DoubleVar(value=0.0)
        line_elevation_entry = ttk.Entry(line_input_frame, textvariable=self.hline2_elevation_var, width=10)
        line_elevation_entry.pack(side='left', padx=5)

        # Line minimum x value label and entry
        ttk.Label(line_input_frame, text="X min:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline2_xmin_var'):
            self.hline2_xmin_var = tk.DoubleVar(value=self.fv_df['length'].min() if self.fv_df is not None else 0.0)
        line_xmin_entry = ttk.Entry(line_input_frame, textvariable=self.hline2_xmin_var, width=10)
        line_xmin_entry.pack(side='left', padx=5)

        # Line maximum x value label and entry
        ttk.Label(line_input_frame, text="X max:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline2_xmax_var'):
            self.hline2_xmax_var = tk.DoubleVar(value=self.fv_df['length'].max() if self.fv_df is not None else 0.0)
        line_xmax_entry = ttk.Entry(line_input_frame, textvariable=self.hline2_xmax_var, width=10)
        line_xmax_entry.pack(side='left', padx=5)

        # Line style drop down entry
        ttk.Label(line_input_frame, text="Style:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline2_style_var'):
            self.hline2_style_var = StringVar(value="solid")
        line_style_options = ["solid", "dashed", "dashdot", "dotted"]
        line_style_menu = ttk.OptionMenu(line_input_frame, self.hline2_style_var, self.hline2_style_var.get(), *line_style_options)
        line_style_menu.pack(side='left', padx=5)

        # Line color selection button
        if not hasattr(self, 'hline2_color_var'):
            self.hline2_color_var = StringVar(value="#FF0000")  # Default to red
        def choose_hline2_color():
            current_color = self.hline2_color_var.get()
            display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#FF0000'
            chosen = colorchooser.askcolor(color=display_color, title="Choose color for horizontal line")[1]
            if chosen:
                self.hline2_color_var.set(chosen)
                hline2_color_btn.config(bg=chosen, activebackground=chosen)  
   

        hline2_color_btn = tk.Button(line_input_frame, text="Color", command=choose_hline2_color, bg=self.hline2_color_var.get(), activebackground=self.hline2_color_var.get())
        hline2_color_btn.pack(side='left', padx=5)

        # Add checkbox to enable/disable the horizontal line
        if not hasattr(self, 'hline2_enabled_var'):
            self.hline2_enabled_var = tk.BooleanVar(value=False)
        hline2_enabled_check = ttk.Checkbutton(line_input_frame, text="Enable", variable=self.hline2_enabled_var)
        hline2_enabled_check.pack(side='left', padx=5)

        # Add name and elevation inputs for horizontal lines 3
        line_input_frame = ttk.Frame(line_frame)
        line_input_frame.pack(fill='x', padx=10, pady=5)

        # Line name label and entry
        ttk.Label(line_input_frame, text="Name:").pack(side='left', padx=(0, 5))
        if not hasattr(self, 'hline3_name_var'):
            self.hline3_name_var = StringVar(value="")
        line_name_entry = ttk.Entry(line_input_frame, textvariable=self.hline3_name_var, width=20)
        line_name_entry.pack(side='left', padx=5)

        # Line elevation label and entry
        ttk.Label(line_input_frame, text="Elevation:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline3_elevation_var'):
            self.hline3_elevation_var = tk.DoubleVar(value=0.0)
        line_elevation_entry = ttk.Entry(line_input_frame, textvariable=self.hline3_elevation_var, width=10)
        line_elevation_entry.pack(side='left', padx=5)

        # Line minimum x value label and entry
        ttk.Label(line_input_frame, text="X min:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline3_xmin_var'):
            self.hline3_xmin_var = tk.DoubleVar(value=self.fv_df['length'].min() if self.fv_df is not None else 0.0)
        line_xmin_entry = ttk.Entry(line_input_frame, textvariable=self.hline3_xmin_var, width=10)
        line_xmin_entry.pack(side='left', padx=5)

        # Line maximum x value label and entry
        ttk.Label(line_input_frame, text="X max:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline3_xmax_var'):
            self.hline3_xmax_var = tk.DoubleVar(value=self.fv_df['length'].max() if self.fv_df is not None else 0.0)
        line_xmax_entry = ttk.Entry(line_input_frame, textvariable=self.hline3_xmax_var, width=10)
        line_xmax_entry.pack(side='left', padx=5)

        # Line style drop down entry
        ttk.Label(line_input_frame, text="Style:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline3_style_var'):
            self.hline3_style_var = StringVar(value="solid")
        line_style_options = ["solid", "dashed", "dashdot", "dotted"]
        line_style_menu = ttk.OptionMenu(line_input_frame, self.hline3_style_var, self.hline3_style_var.get(), *line_style_options)
        line_style_menu.pack(side='left', padx=5)

        # Line color selection button
        if not hasattr(self, 'hline3_color_var'):
            self.hline3_color_var = StringVar(value="#FF0000")  # Default to red
        def choose_hline3_color():
            current_color = self.hline3_color_var.get()
            display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#FF0000'
            chosen = colorchooser.askcolor(color=display_color, title="Choose color for horizontal line")[1]
            if chosen:
                self.hline3_color_var.set(chosen)
                hline3_color_btn.config(bg=chosen, activebackground=chosen)  
   

        hline3_color_btn = tk.Button(line_input_frame, text="Color", command=choose_hline3_color, bg=self.hline3_color_var.get(), activebackground=self.hline3_color_var.get())
        hline3_color_btn.pack(side='left', padx=5)

        # Add checkbox to enable/disable the horizontal line
        if not hasattr(self, 'hline3_enabled_var'):
            self.hline3_enabled_var = tk.BooleanVar(value=False)
        hline3_enabled_check = ttk.Checkbutton(line_input_frame, text="Enable", variable=self.hline3_enabled_var)
        hline3_enabled_check.pack(side='left', padx=5)


        # Add name and elevation inputs for horizontal lines 4
        line_input_frame = ttk.Frame(line_frame)
        line_input_frame.pack(fill='x', padx=10, pady=5)

        # Line name label and entry
        ttk.Label(line_input_frame, text="Name:").pack(side='left', padx=(0, 5))
        if not hasattr(self, 'hline4_name_var'):
            self.hline4_name_var = StringVar(value="")
        line_name_entry = ttk.Entry(line_input_frame, textvariable=self.hline4_name_var, width=20)
        line_name_entry.pack(side='left', padx=5)

        # Line elevation label and entry
        ttk.Label(line_input_frame, text="Elevation:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline4_elevation_var'):
            self.hline4_elevation_var = tk.DoubleVar(value=0.0)
        line_elevation_entry = ttk.Entry(line_input_frame, textvariable=self.hline4_elevation_var, width=10)
        line_elevation_entry.pack(side='left', padx=5)

        # Line minimum x value label and entry
        ttk.Label(line_input_frame, text="X min:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline4_xmin_var'):
            self.hline4_xmin_var = tk.DoubleVar(value=self.fv_df['length'].min() if self.fv_df is not None else 0.0)
        line_xmin_entry = ttk.Entry(line_input_frame, textvariable=self.hline4_xmin_var, width=10)
        line_xmin_entry.pack(side='left', padx=5)

        # Line maximum x value label and entry
        ttk.Label(line_input_frame, text="X max:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline4_xmax_var'):
            self.hline4_xmax_var = tk.DoubleVar(value=self.fv_df['length'].max() if self.fv_df is not None else 0.0)
        line_xmax_entry = ttk.Entry(line_input_frame, textvariable=self.hline4_xmax_var, width=10)
        line_xmax_entry.pack(side='left', padx=5)

        # Line style drop down entry
        ttk.Label(line_input_frame, text="Style:").pack(side='left', padx=(10, 5))
        if not hasattr(self, 'hline4_style_var'):
            self.hline4_style_var = StringVar(value="solid")
        line_style_options = ["solid", "dashed", "dashdot", "dotted"]
        line_style_menu = ttk.OptionMenu(line_input_frame, self.hline4_style_var, self.hline4_style_var.get(), *line_style_options)
        line_style_menu.pack(side='left', padx=5)

        # Line color selection button
        if not hasattr(self, 'hline4_color_var'):
            self.hline4_color_var = StringVar(value="#FF0000")  # Default to red
        def choose_hline4_color():
            current_color = self.hline4_color_var.get()
            display_color = current_color if current_color not in ['#000000', '#000', 'black'] else '#FF0000'
            chosen = colorchooser.askcolor(color=display_color, title="Choose color for horizontal line")[1]
            if chosen:
                self.hline4_color_var.set(chosen)
                hline4_color_btn.config(bg=chosen, activebackground=chosen)  
   

        hline4_color_btn = tk.Button(line_input_frame, text="Color", command=choose_hline4_color, bg=self.hline4_color_var.get(), activebackground=self.hline4_color_var.get())
        hline4_color_btn.pack(side='left', padx=5)

        # Add checkbox to enable/disable the horizontal line
        if not hasattr(self, 'hline4_enabled_var'):
            self.hline4_enabled_var = tk.BooleanVar(value=False)
        hline4_enabled_check = ttk.Checkbutton(line_input_frame, text="Enable", variable=self.hline4_enabled_var)
        hline4_enabled_check.pack(side='left', padx=5)



        # Update legends if plot data is available
        if hasattr(self, 'ecolor_df') and self.ecolor_df is not None:
            self.setup_legend_plot()
            
    def update_horizon_alias(self, horizon):
        """Update horizon alias when changed"""
        if horizon in self.horizon_alias_vars:
            self.horizon_aliases[horizon] = self.horizon_alias_vars[horizon].get()
            self.setup_legend_plot()  # Update legend immediately
            
    def update_zone_alias(self, zone):
        """Update zone alias when changed"""
        if zone in self.zone_alias_vars:
            old_alias = self.zone_names_aliases.get(zone, zone)
            new_alias = self.zone_alias_vars[zone].get()
            self.zone_names_aliases[zone] = new_alias
            
            # Update the key in zone_unit_colors if it exists
            if old_alias in self.zone_unit_colors:
                self.zone_unit_colors[new_alias] = self.zone_unit_colors.pop(old_alias)
            
            self.setup_legend_plot()  # Update legend immediately
            
    def update_zone_lithology(self, zone):
        """Update zone lithology and color when changed"""
        if zone in self.zone_lithology_vars:
            lithology = self.zone_lithology_vars[zone].get()
            if lithology in self.zone_lithology:
                self.zone_colors[zone] = self.zone_lithology[lithology]
                # Update the color indicator
                for widget in self.color_scrollable_frame.winfo_children():
                    if isinstance(widget, ttk.LabelFrame) and 'Zone' in str(widget['text']):
                        for row_widget in widget.winfo_children():
                            if isinstance(row_widget, ttk.Frame):
                                widgets = row_widget.winfo_children()
                                if len(widgets) >= 4 and str(widgets[0]['text']).strip() == zone[:15]:
                                    if len(widgets) >= 5 and isinstance(widgets[4], tk.Label):
                                        widgets[4].config(bg=self.zone_colors[zone])
                self.setup_legend_plot()  # Update legend immediately
    
    def on_closing(self):
        """Clean up matplotlib figures before closing the application"""
        plt.close('all')  # Close all matplotlib figures
        self.destroy()    # Close the tkinter window
    
    def generate_plots(self):
        """Generate all plots with current settings"""
        # Check all required data
        if self.datadict is None or len(self.datadict) == 0:
            messagebox.showwarning("Warning", "Please load horizon data first!")
            return
        
        if self.nfv_df is None or self.nhv_df is None:
            messagebox.showwarning("Warning", "Please execute horizon shift first!")
            return
        
        if self.nh_list is None or len(self.nh_list) == 0:
            messagebox.showwarning("Warning", "No horizons available. Please execute horizon shift first!")
            return
        
        try:
            # Process data for plotting
            self.nfv_df, self.nhv_df = overlap_trunk(self.nfv_df, self.nhv_df)
            
            # Setup color DataFrames for plotting
            self.setup_plot_data()
            
            # Generate all plots
            self.setup_all_plots()
            
            messagebox.showinfo("Success", "All plots generated successfully! Check the plot tabs.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate plots: {str(e)}\n\nPlease ensure you have:\n1. Loaded data\n2. Converted to length/depth\n3. Executed horizon shift")
    
    def setup_plot_data(self):
        """Setup color and type data for plotting"""
        if self.nh_list is not None:
            # Create color dataframe
            self.color_df = pd.DataFrame({
                'Horizon': self.nh_list,
                'Alias': [self.horizon_aliases.get(h, h) for h in self.nh_list],
                'Color': [self.horizon_colors.get(h, '#000000') for h in self.nh_list]
            })
            self.ecolor_df = self.color_df.copy()
            
            # Create zone type dataframe
            zone_list = list(self.zone_names_aliases.keys())
            #print(zone_list)
            self.ztype_df = pd.DataFrame({
                'Zone': zone_list,
                'Alias': [self.zone_names_aliases.get(z, z) for z in zone_list],
                'Type': ['Undefined'] * len(zone_list)
            })
            self.eztype_df = self.ztype_df.copy()
            #print('exztype_df', self.eztype_df)

            #self.ezcolor_df = efa.zone_type_color(self.eztype_df)

            # Update zone colors based on lithology settings
            if hasattr(self, 'zone_lithology_vars'):
                for zone, var in self.zone_lithology_vars.items():
                    lithology = var.get()
                    if lithology in self.zone_lithology:
                        self.zone_colors[zone] = self.zone_lithology[lithology]
            
            # Create zone color dataframe with lithology type
            lithology_types = []
            for z in zone_list:
                if hasattr(self, 'zone_lithology_vars') and z in self.zone_lithology_vars:
                    lithology_types.append(self.zone_lithology_vars[z].get())
                else:
                    lithology_types.append('Undefined')
            
            self.ezcolor_df = pd.DataFrame({
                'Zone': zone_list,
                'Alias': [self.zone_names_aliases.get(z, z) for z in zone_list],
                'Color': [self.zone_colors.get(z, '#ffffff') for z in zone_list],
                'Lithology': lithology_types
            })
            #print('ezcolor_df', self.ezcolor_df)
    
    def setup_all_plots(self):
        """Setup all plot tabs"""
        self.setup_throw_profile_plot()
        self.setup_juxtaposition_unit_plot()
        self.setup_juxtaposition_plot()
        self.setup_scenario_plot()
        self.setup_legend_plot()
        self.setup_output_tables_data()
    
    # Plot tab setup methods from efa_tkinter_juxtaposition_app_v2.py
    def setup_throw_profile_tab(self):
        """Setup throw profile tab with legend sidebar"""
        main_frame = ttk.Frame(self.throw_profile_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create legend sidebar
        self.legend_sidebar_throw = ttk.Frame(main_frame, width=400)
        self.legend_sidebar_throw.pack(side='left', fill='y', padx=(0, 10))
        self.legend_sidebar_throw.pack_propagate(False)
        
        # Add separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)

        # Main plot area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side='left', fill='both', expand=True)

        ttk.Label(content_frame, 
                 text='Throw profile analysis',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        self.gridvarf0 = BooleanVar(value=True)
        self.meanthrow_var = BooleanVar(value=True)
        self.throw_leg_var = BooleanVar(value=True)
        self.throw_invertx_var = BooleanVar(value=False)

        ttk.Checkbutton(controls_frame, text="Display gridlines", 
                       variable=self.gridvarf0, command=self.update_throw_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display mean throw", 
                       variable=self.meanthrow_var, 
                       command=self.update_throw_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display legend", 
                       variable=self.throw_leg_var, 
                       command=self.update_throw_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Invert X-axis", 
                       variable=self.throw_invertx_var, 
                       command=self.update_throw_plot).pack(side='left', padx=5)
        
        self.throw_plot_frame = ttk.Frame(content_frame)
        self.throw_plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    def setup_throw_profile_plot(self):
        """Generate throw profile plot"""
        # Safety check: ensure frame exists
        if not hasattr(self, 'throw_plot_frame') or self.throw_plot_frame is None:
            print("Warning: throw_plot_frame not available")
            return
        
        try:
            for widget in self.throw_plot_frame.winfo_children():
                widget.destroy()
        except:
            pass
        
        # Close any existing figures to prevent memory leaks
        plt.close('all')
        
        try:
            fig4, self.throwrange_df, self.throwarray = self.throw_plot_method()
            
            # Store figure reference for clipboard copying
            self.current_throw_fig = fig4
            
            # Create frame for plot and controls
            plot_container = ttk.Frame(self.throw_plot_frame)
            plot_container.pack(fill='both', expand=True)
            
            # Add toolbar frame with copy button
            toolbar_frame = ttk.Frame(plot_container)
            toolbar_frame.pack(fill='x', padx=5, pady=(2, 0))
            
            # Left side: Title
            ttk.Label(toolbar_frame, text="Throw Profile Plot", 
                     font=('Arial', 10, 'bold')).pack(side='left')
            
            # Right side: Copy button
            button_frame = ttk.Frame(toolbar_frame)
            button_frame.pack(side='right')
            
            ttk.Button(button_frame, text="📋 Copy to Clipboard", 
                      command=self.copy_throw_plot_to_clipboard,
                      style='Accent.TButton').pack(side='right', padx=(5, 0))
            
            canvas = FigureCanvasTkAgg(fig4, plot_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
            # Add navigation toolbar (only one)
            toolbar = NavigationToolbar2Tk(canvas, plot_container)
            toolbar.update()
            
        except Exception as e:
            ttk.Label(self.throw_plot_frame, text=f"Error creating plot: {str(e)}").pack()
    
    def update_throw_plot(self):
        """Update throw plot when checkbox changes"""
        if hasattr(self, 'throwrange_df'):
            self.setup_throw_profile_plot()
            # Update legend as well
            if hasattr(self, 'legend_sidebar_throw') and hasattr(self, 'ecolor_df'):
                self.setup_legend_plot()
    

    def setup_juxtaposition_unit_tab(self):
        """Setup juxtaposition unit tab with legend sidebar"""
        main_frame = ttk.Frame(self.juxtaposition_unit_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        # Create legend sidebar
        self.legend_sidebar_juxt_unit = ttk.Frame(main_frame, width=400)
        self.legend_sidebar_juxt_unit.pack(side='left', fill='y', padx=(0, 10))
        self.legend_sidebar_juxt_unit.pack_propagate(False)
        # Add separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)
        # Main plot area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side='left', fill='both', expand=True)

        ttk.Label(content_frame, 
                 text='Zone juxtaposition unit analysis',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)

        # Initialize control variables for unit plot
        self.gridvarf_unit = BooleanVar(value=True)
        self.fv_unit_var = BooleanVar(value=True)
        self.hv_unit_var = BooleanVar(value=True)
        self.fill_unit_var = BooleanVar(value=True)
        self.orgpoints_unit = BooleanVar(value=False)
        self.juxt_unit_leg_var = BooleanVar(value=True)
        self.unit_invertx_var = BooleanVar(value=False)

        ttk.Checkbutton(controls_frame, text="Display gridlines", 
                       variable=self.gridvarf_unit, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        
        ttk.Checkbutton(controls_frame, text="Display footwall", 
                       variable=self.fv_unit_var, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display hanging-wall", 
                       variable=self.hv_unit_var, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display zone colors", 
                       variable=self.fill_unit_var, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display original points", 
                       variable=self.orgpoints_unit, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display legend", 
                       variable=self.juxt_unit_leg_var, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Invert X-axis", 
                       variable=self.unit_invertx_var, command=self.update_juxtaposition_unit_plot).pack(side='left', padx=5)

        self.juxt_unit_plot_frame = ttk.Frame(content_frame)
        self.juxt_unit_plot_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def setup_juxtaposition_unit_plot(self):
        """Generate juxtaposition unit plot"""
        # Safety check: ensure frame exists
        if not hasattr(self, 'juxt_unit_plot_frame') or self.juxt_unit_plot_frame is None:
            print("Warning: juxt_unit_plot_frame not available")
            return
        
        try:
            for widget in self.juxt_unit_plot_frame.winfo_children():
                widget.destroy()
        except:
            pass
        
        # Close any existing figures to prevent memory leaks
        plt.close('all')
        
        try:
            fig_unit = self.zone_unit_plot_method()
            
            # Store figure reference for clipboard copying
            self.current_juxt_unit_fig = fig_unit
            
            # Create frame for plot and controls
            plot_container = ttk.Frame(self.juxt_unit_plot_frame)
            plot_container.pack(fill='both', expand=True)
            
            # Add toolbar frame with copy button
            toolbar_frame = ttk.Frame(plot_container)
            toolbar_frame.pack(fill='x', padx=5, pady=(2, 0))
            
            # Left side: Title
            ttk.Label(toolbar_frame, text="Juxtaposition Unit Plot", 
                     font=('Arial', 10, 'bold')).pack(side='left')
            
            # Right side: Copy button
            button_frame = ttk.Frame(toolbar_frame)
            button_frame.pack(side='right')
            
            ttk.Button(button_frame, text="📋 Copy to Clipboard", 
                      command=self.copy_juxt_unit_plot_to_clipboard,
                      style='Accent.TButton').pack(side='right', padx=(5, 0))
            
            canvas = FigureCanvasTkAgg(fig_unit, plot_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
            toolbar = NavigationToolbar2Tk(canvas, plot_container)
            toolbar.update()
            
        except Exception as e:
            ttk.Label(self.juxt_unit_plot_frame, text=f"Error creating plot: {str(e)}").pack()
    
    def update_juxtaposition_unit_plot(self):
        """Update juxtaposition unit plot when checkboxes change"""
        if hasattr(self, 'zone_unit_colors') and self.zone_unit_colors:
            self.setup_juxtaposition_unit_plot()
            # Update legend as well
            if hasattr(self, 'legend_sidebar_juxt_unit') and hasattr(self, 'ecolor_df'):
                self.setup_legend_plot()

    

        
    def setup_juxtaposition_plot_tab(self):
        """Setup juxtaposition plot tab with legend sidebar"""
        main_frame = ttk.Frame(self.juxtaposition_plot_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create legend sidebar
        self.legend_sidebar_juxt = ttk.Frame(main_frame, width=400)
        self.legend_sidebar_juxt.pack(side='left', fill='y', padx=(0, 10))
        self.legend_sidebar_juxt.pack_propagate(False)
        
        # Add separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)

        # Main plot area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(content_frame, 
                 text='Zone juxtaposition plot',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        self.gridvarf1 = BooleanVar(value=True)
        self.fv_var = BooleanVar(value=True)
        self.hv_var = BooleanVar(value=True)
        self.fill_var = BooleanVar(value=True)
        self.orgpoints = BooleanVar(value=False)
        self.juxt_leg_var = BooleanVar(value=True)
        self.lith_invertx_var = BooleanVar(value=False)

        ttk.Checkbutton(controls_frame, text="Display gridlines", 
                       variable=self.gridvarf1, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        
        ttk.Checkbutton(controls_frame, text="Display footwall", 
                       variable=self.fv_var, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display hanging-wall", 
                       variable=self.hv_var, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display lithology", 
                       variable=self.fill_var, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display original points", 
                       variable=self.orgpoints, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display legend", 
                       variable=self.juxt_leg_var, command=self.update_juxtaposition_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Invert X-axis", 
                       variable=self.lith_invertx_var, command=self.update_juxtaposition_plot).pack(side='left', padx=5)

        self.juxt_plot_frame = ttk.Frame(content_frame)
        self.juxt_plot_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    def setup_juxtaposition_plot(self):
        """Generate juxtaposition plot"""
        # Safety check: ensure frame exists
        if not hasattr(self, 'juxt_plot_frame') or self.juxt_plot_frame is None:
            print("Warning: juxt_plot_frame not available")
            return
        
        try:
            for widget in self.juxt_plot_frame.winfo_children():
                widget.destroy()
        except:
            pass
        
        # Close any existing figures to prevent memory leaks
        plt.close('all')
        
        try:
            fig2 = self.zone_color_plot_method()
            
            # Store figure reference for clipboard copying
            self.current_juxt_fig = fig2
            
            # Create frame for plot and controls
            plot_container = ttk.Frame(self.juxt_plot_frame)
            plot_container.pack(fill='both', expand=True)
            
            # Add toolbar frame with copy button
            toolbar_frame = ttk.Frame(plot_container)
            toolbar_frame.pack(fill='x', padx=5, pady=(2, 0))
            
            # Left side: Title
            ttk.Label(toolbar_frame, text="Juxtaposition Plot", 
                     font=('Arial', 10, 'bold')).pack(side='left')
            
            # Right side: Copy button
            button_frame = ttk.Frame(toolbar_frame)
            button_frame.pack(side='right')
            
            ttk.Button(button_frame, text="📋 Copy to Clipboard", 
                      command=self.copy_juxt_plot_to_clipboard,
                      style='Accent.TButton').pack(side='right', padx=(5, 0))
            
            canvas = FigureCanvasTkAgg(fig2, plot_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
            toolbar = NavigationToolbar2Tk(canvas, plot_container)
            toolbar.update()
            
        except Exception as e:
            ttk.Label(self.juxt_plot_frame, text=f"Error creating plot: {str(e)}").pack()
    
    def update_juxtaposition_plot(self):
        """Update juxtaposition plot when checkboxes change"""
        if hasattr(self, 'ezcolor_df'):
            self.setup_juxtaposition_plot()
            # Update legend as well
            if hasattr(self, 'legend_sidebar_juxt') and hasattr(self, 'ecolor_df'):
                self.setup_legend_plot()
    
    def setup_scenario_plot_tab(self):
        """Setup scenario plot tab with legend sidebar"""
        main_frame = ttk.Frame(self.scenario_plot_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create legend sidebar
        self.legend_sidebar_scenario = ttk.Frame(main_frame, width=400)
        self.legend_sidebar_scenario.pack(side='left', fill='y', padx=(0, 10))
        self.legend_sidebar_scenario.pack_propagate(False)
        
        # Add separator
        separator = ttk.Separator(main_frame, orient='vertical')
        separator.pack(side='left', fill='y', padx=5)

        # Main plot area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side='left', fill='both', expand=True)
        
        ttk.Label(content_frame, 
                 text='Juxtaposition scenario plot',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        self.gridvarf2 = BooleanVar(value=True)
        self.fvt6_var = BooleanVar(value=True)
        self.hvt6_var = BooleanVar(value=True)
        self.apex_var = BooleanVar(value=True)
        self.apexid_var = BooleanVar(value=False)
        self.orgpoints2 = BooleanVar(value=False)
        self.scenario_leg_var = BooleanVar(value=True)
        self.scen_invertx_var = BooleanVar(value=False)

        ttk.Checkbutton(controls_frame, text="Display gridlines", 
                       variable=self.gridvarf2, command=self.update_scenario_plot).pack(side='left', padx=5)
        
        ttk.Checkbutton(controls_frame, text="Display footwall lines", 
                       variable=self.fvt6_var, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display hanging-wall lines", 
                       variable=self.hvt6_var, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display apex points", 
                       variable=self.apex_var, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display apex ID", 
                       variable=self.apexid_var, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display original points",
                        variable=self.orgpoints2, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display legend",
                        variable=self.scenario_leg_var, command=self.update_scenario_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Invert X-axis", 
                       variable=self.scen_invertx_var, command=self.update_scenario_plot).pack(side='left', padx=5)

        self.scenario_plot_frame_inner = ttk.Frame(content_frame)
        self.scenario_plot_frame_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.warning_frame = ttk.Frame(content_frame)
        self.warning_frame.pack(fill='x', padx=10, pady=5)
    
    def setup_scenario_plot(self):
        """Generate scenario plot"""
        # Safety check: ensure frames exist
        if not hasattr(self, 'scenario_plot_frame_inner') or self.scenario_plot_frame_inner is None:
            print("Warning: scenario_plot_frame_inner not available")
            return
        if not hasattr(self, 'warning_frame') or self.warning_frame is None:
            print("Warning: warning_frame not available")
            return
        
        try:
            for widget in self.scenario_plot_frame_inner.winfo_children():
                widget.destroy()
        except:
            pass
        
        try:
            for widget in self.warning_frame.winfo_children():
                widget.destroy()
        except:
            pass
        
        # Close any existing figures to prevent memory leaks
        plt.close('all')
        
        try:
            fig3, self.juxtlist, warning = self.zone_juxtscenario_plot_method()
            
            # Store figure reference for clipboard copying
            self.current_scenario_fig = fig3
            
            # Create frame for plot and controls
            plot_container = ttk.Frame(self.scenario_plot_frame_inner)
            plot_container.pack(fill='both', expand=True)
            
            # Add toolbar frame with copy button
            toolbar_frame = ttk.Frame(plot_container)
            toolbar_frame.pack(fill='x', padx=5, pady=(2, 0))
            
            # Left side: Title
            ttk.Label(toolbar_frame, text="Scenario Plot", 
                     font=('Arial', 10, 'bold')).pack(side='left')
            
            # Right side: Copy button
            button_frame = ttk.Frame(toolbar_frame)
            button_frame.pack(side='right')
            
            ttk.Button(button_frame, text="📋 Copy to Clipboard", 
                      command=self.copy_scenario_plot_to_clipboard,
                      style='Accent.TButton').pack(side='right', padx=(5, 0))
            
            canvas = FigureCanvasTkAgg(fig3, plot_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
            # Add mouse hover functionality
            self.setup_scenario_hover(canvas, fig3)
            
            toolbar = NavigationToolbar2Tk(canvas, plot_container)
            toolbar.update()
            
            if warning:
                ttk.Label(self.warning_frame, text=warning, foreground='red').pack()
            
        except Exception as e:
            ttk.Label(self.scenario_plot_frame_inner, text=f"Error creating plot: {str(e)}").pack()
    
    def setup_scenario_hover(self, canvas, fig):
        """Setup mouse hover functionality for scenario plot"""
        ax = fig.gca()
        
        # Create annotation for hover text
        self.scenario_annotation = ax.annotate('', xy=(0,0), xytext=(20,20), 
                                             textcoords="offset points",
                                             bbox=dict(boxstyle="round", fc="w", alpha=0.9),
                                             arrowprops=dict(arrowstyle="->"))
        self.scenario_annotation.set_visible(False)
        
        def on_hover(event):
            if event.inaxes == ax and hasattr(self, 'juxtlist') and self.juxtlist is not None:
                # Check if mouse is near any apex point
                for idx, row in self.juxtlist.iterrows():
                    x, y = row['Length'], row['Elevation']
                    
                    # Calculate distance from mouse to point (in display coordinates)
                    if event.xdata is not None and event.ydata is not None:
                        dx = abs(event.xdata - x)
                        dy = abs(event.ydata - y)
                        
                        # Set tolerance for hover detection (adjust as needed)
                        x_tolerance = (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02  # 2% of x range
                        y_tolerance = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02  # 2% of y range
                        
                        if dx < x_tolerance and dy < y_tolerance:
                            # Build tooltip with juxtaposition data
                            tooltip_text = (f"Apex ID: {idx}\n"
                                          f"Distance a.m.s: {row['Length']:.1f} {self.unit_xy}\n"
                                          f"Elevation: {row['Elevation']:.1f} {self.z_select_to_unit()}\n"
                                          f"FW Alias: {row['FV_Alias']}\n"
                                          f"HW Alias: {row['HV_Alias']}\n"
                                          f"FW Lithology: {row['FV_Lith']}\n"
                                          f"HW Lithology: {row['HV_Lith']}")
                            
                            # Add Mean Throw if available (after Generate Plots is clicked)
                            if 'Mean_Throw' in row and pd.notna(row['Mean_Throw']):
                                tooltip_text += f"\nMean Throw: {row['Mean_Throw']:.1f} {self.z_select_to_unit()}"
                            
                            self.scenario_annotation.xy = (x, y)
                            self.scenario_annotation.set_text(tooltip_text)
                            self.scenario_annotation.set_visible(True)
                            canvas.draw_idle()
                            return
                
                # Hide annotation if not hovering over any point
                if self.scenario_annotation.get_visible():
                    self.scenario_annotation.set_visible(False)
                    canvas.draw_idle()
        
        # Connect the hover event
        canvas.mpl_connect('motion_notify_event', on_hover)

    def update_scenario_plot(self):
        """Update scenario plot when checkboxes change"""
        if hasattr(self, 'juxtlist'):
            # Preserve enhanced juxtlist data if available (with Mean_Throw column)
            if hasattr(self, 'juxt_df') and self.juxt_df is not None and 'Mean_Throw' in self.juxt_df.columns:
                # Store the enhanced data temporarily
                enhanced_juxtlist = self.juxt_df.copy()
                
                # Generate the updated plot
                self.setup_scenario_plot()
                
                # Restore the enhanced data for hover functionality
                self.juxtlist = enhanced_juxtlist
            else:
                # No enhanced data available, proceed normally
                self.setup_scenario_plot()
                
            # Update legend as well
            if hasattr(self, 'legend_sidebar_scenario') and hasattr(self, 'ecolor_df'):
                self.setup_legend_plot()
    

    def setup_legend_plot(self):
        """Setup legend plot in the sidebar for all plot tabs"""
        def populate_legend_sidebar(sidebar, legend_method, ecolor_df, ezcolor_df):
            # Safety check: ensure sidebar exists and is valid
            if sidebar is None:
                return
            
            try:
                # Clear existing widgets in sidebar
                for widget in sidebar.winfo_children():
                    widget.destroy()
            except:
                pass
            
            # Close any existing legend figures to prevent memory leaks
            plt.close('all')
            
            ttk.Label(sidebar, text="Legend", font=('Arial', 12, 'bold')).pack(pady=10)
            
            if ecolor_df is not None:
                try:
                    # Create legend using the specific legend method for this plot type
                    if legend_method == 'throw':
                        legend_fig = self.create_throw_legend(ecolor_df)
                    elif legend_method == 'unit':
                        legend_fig = self.create_unit_legend(ecolor_df)
                    elif legend_method == 'lithology':
                        if ezcolor_df is not None:
                            legend_fig = self.create_lithology_legend(ecolor_df, ezcolor_df)
                        else:
                            raise ValueError("Zone color data required for lithology legend")
                    elif legend_method == 'scenario':
                        legend_fig = self.create_scenario_legend(ecolor_df)
                    else:
                        raise ValueError(f"Unknown legend method: {legend_method}")
                    
                    # Store reference for clipboard functionality
                    self.current_legend_fig = legend_fig
                    
                    # Create frame for legend and copy button
                    legend_frame = ttk.Frame(sidebar)
                    legend_frame.pack(fill='both', expand=True, padx=5, pady=5)
                    
                    # Add copy button
                    copy_btn = ttk.Button(legend_frame, text="Copy Legend to Clipboard", 
                                        command=self.copy_legend_to_clipboard)
                    copy_btn.pack(pady=(0,5))
                    
                    canvas = FigureCanvasTkAgg(legend_fig, legend_frame)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill='both', expand=True)
                except Exception as e:
                    # If legend creation fails, create a simple text-based legend
                    ttk.Label(sidebar, text="Horizon Colors:", font=('Arial', 10, 'bold')).pack(pady=(10,5))
                    
                    # Create a frame for the legend content
                    legend_frame = ttk.Frame(sidebar)
                    legend_frame.pack(fill='both', expand=True, padx=10, pady=5)
                    
                    # Add horizon colors
                    for _, row in ecolor_df.iterrows():
                        color_frame = ttk.Frame(legend_frame)
                        color_frame.pack(fill='x', pady=2)
                        
                        # Color indicator (using colored square Unicode character)
                        color_label = tk.Label(color_frame, text="■", 
                                             foreground=row['Color'], font=('Arial', 12))
                        color_label.pack(side='left', padx=5)
                        
                        # Horizon name
                        name_label = ttk.Label(color_frame, text=row['Alias'])
                        name_label.pack(side='left', padx=5)
                    
                    # Add zone lithology legend if appropriate
                    if legend_method == 'lithology' and hasattr(self, 'zone_lithology'):
                        ttk.Label(sidebar, text="Zone Lithology:", font=('Arial', 10, 'bold')).pack(pady=(10,5))
                        
                        zone_frame = ttk.Frame(sidebar)
                        zone_frame.pack(fill='both', padx=10, pady=5)
                        
                        for zone_type, color in self.zone_lithology.items():
                            type_frame = ttk.Frame(zone_frame)
                            type_frame.pack(fill='x', pady=2)
                            
                            # Color indicator
                            color_label = tk.Label(type_frame, text="■", 
                                                 foreground=color, font=('Arial', 12))
                            color_label.pack(side='left', padx=5)
                            
                            # Zone type name
                            type_label = ttk.Label(type_frame, text=zone_type)
                            type_label.pack(side='left', padx=5)
            else:
                ttk.Label(sidebar, text="No data available\nfor legend", 
                         font=('Arial', 10), foreground='gray').pack(pady=20)

        # Populate legends for all plot tabs with appropriate legend methods
        if hasattr(self, 'legend_sidebar_throw') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_throw, 'throw', self.ecolor_df, self.ezcolor_df)
            
        if hasattr(self, 'legend_sidebar_juxt_unit') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_juxt_unit, 'unit', self.ecolor_df, self.ezcolor_df)
            
        if hasattr(self, 'legend_sidebar_juxt') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_juxt, 'lithology', self.ecolor_df, self.ezcolor_df)
            
        if hasattr(self, 'legend_sidebar_scenario') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_scenario, 'scenario', self.ecolor_df, self.ezcolor_df)

    def setup_output_tables_tab(self):
        """Setup output tables tab"""
        ttk.Label(self.output_tables_frame, 
                 text='Output tables for data export',
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        self.tables_notebook = ttk.Notebook(self.output_tables_frame)
        self.tables_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.throw_stats_frame = ttk.Frame(self.tables_notebook)
        self.juxt_scenarios_frame = ttk.Frame(self.tables_notebook)
        self.footwall_frame = ttk.Frame(self.tables_notebook)
        self.hangingwall_frame = ttk.Frame(self.tables_notebook)
        
        self.tables_notebook.add(self.throw_stats_frame, text='Throw Statistics')
        self.tables_notebook.add(self.juxt_scenarios_frame, text='Juxtaposition Scenarios')
        self.tables_notebook.add(self.footwall_frame, text='Foot-wall Data')
        self.tables_notebook.add(self.hangingwall_frame, text='Hanging-wall Data')
        
        # Create button frame for export buttons
        button_frame = ttk.Frame(self.output_tables_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Export Tables to CSV", 
                  command=self.export_tables).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Export Tables to Excel", 
                  command=self.export_tables_to_excel).pack(side='left', padx=5)
    
    def setup_output_tables_data(self):
        """Setup output tables data"""
        if hasattr(self, 'throwrange_df') and hasattr(self, 'juxtlist') and hasattr(self, 'throwarray'):
            self.juxt_df = interpolate_throw(self.fv_df, self.juxtlist, self.throwarray, self.ecolor_df)
            
            self.create_table_display(self.throw_stats_frame, self.throwrange_df, "Horizon Throw Statistics")
            self.create_juxtaposition_table(self.juxt_scenarios_frame, self.juxt_df, "Juxtaposition Scenarios")
            self.create_table_display(self.footwall_frame, self.nfv_df, "Foot-wall Data")
            self.create_table_display(self.hangingwall_frame, self.nhv_df, "Hanging-wall Data")
    
    def get_juxtaposition_color(self, fv_lith, hv_lith):
        """Get the background color for a juxtaposition scenario based on lithology types"""
        # Normalize lithology strings
        fv = str(fv_lith).strip()
        hv = str(hv_lith).strip()
        
        # Define color mapping based on juxtaposition scenario legend
        # Good Res - Good Res -> green
        if fv == 'Good Res' and hv == 'Good Res':
            return '#90EE90'  # Light green (easier to read text)
        
        # Good Res - Poor Res or Poor Res - Good Res -> yellow
        elif (fv == 'Good Res' and hv == 'Poor Res') or (fv == 'Poor Res' and hv == 'Good Res'):
            return '#FFFF99'  # Light yellow (easier to read text)
        
        # Poor Res - Poor Res -> orange
        elif fv == 'Poor Res' and hv == 'Poor Res':
            return '#FFD699'  # Light orange (easier to read text)
        
        # Good Res - SR or SR - Good Res -> black background (need white text)
        elif (fv == 'Good Res' and hv == 'SR') or (fv == 'SR' and hv == 'Good Res'):
            return 'black'
        
        # Poor Res - SR or SR - Poor Res -> black background (need white text)
        elif (fv == 'Poor Res' and hv == 'SR') or (fv == 'SR' and hv == 'Poor Res'):
            return 'black'
        
        # All other scenarios -> no color
        else:
            return None
    
    def create_juxtaposition_table(self, parent_frame, dataframe, title):
        """Create table display widget with color coding for juxtaposition scenarios"""
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(parent_frame, text=title, font=('Arial', 12, 'bold')).pack(pady=10)
        
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame)
        tree.pack(side='left', fill='both', expand=True)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar = ttk.Scrollbar(parent_frame, orient='horizontal', command=tree.xview)
        h_scrollbar.pack(side='bottom', fill='x')
        
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        columns = list(dataframe.columns)
        tree['columns'] = columns
        tree['show'] = 'tree headings'
        
        # Configure column headers with FW/HW aliases for display
        for col in columns:
            # Create display name by replacing FV with FW and HV with HW
            display_name = col.replace('FV_', 'FW_').replace('HV_', 'HW_')
            tree.heading(col, text=display_name)
            tree.column(col, width=100)
        
        # Define color tags for different juxtaposition scenarios
        tree.tag_configure('good_good', background='#90EE90', foreground='black')  # Light green
        tree.tag_configure('good_poor', background='#FFFF99', foreground='black')  # Light yellow
        tree.tag_configure('poor_poor', background='#FFD699', foreground='black')  # Light orange
        tree.tag_configure('res_sr', background='black', foreground='white')      # Black with white text
        tree.tag_configure('default', background='white', foreground='black')      # Default
        
        # Insert data with color tags based on FV_Lith and HV_Lith
        for index, row in dataframe.iterrows():
            # Get lithology values if they exist
            fv_lith = row.get('FV_Lith', '')
            hv_lith = row.get('HV_Lith', '')
            
            # Determine tag based on lithology combination
            tag = 'default'
            fv = str(fv_lith).strip()
            hv = str(hv_lith).strip()
            
            if fv == 'Good Res' and hv == 'Good Res':
                tag = 'good_good'
            elif (fv == 'Good Res' and hv == 'Poor Res') or (fv == 'Poor Res' and hv == 'Good Res'):
                tag = 'good_poor'
            elif fv == 'Poor Res' and hv == 'Poor Res':
                tag = 'poor_poor'
            elif ((fv == 'Good Res' or fv == 'Poor Res') and hv == 'SR') or \
                 ((hv == 'Good Res' or hv == 'Poor Res') and fv == 'SR'):
                tag = 'res_sr'
            
            tree.insert('', 'end', text=str(index), values=list(row), tags=(tag,))
    
    def create_table_display(self, parent_frame, dataframe, title):
        """Create table display widget"""
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(parent_frame, text=title, font=('Arial', 12, 'bold')).pack(pady=10)
        
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame)
        tree.pack(side='left', fill='both', expand=True)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar = ttk.Scrollbar(parent_frame, orient='horizontal', command=tree.xview)
        h_scrollbar.pack(side='bottom', fill='x')
        
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        columns = list(dataframe.columns)
        tree['columns'] = columns
        tree['show'] = 'tree headings'
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for index, row in dataframe.iterrows():
            tree.insert('', 'end', text=str(index), values=list(row))
    
    def export_tables(self):
        """Export all tables to CSV"""
        if not hasattr(self, 'throwrange_df'):
            messagebox.showwarning("Warning", "No data to export! Please generate plots first.")
            return
        
        directory = filedialog.askdirectory(title="Select directory to save CSV files")
        if not directory:
            return
        
        try:
            self.throwrange_df.to_csv(f"{directory}/throw_statistics.csv")
            self.juxt_df.to_csv(f"{directory}/juxtaposition_scenarios.csv")
            self.nfv_df.to_csv(f"{directory}/footwall_data.csv")
            self.nhv_df.to_csv(f"{directory}/hangingwall_data.csv")
            
            messagebox.showinfo("Success", f"Tables exported successfully to {directory}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export tables: {str(e)}")
    
    def export_tables_to_excel(self):
        """Export all tables to a single Excel file with multiple sheets"""
        if not hasattr(self, 'throwrange_df'):
            messagebox.showwarning("Warning", "No data to export! Please generate plots first.")
            return
        
        # Ask user for file location
        file_path = filedialog.asksaveasfilename(
            title="Save Excel File",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="efa_analysis_tables.xlsx"
        )
        
        if not file_path:
            return
        
        # Try different Excel engines in order of preference
        engines_to_try = ['xlsxwriter', 'openpyxl']
        
        for engine in engines_to_try:
            try:
                # Create Excel writer object with the current engine
                with pd.ExcelWriter(file_path, engine=engine) as writer:
                    # Write each dataframe to a different sheet
                    self.throwrange_df.to_excel(writer, sheet_name='Throw Statistics', index=True)
                    self.juxt_df.to_excel(writer, sheet_name='Juxtaposition Scenarios', index=True)
                    self.nfv_df.to_excel(writer, sheet_name='Footwall Data', index=True)
                    self.nhv_df.to_excel(writer, sheet_name='Hanging wall Data', index=True)
                    
                    # Auto-adjust column widths for better readability (only for xlsxwriter)
                    if engine == 'xlsxwriter':
                        for sheet_name in writer.sheets:
                            worksheet = writer.sheets[sheet_name]
                            # Get the dataframe that was written to this sheet
                            if sheet_name == 'Throw Statistics':
                                df = self.throwrange_df
                            elif sheet_name == 'Juxtaposition Scenarios':
                                df = self.juxt_df
                            elif sheet_name == 'Footwall Data':
                                df = self.nfv_df
                            else:  # Hangingwall Data
                                df = self.nhv_df
                            
                            # Set column widths
                            for idx, col in enumerate(df.columns):
                                # Get max length of column content
                                max_len = max(
                                    df[col].astype(str).apply(len).max(),
                                    len(str(col))
                                ) + 2
                                worksheet.set_column(idx + 1, idx + 1, min(max_len, 50))
                            # Set index column width
                            worksheet.set_column(0, 0, 10)
                    
                    elif engine == 'openpyxl':
                        # Auto-adjust column widths for openpyxl
                        for sheet_name in writer.sheets:
                            worksheet = writer.sheets[sheet_name]
                            for column in worksheet.columns:
                                max_length = 0
                                column_letter = column[0].column_letter
                                for cell in column:
                                    try:
                                        if len(str(cell.value)) > max_length:
                                            max_length = len(str(cell.value))
                                    except:
                                        pass
                                adjusted_width = min(max_length + 2, 50)
                                worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # If we get here, export was successful
                messagebox.showinfo("Success", 
                                  f"Tables exported successfully to:\n{file_path}\n\n"
                                  f"(Using {engine} engine)")
                return  # Exit function after successful export
                
            except ImportError:
                # This engine is not available, try the next one
                continue
            except Exception as e:
                # Some other error occurred with this engine
                messagebox.showerror("Error", f"Failed to export with {engine} engine:\n{str(e)}")
                return
        
        # If we get here, none of the engines worked
        messagebox.showerror("Error", 
                           "Excel export requires either 'xlsxwriter' or 'openpyxl' library.\n\n"
                           "Please install one of them using:\n"
                           "pip install xlsxwriter\n"
                           "or\n"
                           "pip install openpyxl")

    def reset_application(self):
        """Reset the entire application to its initial state"""
        # Ask for confirmation
        response = messagebox.askyesno(
            "Reset Application",
            "This will reset all data, plots, and settings.\n\nAre you sure you want to continue?",
            icon='warning'
        )
        
        if not response:
            return
        
        try:
            # Reset all data variables
            self.datadict = {}
            self.innfiles = []
            
            # Reset processing variables
            self.ld_dict = None
            self.fv_df = None
            self.hv_df = None
            self.nfv_df = None
            self.nhv_df = None
            self.nh_list = None
            self.strike = None
            self.dip = None
            self.shift_df = None
            self.color_df = None
            self.ztype_df = None
            self.ezcolor_df = None
            self.ecolor_df = None
            self.eztype_df = None
            
            # Reset GUI variables to defaults
            self.z_select.set('Z')
            self.num_horizons.set(1)
            self.plot_name.set("Fault")
            self.width.set(12)
            self.height.set(6)
            self.gridlines.set(False)
            self.linewidth.set(1.0)
            self.pointid.set(False)
            self.file_format.set('Petrel_FC')
            self.unit_xy = 'm'
            self.unit_depth = 'm'
            
            # Reset color and alias management
            self.horizon_colors = {}
            self.horizon_aliases = {}
            self.zone_colors = {}
            self.zone_lithology = {
                'Undefined': "azure",
                'Good': "yellow",
                'Poor': "orange", 
                'No Res': "black",
                'SR': "red"
            }
            self.zone_names_aliases = {}
            self.zone_unit_colors = {}
            self.zone_lithology_vars = {}  # Reset zone lithology variables
            
            # Reset legend sidebar references
            self.legend_sidebar_throw = None
            self.legend_sidebar_juxt = None
            self.legend_sidebar_juxt_unit = None
            self.legend_sidebar_scenario = None
            
            # Reset figure references
            self.current_throw_fig = None
            self.current_juxt_fig = None
            self.current_juxt_unit_fig = None
            self.current_scenario_fig = None
            self.current_legend_fig = None
            
            # Clear all tabs - check if attributes exist first and handle errors gracefully
            # Clear Data Input tab (data_display_frame)
            if hasattr(self, 'data_display_frame'):
                try:
                    for widget in self.data_display_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Data Manipulation tab frames
            if hasattr(self, 'ld_scroll_frame'):
                try:
                    for widget in self.ld_scroll_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            if hasattr(self, 'shifted_scroll_frame'):
                try:
                    for widget in self.shifted_scroll_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            if hasattr(self, 'mapped_scroll_frame'):
                try:
                    for widget in self.mapped_scroll_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Plot Settings tab
            if hasattr(self, 'color_scrollable_frame'):
                try:
                    for widget in self.color_scrollable_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Throw Profile tab
            if hasattr(self, 'throw_plot_frame'):
                try:
                    for widget in self.throw_plot_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Juxtaposition Unit Plot tab
            if hasattr(self, 'juxt_unit_plot_frame'):
                try:
                    for widget in self.juxt_unit_plot_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Juxtaposition Plot tab
            if hasattr(self, 'juxt_plot_frame'):
                try:
                    for widget in self.juxt_plot_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Scenario Plot tab (warning_frame contains the scenario plot)
            if hasattr(self, 'warning_frame'):
                try:
                    for widget in self.warning_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear Output Tables tab frames
            if hasattr(self, 'throw_stats_frame'):
                try:
                    for widget in self.throw_stats_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            if hasattr(self, 'juxt_scenarios_frame'):
                try:
                    for widget in self.juxt_scenarios_frame.winfo_children():
                        widget.destroy()
                except:
                    pass
            
            # Clear file listbox in sidebar
            if hasattr(self, 'datafiles_listbox'):
                try:
                    self.datafiles_listbox.delete(0, 'end')
                except:
                    pass
            
            # Clear data text display
            if hasattr(self, 'data_text'):
                try:
                    self.data_text.delete('1.0', 'end')
                except:
                    pass
            
            # Re-add initial instructions to display areas
            if hasattr(self, 'data_display_frame'):
                try:
                    ttk.Label(self.data_display_frame, 
                             text='Data Preview - Loaded files will be displayed here',
                             font=('Arial', 12, 'bold')).pack(pady=10)
                    
                    # Recreate the data text widget
                    data_text_frame = ttk.Frame(self.data_display_frame)
                    data_text_frame.pack(fill='both', expand=True, pady=10)
                    
                    self.data_text = tk.Text(data_text_frame, wrap=tk.WORD)
                    data_scrollbar = ttk.Scrollbar(data_text_frame, orient='vertical', command=self.data_text.yview)
                    self.data_text.configure(yscrollcommand=data_scrollbar.set)
                    
                    self.data_text.pack(side='left', fill='both', expand=True)
                    data_scrollbar.pack(side='right', fill='y')
                except:
                    pass
            
            if hasattr(self, 'ld_scroll_frame'):
                try:
                    ttk.Label(self.ld_scroll_frame, 
                             text="Length/Depth data will appear here after conversion.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'shifted_scroll_frame'):
                try:
                    ttk.Label(self.shifted_scroll_frame, 
                             text="Shifted data will appear here after executing horizon shift.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'mapped_scroll_frame'):
                try:
                    ttk.Label(self.mapped_scroll_frame, 
                             text="Mapped data will appear here after conversion.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'throw_plot_frame'):
                try:
                    ttk.Label(self.throw_plot_frame, 
                             text="Throw plot will appear here after executing horizon shift.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'juxt_unit_plot_frame'):
                try:
                    ttk.Label(self.juxt_unit_plot_frame, 
                             text="Juxtaposition unit plot will appear here after creating juxtaposition diagram.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'juxt_plot_frame'):
                try:
                    ttk.Label(self.juxt_plot_frame, 
                             text="Juxtaposition plot will appear here after creating juxtaposition diagram.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            if hasattr(self, 'warning_frame'):
                try:
                    ttk.Label(self.warning_frame, 
                             text="Scenario plot will appear here after creating scenario diagram.",
                             font=('Arial', 10)).pack(pady=20)
                except:
                    pass
            
            # Refresh the color settings display if available
            if hasattr(self, 'update_color_settings_display'):
                try:
                    self.update_color_settings_display()
                except:
                    pass
            
            messagebox.showinfo("Success", "Application has been reset to initial state.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset application: {str(e)}")

    def save_session(self):
        """Save the complete application session to a pickle file using file dialog"""
        file_path = filedialog.asksaveasfilename(
            title="Save Session",
            defaultextension=".pkl",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Collect all session data
            session_data = {
                # Core data processing variables
                'datadict': self.datadict,
                'innfiles': self.innfiles,
                'ld_dict': self.ld_dict,
                'fv_df': self.fv_df,
                'hv_df': self.hv_df,
                'nfv_df': self.nfv_df,
                'nhv_df': self.nhv_df,
                'nh_list': self.nh_list,
                'strike': self.strike,
                'dip': self.dip,
                'shift_df': self.shift_df,
                'color_df': self.color_df,
                'ztype_df': self.ztype_df,
                'ezcolor_df': self.ezcolor_df,
                'ecolor_df': self.ecolor_df,
                'eztype_df': self.eztype_df,
                
                # Unit variables (new in v0p9p5d3)
                'unit_xy': self.unit_xy,
                'unit_depth': self.unit_depth,
                
                # Color and alias management
                'horizon_colors': self.horizon_colors,
                'horizon_aliases': self.horizon_aliases,
                'zone_colors': self.zone_colors,
                'zone_lithology': self.zone_lithology,
                'zone_names_aliases': self.zone_names_aliases,
                'zone_unit_colors': self.zone_unit_colors,
                
                # UI variable states
                'z_select': self.z_select.get(),
                'num_horizons': self.num_horizons.get(),
                'plot_name': self.plot_name.get(),
                'width': self.width.get(),
                'height': self.height.get(),
                'gridlines': self.gridlines.get(),
                'linewidth': self.linewidth.get(),
                'pointid': self.pointid.get(),
                'file_format': self.file_format.get(),
                
                # Plot-specific variables (if they exist)
                'throwrange_df': getattr(self, 'throwrange_df', None),
                'throwarray': getattr(self, 'throwarray', None),
                'juxtlist': getattr(self, 'juxtlist', None),
                'juxt_df': getattr(self, 'juxt_df', None),
                
                # Additional plot control variables (if they exist)
                'gridvarf0': getattr(self, 'gridvarf0', BooleanVar(value=True)).get() if hasattr(self, 'gridvarf0') else True,
                'meanthrow_var': getattr(self, 'meanthrow_var', BooleanVar(value=True)).get() if hasattr(self, 'meanthrow_var') else True,
                'gridvarf1': getattr(self, 'gridvarf1', BooleanVar(value=True)).get() if hasattr(self, 'gridvarf1') else True,
                'fv_var': getattr(self, 'fv_var', BooleanVar(value=True)).get() if hasattr(self, 'fv_var') else True,
                'hv_var': getattr(self, 'hv_var', BooleanVar(value=True)).get() if hasattr(self, 'hv_var') else True,
                'fill_var': getattr(self, 'fill_var', BooleanVar(value=True)).get() if hasattr(self, 'fill_var') else True,
                'orgpoints': getattr(self, 'orgpoints', BooleanVar(value=False)).get() if hasattr(self, 'orgpoints') else False,
                'gridvarf2': getattr(self, 'gridvarf2', BooleanVar(value=True)).get() if hasattr(self, 'gridvarf2') else True,
                'fvt6_var': getattr(self, 'fvt6_var', BooleanVar(value=True)).get() if hasattr(self, 'fvt6_var') else True,
                'hvt6_var': getattr(self, 'hvt6_var', BooleanVar(value=True)).get() if hasattr(self, 'hvt6_var') else True,
                'apex_var': getattr(self, 'apex_var', BooleanVar(value=True)).get() if hasattr(self, 'apex_var') else True,
                'apexid_var': getattr(self, 'apexid_var', BooleanVar(value=False)).get() if hasattr(self, 'apexid_var') else False,
                'orgpoints2': getattr(self, 'orgpoints2', BooleanVar(value=False)).get() if hasattr(self, 'orgpoints2') else False,
                # Unit plot control variables
                'gridvarf_unit': getattr(self, 'gridvarf_unit', BooleanVar(value=True)).get() if hasattr(self, 'gridvarf_unit') else True,
                'fv_unit_var': getattr(self, 'fv_unit_var', BooleanVar(value=True)).get() if hasattr(self, 'fv_unit_var') else True,
                'hv_unit_var': getattr(self, 'hv_unit_var', BooleanVar(value=True)).get() if hasattr(self, 'hv_unit_var') else True,
                'fill_unit_var': getattr(self, 'fill_unit_var', BooleanVar(value=True)).get() if hasattr(self, 'fill_unit_var') else True,
                'orgpoints_unit': getattr(self, 'orgpoints_unit', BooleanVar(value=False)).get() if hasattr(self, 'orgpoints_unit') else False,
                'juxt_unit_leg_var': getattr(self, 'juxt_unit_leg_var', BooleanVar(value=True)).get() if hasattr(self, 'juxt_unit_leg_var') else True,
                'unit_invertx_var': getattr(self, 'unit_invertx_var', BooleanVar(value=False)).get() if hasattr(self, 'unit_invertx_var') else False,
                # Horizontal line variables
                'hline_enabled_var': getattr(self, 'hline_enabled_var', BooleanVar(value=False)).get() if hasattr(self, 'hline_enabled_var') else False,
                'hline2_enabled_var': getattr(self, 'hline2_enabled_var', BooleanVar(value=False)).get() if hasattr(self, 'hline2_enabled_var') else False,
                'hline3_enabled_var': getattr(self, 'hline3_enabled_var', BooleanVar(value=False)).get() if hasattr(self, 'hline3_enabled_var') else False,
                'hline4_enabled_var': getattr(self, 'hline4_enabled_var', BooleanVar(value=False)).get() if hasattr(self, 'hline4_enabled_var') else False,
                'hline_elevation_var': getattr(self, 'hline_elevation_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline_elevation_var') else 0.0,
                'hline2_elevation_var': getattr(self, 'hline2_elevation_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline2_elevation_var') else 0.0,
                'hline3_elevation_var': getattr(self, 'hline3_elevation_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline3_elevation_var') else 0.0,
                'hline4_elevation_var': getattr(self, 'hline4_elevation_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline4_elevation_var') else 0.0,
                'hline_xmin_var': getattr(self, 'hline_xmin_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline_xmin_var') else 0.0,
                'hline2_xmin_var': getattr(self, 'hline2_xmin_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline2_xmin_var') else 0.0,
                'hline3_xmin_var': getattr(self, 'hline3_xmin_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline3_xmin_var') else 0.0,
                'hline4_xmin_var': getattr(self, 'hline4_xmin_var', tk.DoubleVar(value=0.0)).get() if hasattr(self, 'hline4_xmin_var') else 0.0,
                'hline_xmax_var': getattr(self, 'hline_xmax_var', tk.DoubleVar(value=1000.0)).get() if hasattr(self, 'hline_xmax_var') else 1000.0,
                'hline2_xmax_var': getattr(self, 'hline2_xmax_var', tk.DoubleVar(value=1000.0)).get() if hasattr(self, 'hline2_xmax_var') else 1000.0,
                'hline3_xmax_var': getattr(self, 'hline3_xmax_var', tk.DoubleVar(value=1000.0)).get() if hasattr(self, 'hline3_xmax_var') else 1000.0,
                'hline4_xmax_var': getattr(self, 'hline4_xmax_var', tk.DoubleVar(value=1000.0)).get() if hasattr(self, 'hline4_xmax_var') else 1000.0,
                'hline_color_var': getattr(self, 'hline_color_var', StringVar(value='red')).get() if hasattr(self, 'hline_color_var') else 'red',
                'hline2_color_var': getattr(self, 'hline2_color_var', StringVar(value='blue')).get() if hasattr(self, 'hline2_color_var') else 'blue',
                'hline3_color_var': getattr(self, 'hline3_color_var', StringVar(value='green')).get() if hasattr(self, 'hline3_color_var') else 'green',
                'hline4_color_var': getattr(self, 'hline4_color_var', StringVar(value='orange')).get() if hasattr(self, 'hline4_color_var') else 'orange',
                'hline_style_var': getattr(self, 'hline_style_var', StringVar(value='solid')).get() if hasattr(self, 'hline_style_var') else 'solid',
                'hline2_style_var': getattr(self, 'hline2_style_var', StringVar(value='solid')).get() if hasattr(self, 'hline2_style_var') else 'solid',
                'hline3_style_var': getattr(self, 'hline3_style_var', StringVar(value='solid')).get() if hasattr(self, 'hline3_style_var') else 'solid',
                'hline4_style_var': getattr(self, 'hline4_style_var', StringVar(value='solid')).get() if hasattr(self, 'hline4_style_var') else 'solid',
                'hline_name_var': getattr(self, 'hline_name_var', StringVar(value='H-Line 1')).get() if hasattr(self, 'hline_name_var') else 'H-Line 1',
                'hline2_name_var': getattr(self, 'hline2_name_var', StringVar(value='H-Line 2')).get() if hasattr(self, 'hline2_name_var') else 'H-Line 2',
                'hline3_name_var': getattr(self, 'hline3_name_var', StringVar(value='H-Line 3')).get() if hasattr(self, 'hline3_name_var') else 'H-Line 3',
                'hline4_name_var': getattr(self, 'hline4_name_var', StringVar(value='H-Line 4')).get() if hasattr(self, 'hline4_name_var') else 'H-Line 4',
            }
            
            # Save to pickle file
            with open(file_path, 'wb') as f:
                pickle.dump(session_data, f)
            
            messagebox.showinfo("Success", f"Session saved successfully to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session:\n{str(e)}")
    
    def load_session(self):
        """Load a complete application session from a pickle file using file dialog"""
        file_path = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Load session data
            with open(file_path, 'rb') as f:
                session_data = pickle.load(f)
            
            # Restore core data processing variables
            self.datadict = session_data.get('datadict', {})
            self.innfiles = session_data.get('innfiles', [])
            self.ld_dict = session_data.get('ld_dict', None)
            self.fv_df = session_data.get('fv_df', None)
            self.hv_df = session_data.get('hv_df', None)
            self.nfv_df = session_data.get('nfv_df', None)
            self.nhv_df = session_data.get('nhv_df', None)
            self.nh_list = session_data.get('nh_list', None)
            self.strike = session_data.get('strike', None)
            self.dip = session_data.get('dip', None)
            self.shift_df = session_data.get('shift_df', None)
            self.color_df = session_data.get('color_df', None)
            self.ztype_df = session_data.get('ztype_df', None)
            self.ezcolor_df = session_data.get('ezcolor_df', None)
            self.ecolor_df = session_data.get('ecolor_df', None)
            self.eztype_df = session_data.get('eztype_df', None)
            
            # Restore unit variables (backwards compatible - defaults to 'm' if not found)
            self.unit_xy = session_data.get('unit_xy', 'm')
            self.unit_depth = session_data.get('unit_depth', 'm')
            
            # Restore color and alias management
            self.horizon_colors = session_data.get('horizon_colors', {})
            self.horizon_aliases = session_data.get('horizon_aliases', {})
            self.zone_colors = session_data.get('zone_colors', {})
            self.zone_lithology = session_data.get('zone_lithology', {
                'Undefined': "#CCCCCC", 'Good': "yellow", 'Poor': "orange", 
                'No Res': "black", 'SR': "red"
            })
            self.zone_names_aliases = session_data.get('zone_names_aliases', {})
            self.zone_unit_colors = session_data.get('zone_unit_colors', {})
            
            # Restore UI variable states
            self.z_select.set(session_data.get('z_select', 'Z'))
            self.num_horizons.set(session_data.get('num_horizons', 1))
            self.plot_name.set(session_data.get('plot_name', "Analysis Plot"))
            self.width.set(session_data.get('width', 12))
            self.height.set(session_data.get('height', 6))
            self.gridlines.set(session_data.get('gridlines', False))
            self.linewidth.set(session_data.get('linewidth', 1.0))
            self.pointid.set(session_data.get('pointid', False))
            self.file_format.set(session_data.get('file_format', 'Petrel_FC'))
            
            # Restore plot-specific variables
            self.throwrange_df = session_data.get('throwrange_df', None)
            self.throwarray = session_data.get('throwarray', None)
            self.juxtlist = session_data.get('juxtlist', None)
            self.juxt_df = session_data.get('juxt_df', None)
            
            # Restore plot control variables (create if they don't exist)
            if hasattr(self, 'gridvarf0'):
                self.gridvarf0.set(session_data.get('gridvarf0', True))
            if hasattr(self, 'meanthrow_var'):
                self.meanthrow_var.set(session_data.get('meanthrow_var', True))
            if hasattr(self, 'gridvarf1'):
                self.gridvarf1.set(session_data.get('gridvarf1', True))
            if hasattr(self, 'fv_var'):
                self.fv_var.set(session_data.get('fv_var', True))
            if hasattr(self, 'hv_var'):
                self.hv_var.set(session_data.get('hv_var', True))
            if hasattr(self, 'fill_var'):
                self.fill_var.set(session_data.get('fill_var', True))
            if hasattr(self, 'orgpoints'):
                self.orgpoints.set(session_data.get('orgpoints', False))
            if hasattr(self, 'gridvarf2'):
                self.gridvarf2.set(session_data.get('gridvarf2', True))
            if hasattr(self, 'fvt6_var'):
                self.fvt6_var.set(session_data.get('fvt6_var', True))
            if hasattr(self, 'hvt6_var'):
                self.hvt6_var.set(session_data.get('hvt6_var', True))
            if hasattr(self, 'apex_var'):
                self.apex_var.set(session_data.get('apex_var', True))
            if hasattr(self, 'apexid_var'):
                self.apexid_var.set(session_data.get('apexid_var', False))
            if hasattr(self, 'orgpoints2'):
                self.orgpoints2.set(session_data.get('orgpoints2', False))
            
            # Restore unit plot control variables
            if hasattr(self, 'gridvarf_unit'):
                self.gridvarf_unit.set(session_data.get('gridvarf_unit', True))
            if hasattr(self, 'fv_unit_var'):
                self.fv_unit_var.set(session_data.get('fv_unit_var', True))
            if hasattr(self, 'hv_unit_var'):
                self.hv_unit_var.set(session_data.get('hv_unit_var', True))
            if hasattr(self, 'fill_unit_var'):
                self.fill_unit_var.set(session_data.get('fill_unit_var', True))
            if hasattr(self, 'orgpoints_unit'):
                self.orgpoints_unit.set(session_data.get('orgpoints_unit', False))
            if hasattr(self, 'juxt_unit_leg_var'):
                self.juxt_unit_leg_var.set(session_data.get('juxt_unit_leg_var', True))
            if hasattr(self, 'unit_invertx_var'):
                self.unit_invertx_var.set(session_data.get('unit_invertx_var', False))
            
            # Restore horizontal line variables (backwards compatible - create if they don't exist)
            # Line 1
            if not hasattr(self, 'hline_enabled_var'):
                self.hline_enabled_var = tk.BooleanVar(value=False)
            self.hline_enabled_var.set(session_data.get('hline_enabled_var', False))
            
            if not hasattr(self, 'hline_elevation_var'):
                self.hline_elevation_var = tk.DoubleVar(value=0.0)
            self.hline_elevation_var.set(session_data.get('hline_elevation_var', 0.0))
            
            if not hasattr(self, 'hline_xmin_var'):
                self.hline_xmin_var = tk.DoubleVar(value=0.0)
            self.hline_xmin_var.set(session_data.get('hline_xmin_var', 0.0))
            
            if not hasattr(self, 'hline_xmax_var'):
                self.hline_xmax_var = tk.DoubleVar(value=1000.0)
            self.hline_xmax_var.set(session_data.get('hline_xmax_var', 1000.0))
            
            if not hasattr(self, 'hline_color_var'):
                self.hline_color_var = StringVar(value='red')
            self.hline_color_var.set(session_data.get('hline_color_var', 'red'))
            
            if not hasattr(self, 'hline_style_var'):
                self.hline_style_var = StringVar(value='solid')
            self.hline_style_var.set(session_data.get('hline_style_var', 'solid'))
            
            if not hasattr(self, 'hline_name_var'):
                self.hline_name_var = StringVar(value='H-Line 1')
            self.hline_name_var.set(session_data.get('hline_name_var', 'H-Line 1'))
            
            # Line 2
            if not hasattr(self, 'hline2_enabled_var'):
                self.hline2_enabled_var = tk.BooleanVar(value=False)
            self.hline2_enabled_var.set(session_data.get('hline2_enabled_var', False))
            
            if not hasattr(self, 'hline2_elevation_var'):
                self.hline2_elevation_var = tk.DoubleVar(value=0.0)
            self.hline2_elevation_var.set(session_data.get('hline2_elevation_var', 0.0))
            
            if not hasattr(self, 'hline2_xmin_var'):
                self.hline2_xmin_var = tk.DoubleVar(value=0.0)
            self.hline2_xmin_var.set(session_data.get('hline2_xmin_var', 0.0))
            
            if not hasattr(self, 'hline2_xmax_var'):
                self.hline2_xmax_var = tk.DoubleVar(value=1000.0)
            self.hline2_xmax_var.set(session_data.get('hline2_xmax_var', 1000.0))
            
            if not hasattr(self, 'hline2_color_var'):
                self.hline2_color_var = StringVar(value='blue')
            self.hline2_color_var.set(session_data.get('hline2_color_var', 'blue'))
            
            if not hasattr(self, 'hline2_style_var'):
                self.hline2_style_var = StringVar(value='solid')
            self.hline2_style_var.set(session_data.get('hline2_style_var', 'solid'))
            
            if not hasattr(self, 'hline2_name_var'):
                self.hline2_name_var = StringVar(value='H-Line 2')
            self.hline2_name_var.set(session_data.get('hline2_name_var', 'H-Line 2'))
            
            # Line 3
            if not hasattr(self, 'hline3_enabled_var'):
                self.hline3_enabled_var = tk.BooleanVar(value=False)
            self.hline3_enabled_var.set(session_data.get('hline3_enabled_var', False))
            
            if not hasattr(self, 'hline3_elevation_var'):
                self.hline3_elevation_var = tk.DoubleVar(value=0.0)
            self.hline3_elevation_var.set(session_data.get('hline3_elevation_var', 0.0))
            
            if not hasattr(self, 'hline3_xmin_var'):
                self.hline3_xmin_var = tk.DoubleVar(value=0.0)
            self.hline3_xmin_var.set(session_data.get('hline3_xmin_var', 0.0))
            
            if not hasattr(self, 'hline3_xmax_var'):
                self.hline3_xmax_var = tk.DoubleVar(value=1000.0)
            self.hline3_xmax_var.set(session_data.get('hline3_xmax_var', 1000.0))
            
            if not hasattr(self, 'hline3_color_var'):
                self.hline3_color_var = StringVar(value='green')
            self.hline3_color_var.set(session_data.get('hline3_color_var', 'green'))
            
            if not hasattr(self, 'hline3_style_var'):
                self.hline3_style_var = StringVar(value='solid')
            self.hline3_style_var.set(session_data.get('hline3_style_var', 'solid'))
            
            if not hasattr(self, 'hline3_name_var'):
                self.hline3_name_var = StringVar(value='H-Line 3')
            self.hline3_name_var.set(session_data.get('hline3_name_var', 'H-Line 3'))
            
            # Line 4
            if not hasattr(self, 'hline4_enabled_var'):
                self.hline4_enabled_var = tk.BooleanVar(value=False)
            self.hline4_enabled_var.set(session_data.get('hline4_enabled_var', False))
            
            if not hasattr(self, 'hline4_elevation_var'):
                self.hline4_elevation_var = tk.DoubleVar(value=0.0)
            self.hline4_elevation_var.set(session_data.get('hline4_elevation_var', 0.0))
            
            if not hasattr(self, 'hline4_xmin_var'):
                self.hline4_xmin_var = tk.DoubleVar(value=0.0)
            self.hline4_xmin_var.set(session_data.get('hline4_xmin_var', 0.0))
            
            if not hasattr(self, 'hline4_xmax_var'):
                self.hline4_xmax_var = tk.DoubleVar(value=1000.0)
            self.hline4_xmax_var.set(session_data.get('hline4_xmax_var', 1000.0))
            
            if not hasattr(self, 'hline4_color_var'):
                self.hline4_color_var = StringVar(value='orange')
            self.hline4_color_var.set(session_data.get('hline4_color_var', 'orange'))
            
            if not hasattr(self, 'hline4_style_var'):
                self.hline4_style_var = StringVar(value='solid')
            self.hline4_style_var.set(session_data.get('hline4_style_var', 'solid'))
            
            if not hasattr(self, 'hline4_name_var'):
                self.hline4_name_var = StringVar(value='H-Line 4')
            self.hline4_name_var.set(session_data.get('hline4_name_var', 'H-Line 4'))
            
            # Refresh all displays
            self.refresh_all_displays()
            
            messagebox.showinfo("Success", f"Session loaded successfully from:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session:\n{str(e)}")
    
    def copy_figure_to_clipboard(self, fig, plot_type="Figure"):
        """Copy a matplotlib figure to clipboard as an image"""
        try:
            # Save figure to a bytes buffer
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buf.seek(0)
            
            # Convert to PIL Image
            image = Image.open(buf)
            
            # Copy to clipboard (Windows-specific)
            output = io.BytesIO()
            image.save(output, format='BMP')
            data = output.getvalue()[14:]  # Remove BMP header
            output.close()
            buf.close()
            
            # Use Windows clipboard
            if CLIPBOARD_AVAILABLE:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                
                messagebox.showinfo("Success", f"{plot_type} copied to clipboard!\n\nYou can now paste it into:\n• Word documents\n• PowerPoint presentations\n• Image editors\n• Email clients")
            else:
                raise ImportError("win32clipboard not available")
            
        except ImportError:
            # Fallback method if win32clipboard is not available
            self.copy_figure_to_clipboard_fallback(fig, plot_type)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy {plot_type.lower()} to clipboard:\n{str(e)}")
    
    def copy_figure_to_clipboard_fallback(self, fig, plot_type="Figure"):
        """Fallback method to save figure to temp file and show instructions"""
        try:
            import tempfile
            import os
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"efa_{plot_type.lower().replace(' ', '_')}_temp.png")
            
            # Save figure to temp file
            fig.savefig(temp_file, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            
            # Show instructions
            messagebox.showinfo("Clipboard Copy", 
                               f"{plot_type} saved to temporary file:\n{temp_file}\n\n"
                               f"To copy to clipboard:\n"
                               f"1. Open the file in Paint or an image viewer\n"
                               f"2. Select All (Ctrl+A) and Copy (Ctrl+C)\n"
                               f"3. Paste into your target application")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {plot_type.lower()}:\n{str(e)}")
    
    def copy_throw_plot_to_clipboard(self):
        """Copy the current throw profile plot to clipboard"""
        if self.current_throw_fig is not None:
            self.copy_figure_to_clipboard(self.current_throw_fig, "Throw Profile Plot")
        else:
            messagebox.showwarning("No Plot", "No throw profile plot available to copy.\nPlease generate a plot first.")
    
    def copy_juxt_plot_to_clipboard(self):
        """Copy the current juxtaposition plot to clipboard"""
        if self.current_juxt_fig is not None:
            self.copy_figure_to_clipboard(self.current_juxt_fig, "Juxtaposition Plot")
        else:
            messagebox.showwarning("No Plot", "No juxtaposition plot available to copy.\nPlease generate a plot first.")
    
    def copy_juxt_unit_plot_to_clipboard(self):
        """Copy the current juxtaposition unit plot to clipboard"""
        if hasattr(self, 'current_juxt_unit_fig') and self.current_juxt_unit_fig is not None:
            self.copy_figure_to_clipboard(self.current_juxt_unit_fig, "Juxtaposition Unit Plot")
        else:
            messagebox.showwarning("No Plot", "No juxtaposition unit plot available to copy.\nPlease generate a plot first.")
    
    def copy_scenario_plot_to_clipboard(self):
        """Copy the current scenario plot to clipboard"""
        if self.current_scenario_fig is not None:
            self.copy_figure_to_clipboard(self.current_scenario_fig, "Scenario Plot")
        else:
            messagebox.showwarning("No Plot", "No scenario plot available to copy.\nPlease generate a plot first.")
    
    def copy_legend_to_clipboard(self):
        """Copy the current legend to clipboard"""
        if self.current_legend_fig is not None:
            self.copy_figure_to_clipboard(self.current_legend_fig, "Legend")
        else:
            messagebox.showwarning("No Legend", "No legend available to copy.\nPlease generate a plot with legend first.")
    
    def copy_all_plots_to_files(self):
        """Save all current plots to files for easy sharing"""
        from tkinter import filedialog
        import os
        
        # Ask user to select directory
        save_dir = filedialog.askdirectory(title="Select directory to save all plots")
        if not save_dir:
            return
        
        saved_files = []
        plot_name = self.plot_name.get().replace(" ", "_").replace("/", "_").replace("\\", "_")
        
        try:
            # Save throw plot
            if self.current_throw_fig is not None:
                throw_file = os.path.join(save_dir, f"{plot_name}_throw_profile.png")
                self.current_throw_fig.savefig(throw_file, format='png', dpi=300, bbox_inches='tight', 
                                              facecolor='white', edgecolor='none')
                saved_files.append(throw_file)
            
            # Save juxtaposition plot
            if self.current_juxt_fig is not None:
                juxt_file = os.path.join(save_dir, f"{plot_name}_juxtaposition.png")
                self.current_juxt_fig.savefig(juxt_file, format='png', dpi=300, bbox_inches='tight', 
                                             facecolor='white', edgecolor='none')
                saved_files.append(juxt_file)
            
            # Save scenario plot
            if self.current_scenario_fig is not None:
                scenario_file = os.path.join(save_dir, f"{plot_name}_scenario.png")
                self.current_scenario_fig.savefig(scenario_file, format='png', dpi=300, bbox_inches='tight', 
                                                 facecolor='white', edgecolor='none')
                saved_files.append(scenario_file)
            
            # Save legend
            if self.current_legend_fig is not None:
                legend_file = os.path.join(save_dir, f"{plot_name}_legend.png")
                self.current_legend_fig.savefig(legend_file, format='png', dpi=300, bbox_inches='tight', 
                                               facecolor='white', edgecolor='none')
                saved_files.append(legend_file)
            
            if saved_files:
                file_list = "\n".join([os.path.basename(f) for f in saved_files])
                messagebox.showinfo("Success", f"Plots saved successfully!\n\nFiles saved:\n{file_list}\n\nLocation: {save_dir}")
            else:
                messagebox.showwarning("No Plots", "No plots available to save.\nPlease generate plots first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save plots:\n{str(e)}")
    
    def refresh_all_plots(self):
        """Refresh all currently displayed plots"""
        try:
            # Refresh throw plot if data exists
            if hasattr(self, 'throwrange_df') and self.throwrange_df is not None:
                self.setup_throw_profile_plot()
            
            # Refresh juxtaposition plot if data exists
            if hasattr(self, 'ezcolor_df') and self.ezcolor_df is not None:
                self.setup_juxtaposition_plot()
                
            # Refresh scenario plot if data exists
            if hasattr(self, 'juxtlist') and self.juxtlist is not None:
                self.setup_scenario_plot()
            
            messagebox.showinfo("Success", "All plots have been refreshed!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh plots:\n{str(e)}")
    
    def refresh_all_displays(self):
        """Refresh all displays after loading a session"""
        try:
            # Refresh data input display
            self.update_file_listbox()
            if self.datadict:
                self.display_loaded_data()
            
            # Refresh data manipulation displays
            if self.fv_df is not None or self.hv_df is not None:
                self.display_length_depth_results()
            
            if self.nfv_df is not None or self.nhv_df is not None:
                self.display_shifted_data_results()
            
            if self.ld_dict is not None:
                self.display_mapped_data_results()
            
            # Refresh plot settings display
            self.update_color_settings_display()
            
            # Refresh plots if data exists
            if hasattr(self, 'throwrange_df') and self.throwrange_df is not None:
                self.setup_throw_profile_plot()
            
            if hasattr(self, 'ezcolor_df') and self.ezcolor_df is not None:
                self.setup_juxtaposition_plot()
                
            if hasattr(self, 'juxtlist') and self.juxtlist is not None:
                self.setup_scenario_plot()
            
            # Refresh output tables
            if hasattr(self, 'throwrange_df') and hasattr(self, 'juxtlist') and hasattr(self, 'throwarray'):
                self.setup_output_tables_data()
            
            # Refresh legends
            if hasattr(self, 'ecolor_df') and self.ecolor_df is not None:
                self.setup_legend_plot()
                
        except Exception as e:
            print(f"Warning: Some displays could not be refreshed: {e}")
    
    def update_file_listbox(self):
        """Update the file listbox with current innfiles"""
        self.datafiles_listbox.delete(0, tk.END)
        for fname in self.innfiles:
            display_name = fname.split('/')[-1] if '/' in fname else fname.split('\\')[-1]
            self.datafiles_listbox.insert(tk.END, display_name)

    def qc_plot_method(self, title='', figsize=(6,12), gridlines=1, linewidth=1, z_select='Z'):
        """
        Plot orignal footwall and hangingwall data for QC as a class method, with throw profile below
        """
        try:
            # Use instance variables as defaults if not provided
            ld_dict = self.ld_dict

            if not title:
                title = self.plot_name.get() + f' - mean strike/dip = {round(self.strike)}/{round(self.dip)}'
            if figsize == (6,12):
                figsize = (self.width.get(), self.height.get())
            if gridlines == 1:
                gridlines = self.gridvarf0.get()
            if linewidth == 1:
                linewidth = self.linewidth.get()
            if z_select == 'Z':
                z_select = self.z_select.get()
                
            # create two sub plots stacked vertically
            title = 'QC Plot - ' + title
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={'height_ratios': [3, 1]})

            # First subplot: juxtaposition plot
            for i in range(len(list(ld_dict.keys()))):
                horizon_name = list(ld_dict.keys())[i]
                print(f"Processing horizon: {horizon_name}")
                
                fv_length_list = ld_dict[horizon_name]['fv']['l']
                fv_depth_list = ld_dict[horizon_name]['fv']['d']
                hv_length_list = ld_dict[horizon_name]['hv']['l']
                hv_depth_list = ld_dict[horizon_name]['hv']['d']

                colorlist = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

                horizon_color = self.horizon_colors.get(horizon_name, colorlist[i % len(colorlist)])
                ax1.plot(fv_length_list, fv_depth_list, color=horizon_color, linewidth=linewidth)
                ax1.plot(hv_length_list, hv_depth_list, color=horizon_color, linewidth=linewidth, linestyle='--')
                ax1.scatter(fv_length_list, fv_depth_list, marker='^', color=horizon_color, label=f'{horizon_name} FW', s=30)
                ax1.scatter(hv_length_list, hv_depth_list, marker='v', color=horizon_color, label=f'{horizon_name} HW', s=30)



            # Format first subplot
            ax1.set_ylabel(f'{z_select} ({self.unit_depth})')
            #ax1.set_title(title)
            #ax1.invert_yaxis()
            ax1.legend(loc='best', fontsize=8)
            if gridlines:
                ax1.grid(True, alpha=0.3)
            
            # Second subplot: throw profile
            if self.fv_df is not None and self.hv_df is not None:
                for i in range(1, self.fv_df.shape[1]):
                    throw = self.fv_df.iloc[:,i] - self.hv_df.iloc[:,i]
                    horizon_name = self.fv_df.columns[i]
                    colorlist = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
                    horizon_color = self.horizon_colors.get(horizon_name, colorlist[i-1 % len(colorlist)])
                    ax2.plot(self.fv_df['length'], throw, 
                            color=horizon_color,
                            linewidth=linewidth,
                            label=horizon_name)
                
                ax2.set_xlabel(f'Length ({self.unit_xy})')
                ax2.set_ylabel(f'Throw ({self.unit_depth})')
                ax2.legend(loc='best', fontsize=8)
                if gridlines:
                    ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            import traceback
            print(f"Error in qc_plot_method: {traceback.format_exc()}")
            raise

    def throw_plot_method(self, fv_df=None, hv_df=None, h_color=None, title='', figsize=(6,12), gridlines=1, linewidth=1, meanthrow=1, showlegend=1,invertx = 1, z_select='Z'):
        """
        Create a throw profile plot as a class method.
        """
        # Use instance variables as defaults if not provided
        if fv_df is None:
            fv_df = self.nfv_df
        if hv_df is None:
            hv_df = self.nhv_df
        if h_color is None:
            h_color = self.ecolor_df
        if not title:
            title = self.plot_name.get() + f' - mean strike/dip = {round(self.strike)}/{round(self.dip)}'
        if figsize == (6,12):
            figsize = (self.width.get(), self.height.get())
        if gridlines == 1:
            gridlines = self.gridvarf0.get()
        if linewidth == 1:
            linewidth = self.linewidth.get()
        if meanthrow == 1:
            meanthrow = self.meanthrow_var.get()
        if showlegend == 1:
            showlegend = self.throw_leg_var.get()
        if invertx == 1:
            invertx = self.throw_invertx_var.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Throw - ' + title
        fig = plt.figure(figsize=figsize)
        throwrange = []
        throwlist = []
        for i in range(1,fv_df.shape[1]):
            throw = fv_df.iloc[:,i]-hv_df.iloc[:,i]
            throwlist.append(throw)
            # Add label for legend (use Alias if available, otherwise Horizon name)
            horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
            plt.plot(fv_df['length'],throw,color=h_color.loc[i-1,'Color'], linewidth = linewidth, label=horizon_label)
            tmin = round(np.nanmin(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            tmean = round(np.nanmean(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            tmax = round(np.nanmax(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            throwrange.append([h_color.loc[i-1,'Horizon'], h_color.loc[i-1,'Alias'],tmin,tmean,tmax])
        throwarray = np.array(throwlist)
        if meanthrow == 1:
            # Suppress RuntimeWarning about mean of empty slice (happens when all values are NaN)
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=RuntimeWarning)
                mean_throw = np.nanmean(throwarray, axis=0)
            plt.plot(fv_df['length'], mean_throw, color='black', linestyle='dotted', label='Mean Throw')
            
        plt.xlabel(f"Distance along mean strike ({self.unit_xy})")
        plt.ylabel(f"Throw ({self.z_select_to_unit()})")
        # Place text in the upper left corner of the plot
        plt.title(title)
        #Get compass directions from strike
        ur, ul = strike_to_compass(self.strike)
        # invert x axis if specified, invert compas directions
        if invertx:
            plt.gca().invert_xaxis()
            plt.title(ul, loc='right')
            plt.title(ur, loc='left')
        else:
            plt.title(ur, loc='right')
            plt.title(ul, loc='left')

        
        # Add legend at best location if enabled
        self.throwlegend_handles, self.throwlegend_labels = plt.gca().get_legend_handles_labels()
        if showlegend:
            plt.legend(loc='best', fontsize=8, framealpha=0.9)
        
        if gridlines == 1:
            plt.grid(alpha = 0.5)
        throwrange_df = pd.DataFrame(throwrange,columns=['Horizon', 'Alias', 'min_Throw', 'mean_throw','max_throw'])
        return(fig,throwrange_df, throwarray)


    def zone_color_plot_method(self, fv_df=None, hv_df=None, ld_dict=None, h_color=None, z_color=None, title='', figsize=(6,12), fv=1, hv=1, fill=1, gridlines=1, linewidth=1, showlegend=1,invertx = 1, z_select='Z', disp_orgpoints=1):
        """
        Basic horizon plotter function that uses the footwall and hangingwall files and zone colors as a class method.
        """
        # Use instance variables as defaults if not provided
        if fv_df is None:
            fv_df = self.nfv_df
        if hv_df is None:
            hv_df = self.nhv_df
        if ld_dict is None:
            ld_dict = self.ld_dict
        if h_color is None:
            h_color = self.ecolor_df
        if z_color is None:
            z_color = self.ezcolor_df
        if not title:
            title = self.plot_name.get() + f' - mean strike/dip: {round(self.strike)}/{round(self.dip)}'
        if figsize == (6,12):
            figsize = (self.width.get(), self.height.get())
        if gridlines == 1:
            gridlines = self.gridvarf1.get()
        if linewidth == 1:
            linewidth = self.linewidth.get()
        if fv == 1:
            fv = self.fv_var.get()
        if hv == 1:
            hv = self.hv_var.get()
        if fill == 1:
            fill = self.fill_var.get()
        if showlegend == 1:
            showlegend = self.juxt_leg_var.get()
        if disp_orgpoints == 1:
            disp_orgpoints = self.orgpoints.get()
        if invertx == 1:
            invertx = self.lith_invertx_var.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Lithology Juxtaposition - ' + title
        fig = plt.figure(figsize = figsize)
        
        # Track which zones are displayed for legend
        displayed_zones = set()
        
        if fill == 1:
            if hv_df.shape[1] > 2:
                for i in range(2,hv_df.shape[1]):
                    zone_idx = i-2
                    if fv == 1:
                        #plt.fill_between(fv_df['length'],fv_df.iloc[:,i-1],fv_df.iloc[:,i],color=z_color.loc[i-2,'Color'],alpha=0.5)
                        # Extract Length and depth values for horizon i-1 where values are not nan
                        fv_length = fv_df['length'][~np.isnan(fv_df.iloc[:,i-1])].values
                        fv_depth = fv_df.iloc[:,i-1][~np.isnan(fv_df.iloc[:,i-1])].values
                        # extract Length and depth values for horizon i where values are not nan
                        fv_length2 = fv_df['length'][~np.isnan(fv_df.iloc[:,i])].values
                        fv_depth2 = fv_df.iloc[:,i][~np.isnan(fv_df.iloc[:,i])].values
                        # Create polygon between fv_length and fv_length2 and use plt.fill to fill polygon
                        plt.fill(np.concatenate([fv_length, fv_length2[::-1]]),
                                 np.concatenate([fv_depth, fv_depth2[::-1]]),
                                 color=z_color.loc[zone_idx,'Color'], alpha=0.5)
                        displayed_zones.add(zone_idx)

                    if hv == 1:
                        #plt.fill_between(hv_df['length'],hv_df.iloc[:,i-1],hv_df.iloc[:,i],color=z_color.loc[i-2,'Color'],alpha=0.5)
                        hv_length = hv_df['length'][~np.isnan(hv_df.iloc[:,i-1])].values
                        hv_depth = hv_df.iloc[:,i-1][~np.isnan(hv_df.iloc[:,i-1])].values
                        # extract Length and depth values for horizon i where values are not nan
                        hv_length2 = hv_df['length'][~np.isnan(hv_df.iloc[:,i])].values
                        hv_depth2 = hv_df.iloc[:,i][~np.isnan(hv_df.iloc[:,i])].values
                        # Create polygon between hv_length and hv_length2 and use plt.fill to fill polygon
                        plt.fill(np.concatenate([hv_length, hv_length2[::-1]]),
                                 np.concatenate([hv_depth, hv_depth2[::-1]]),
                                 color=z_color.loc[zone_idx,'Color'], alpha=0.5)
                        displayed_zones.add(zone_idx)
        if fv == 1:
            for i in range(1,fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], linewidth = linewidth, label=f'{horizon_label} (FW)')
        if hv == 1:
            for i in range(1,fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', linewidth = linewidth, label=f'{horizon_label} (HW)')
        if fv == 0:
            for i in range(1,fv_df.shape[1]):
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], alpha = 0.1, linewidth = linewidth)
        if hv == 0:
            for i in range(1,fv_df.shape[1]):
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', alpha = 0.1, linewidth = linewidth)
        
         # Draw horizontal lines if enabled 
        if self.hline_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline_elevation_var.get(), xmin=self.hline_xmin_var.get(), xmax=self.hline_xmax_var.get(), colors=self.hline_color_var.get(), linestyles=self.hline_style_var.get(), linewidth=1.5, label=self.hline_name_var.get())
        
        if self.hline2_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline2_elevation_var.get(), xmin=self.hline2_xmin_var.get(), xmax=self.hline2_xmax_var.get(), colors=self.hline2_color_var.get(), linestyles=self.hline2_style_var.get(), linewidth=1.5, label=self.hline2_name_var.get())
        
        if self.hline3_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline3_elevation_var.get(), xmin=self.hline3_xmin_var.get(), xmax=self.hline3_xmax_var.get(), colors=self.hline3_color_var.get(), linestyles=self.hline3_style_var.get(), linewidth=1.5, label=self.hline3_name_var.get())

        if self.hline4_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline4_elevation_var.get(), xmin=self.hline4_xmin_var.get(), xmax=self.hline4_xmax_var.get(), colors=self.hline4_color_var.get(), linestyles=self.hline4_style_var.get(), linewidth=1.5, label=self.hline4_name_var.get())

        
        if disp_orgpoints == 1:
            for i in range(len(list(ld_dict.keys()))):
                #print(list(ld_dict.keys())[i])
                #print(h_color)
                #print(self.horizon_colors[list(ld_dict.keys())[i]])
                zfv = []
                for zfvi in range(0,len(ld_dict[list(ld_dict.keys())[i]]['fv']['l'])):
                    zfv.append(zfvi)
                zhv = []
                for zhvi in range(0,len(ld_dict[list(ld_dict.keys())[i]]['hv']['l'])):
                    zhv.append(zhvi)
            
            

                fv_length_list = ld_dict[list(ld_dict.keys())[i]]['fv']['l']
                fv_depth_list = ld_dict[list(ld_dict.keys())[i]]['fv']['d']
                hv_length_list = ld_dict[list(ld_dict.keys())[i]]['hv']['l']
                hv_depth_list = ld_dict[list(ld_dict.keys())[i]]['hv']['d']

                plt.scatter(fv_length_list, fv_depth_list, marker='^', color=self.horizon_colors[list(ld_dict.keys())[i]])
                plt.scatter(hv_length_list, hv_depth_list, marker='v', color=self.horizon_colors[list(ld_dict.keys())[i]])

        
        plt.xlabel(f"Distance along mean strike ({self.unit_xy})")
        plt.ylabel(f"Elevation ({self.z_select_to_unit()})")
        plt.title(title)
        ur, ul = strike_to_compass(self.strike)
        # invert x axis if specified, invert compas directions
        if invertx:
            plt.gca().invert_xaxis()
            plt.title(ul, loc='right')
            plt.title(ur, loc='left')
        else:
            plt.title(ur, loc='right')
            plt.title(ul, loc='left')
        
        # Add legend at best location if enabled
        if showlegend:
            # Get current legend handles and labels from the plot
            handles, labels = plt.gca().get_legend_handles_labels()
            
            # Add lithology zone patches to legend if fill is displayed
            if fill == 1 and len(displayed_zones) > 0:
                # Add separator comment (using empty handle)
                if len(handles) > 0:
                    handles.append(plt.Line2D([0], [0], color='none'))
                    labels.append('─── Lithology ───')
                
                # Add each displayed zone with lithology type
                for zone_idx in sorted(displayed_zones):
                    zone_label = z_color.loc[zone_idx, 'Alias'] if z_color.loc[zone_idx, 'Alias'] else z_color.loc[zone_idx, 'Zone']
                    lithology_type = z_color.loc[zone_idx, 'Lithology'] if 'Lithology' in z_color.columns else 'Undefined'
                    
                    # Combine zone name with lithology type
                    full_label = f"{zone_label} ({lithology_type})"
                    
                    zone_patch = Patch(facecolor=z_color.loc[zone_idx, 'Color'], 
                                      alpha=0.5, 
                                      label=full_label)
                    handles.append(zone_patch)
                    labels.append(full_label)
            
            # Display legend with all handles
            self.lithologyleg_handles = handles  # Store for legend plot
            self.lithologyleg_labels = labels    # Store for legend plot
            if len(handles) > 0:
                plt.legend(handles=handles, labels=labels, loc='best', fontsize=8, framealpha=0.9)
        
        if gridlines == 1:
            plt.grid(alpha=0.5)
        return(fig)

    def zone_unit_plot_method(self, fv_df=None, hv_df=None, ld_dict=None, h_color=None, zone_unit_colors=None, title='', figsize=(6,12), fv=1, hv=1, fill=1, gridlines=1, linewidth=1, showlegend=1, invertx=1, z_select='Z', disp_orgpoints=1):
        """
        Zone unit color plotter function that uses zone_unit_colors instead of lithology colors.
        """
        # Use instance variables as defaults if not provided
        if fv_df is None:
            fv_df = self.nfv_df
        if hv_df is None:
            hv_df = self.nhv_df
        if ld_dict is None:
            ld_dict = self.ld_dict
        if h_color is None:
            h_color = self.ecolor_df
        if zone_unit_colors is None:
            zone_unit_colors = self.zone_unit_colors
        if not title:
            title = self.plot_name.get() + f' - mean strike/dip: {round(self.strike)}/{round(self.dip)}'
        if figsize == (6,12):
            figsize = (self.width.get(), self.height.get())
        if gridlines == 1:
            gridlines = self.gridvarf_unit.get()
        if linewidth == 1:
            linewidth = self.linewidth.get()
        if fv == 1:
            fv = self.fv_unit_var.get()
        if hv == 1:
            hv = self.hv_unit_var.get()
        if fill == 1:
            fill = self.fill_unit_var.get()
        if showlegend == 1:
            showlegend = self.juxt_unit_leg_var.get()
        if disp_orgpoints == 1:
            disp_orgpoints = self.orgpoints_unit.get()
        if invertx == 1:
            invertx = self.unit_invertx_var.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Zone Juxtaposition - ' + title
        fig = plt.figure(figsize = figsize)
        
        # Track which zones are displayed for legend
        displayed_zones = set()
        
        if fill == 1:
            if hv_df.shape[1] > 2:
                for i in range(2, hv_df.shape[1]):
                    alpha = 0.5
                    zone_idx = i - 2
                    # Get zone alias for lookup in zone_unit_colors
                    if zone_idx < len(self.ezcolor_df):
                        zone_alias = self.ezcolor_df.loc[zone_idx, 'Alias']
                        zone_color = zone_unit_colors.get(zone_alias, '#ffffff')  # Default color if not found
                    else:
                        zone_color = '#ffffff'
                    
                    # set alpha to 0 if zone color is white
                    if zone_color.lower() == '#ffffff' or zone_color.lower() == 'white':
                        alpha = 0.0

                    if fv == 1:
                        # Extract Length and depth values for horizon i-1 where values are not nan
                        fv_length = fv_df['length'][~np.isnan(fv_df.iloc[:,i-1])].values
                        fv_depth = fv_df.iloc[:,i-1][~np.isnan(fv_df.iloc[:,i-1])].values
                        # extract Length and depth values for horizon i where values are not nan
                        fv_length2 = fv_df['length'][~np.isnan(fv_df.iloc[:,i])].values
                        fv_depth2 = fv_df.iloc[:,i][~np.isnan(fv_df.iloc[:,i])].values
                        # Create polygon between fv_length and fv_length2 and use plt.fill to fill polygon
                        plt.fill(np.concatenate([fv_length, fv_length2[::-1]]),
                                 np.concatenate([fv_depth, fv_depth2[::-1]]),
                                 color=zone_color, alpha=alpha)
                        displayed_zones.add(zone_idx)

                    if hv == 1:
                        hv_length = hv_df['length'][~np.isnan(hv_df.iloc[:,i-1])].values
                        hv_depth = hv_df.iloc[:,i-1][~np.isnan(hv_df.iloc[:,i-1])].values
                        # extract Length and depth values for horizon i where values are not nan
                        hv_length2 = hv_df['length'][~np.isnan(hv_df.iloc[:,i])].values
                        hv_depth2 = hv_df.iloc[:,i][~np.isnan(hv_df.iloc[:,i])].values
                        # Create polygon between hv_length and hv_length2 and use plt.fill to fill polygon
                        plt.fill(np.concatenate([hv_length, hv_length2[::-1]]),
                                 np.concatenate([hv_depth, hv_depth2[::-1]]),
                                 color=zone_color, alpha=alpha)
                        displayed_zones.add(zone_idx)
 

        
        if fv == 1:
            for i in range(1, fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(fv_df['length'], fv_df.iloc[:,i], color=h_color.loc[i-1,'Color'], linewidth=linewidth, label=f'{horizon_label} (FW)')
        
        if hv == 1:
            for i in range(1, fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(hv_df['length'], hv_df.iloc[:,i], color=h_color.loc[i-1,'Color'], linestyle='--', linewidth=linewidth, label=f'{horizon_label} (HW)')

        
        if fv == 0:
            for i in range(1, fv_df.shape[1]):
                plt.plot(fv_df['length'], fv_df.iloc[:,i], color=h_color.loc[i-1,'Color'], alpha=0.1, linewidth=linewidth)
        
        if hv == 0:
            for i in range(1, fv_df.shape[1]):
                plt.plot(hv_df['length'], hv_df.iloc[:,i], color=h_color.loc[i-1,'Color'], linestyle='--', alpha=0.1, linewidth=linewidth)

        # Draw horizontal lines if enabled 
        if self.hline_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline_elevation_var.get(), xmin=self.hline_xmin_var.get(), xmax=self.hline_xmax_var.get(), colors=self.hline_color_var.get(), linestyles=self.hline_style_var.get(), linewidth=1.5, label=self.hline_name_var.get())
        
        if self.hline2_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline2_elevation_var.get(), xmin=self.hline2_xmin_var.get(), xmax=self.hline2_xmax_var.get(), colors=self.hline2_color_var.get(), linestyles=self.hline2_style_var.get(), linewidth=1.5, label=self.hline2_name_var.get())
        
        if self.hline3_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline3_elevation_var.get(), xmin=self.hline3_xmin_var.get(), xmax=self.hline3_xmax_var.get(), colors=self.hline3_color_var.get(), linestyles=self.hline3_style_var.get(), linewidth=1.5, label=self.hline3_name_var.get())

        if self.hline4_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline4_elevation_var.get(), xmin=self.hline4_xmin_var.get(), xmax=self.hline4_xmax_var.get(), colors=self.hline4_color_var.get(), linestyles=self.hline4_style_var.get(), linewidth=1.5, label=self.hline4_name_var.get())

        if disp_orgpoints == 1:
            for i in range(len(list(ld_dict.keys()))):
                zfv = []
                for zfvi in range(0, len(ld_dict[list(ld_dict.keys())[i]]['fv']['l'])):
                    zfv.append(zfvi)
                zhv = []
                for zhvi in range(0, len(ld_dict[list(ld_dict.keys())[i]]['hv']['l'])):
                    zhv.append(zhvi)
            
                fv_length_list = ld_dict[list(ld_dict.keys())[i]]['fv']['l']
                fv_depth_list = ld_dict[list(ld_dict.keys())[i]]['fv']['d']
                hv_length_list = ld_dict[list(ld_dict.keys())[i]]['hv']['l']
                hv_depth_list = ld_dict[list(ld_dict.keys())[i]]['hv']['d']

                plt.scatter(fv_length_list, fv_depth_list, marker='^', color=self.horizon_colors[list(ld_dict.keys())[i]])
                plt.scatter(hv_length_list, hv_depth_list, marker='v', color=self.horizon_colors[list(ld_dict.keys())[i]])

        plt.xlabel(f"Distance along mean strike ({self.unit_xy})")
        plt.ylabel(f"Elevation ({self.z_select_to_unit()})")
        plt.title(title)
        ur, ul = strike_to_compass(self.strike)
        # invert x axis if specified, invert compas directions
        if invertx:
            plt.gca().invert_xaxis()
            plt.title(ul, loc='right')
            plt.title(ur, loc='left')
        else:
            plt.title(ur, loc='right')
            plt.title(ul, loc='left')
        
        # Add legend at best location if enabled
        if showlegend:
            # Get current legend handles and labels from the plot
            handles, labels = plt.gca().get_legend_handles_labels()
            
            # Add unit zone patches to legend if fill is displayed
            if fill == 1 and len(displayed_zones) > 0:
                # Add separator comment (using empty handle)
                if len(handles) > 0:
                    handles.append(plt.Line2D([0], [0], color='none'))
                    labels.append('─── Zone Units ───')
                
                # Add each displayed zone with unit color
                for zone_idx in sorted(displayed_zones):
                    if zone_idx < len(self.ezcolor_df):
                        zone_alias = self.ezcolor_df.loc[zone_idx, 'Alias']
                        zone_color = zone_unit_colors.get(zone_alias, '#ffffff')
                        
                        zone_patch = Patch(facecolor=zone_color, 
                                          alpha=0.5, 
                                          label=zone_alias)
                        handles.append(zone_patch)
                        labels.append(zone_alias)
            
            # Display legend with all handles
            self.unitlegend_handles = handles
            self.unitlegend_labels = labels
            if len(handles) > 0:
                plt.legend(handles=handles, labels=labels, loc='best', fontsize=8, framealpha=0.9)
        
        if gridlines == 1:
            plt.grid(alpha=0.5)
        return(fig)

    def zone_juxtscenario_plot_method(self, fv_df=None, hv_df=None, ld_dict=None, h_color=None, z_color=None, title='', figsize=(6,12), gridlines=1, linewidth=1, fv=1, hv=1, apex=1, apexid=1, showlegend=1, invertx=1, z_select='Z', disp_orgpoints=1):
        """
        Juxtaposition scenario plot as a class method.
        """
        # Use instance variables as defaults if not provided
        if fv_df is None:
            fv_df = self.nfv_df
        if hv_df is None:
            hv_df = self.nhv_df
        if ld_dict is None:
            ld_dict = self.ld_dict
        if h_color is None:
            h_color = self.ecolor_df
        if z_color is None:
            z_color = self.ezcolor_df
        if not title:
            title = self.plot_name.get() + f' - mean strike/dip: {round(self.strike)}/{round(self.dip)}'
        if figsize == (6,12):
            figsize = (self.width.get(), self.height.get())
        if gridlines == 1:
            gridlines = self.gridvarf2.get()
        if linewidth == 1:
            linewidth = self.linewidth.get()
        if fv == 1:
            fv = self.fvt6_var.get()
        if hv == 1:
            hv = self.hvt6_var.get()
        if apex == 1:
            apex = self.apex_var.get()
        if apexid == 1:
            apexid = self.apexid_var.get()
        if showlegend == 1:
            showlegend = self.scenario_leg_var.get()
        if invertx == 1:
            invertx = self.scen_invertx_var.get()
        if disp_orgpoints == 1:
            disp_orgpoints = self.orgpoints2.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Juxtaposition Scenario - ' + title
        warning = ''
        fig = plt.figure(figsize=figsize)
        fv_poly_x = np.append(fv_df['length'].to_numpy(),fv_df['length'].to_numpy()[::-1])
        hv_poly_x = np.append(hv_df['length'].to_numpy(),hv_df['length'].to_numpy()[::-1])
        
        # Track juxtaposition types for legend (color -> label mapping)
        juxt_types_displayed = {}
        
        def create_safe_polygon(x_coords, y_coords):
            """
            Safely create a polygon from coordinates, handling NaN values and other issues.
            
            Args:
                x_coords: Array of x coordinates
                y_coords: Array of y coordinates
            
            Returns:
                shapely.geometry.Polygon or None if creation fails
            """
            try:
                # Remove NaN and infinite values
                valid_mask = np.isfinite(x_coords) & np.isfinite(y_coords)
                x_clean = x_coords[valid_mask]
                y_clean = y_coords[valid_mask]
                
                if len(x_clean) < 3:
                    return None
                
                # Remove duplicate consecutive points
                coords = list(zip(x_clean, y_clean))
                unique_coords = []
                for i, coord in enumerate(coords):
                    if i == 0 or coord != coords[i-1]:
                        unique_coords.append(coord)
                
                if len(unique_coords) < 3:
                    return None
                
                # Create polygon
                polygon = Polygon(unique_coords)
                
                # Fix self-intersections if needed
                if not polygon.is_valid:
                    polygon = polygon.buffer(0)
                
                return polygon if polygon.is_valid else None
                
            except Exception:
                return None
        
        juxt_list = []
        for i in range(2,fv_df.shape[1]):
            fv_poly_y = np.append(fv_df.iloc[:,i-1].to_numpy(),fv_df.iloc[:,i].to_numpy()[::-1])
            fv_poly = create_safe_polygon(fv_poly_x, fv_poly_y)
            if fv_poly is None:
                continue  # Skip this iteration if polygon creation failed
            for j in range(2,hv_df.shape[1]):
                hv_poly_y = np.append(hv_df.iloc[:,j-1].to_numpy(),hv_df.iloc[:,j].to_numpy()[::-1])
                hv_poly = create_safe_polygon(hv_poly_x, hv_poly_y)
                if hv_poly is None:
                    continue  # Skip this iteration if polygon creation failed
                new_color,fv_type,hv_type = juxtaposition_color(z_color.loc[i-2,'Color'],z_color.loc[j-2,'Color'])
                
                # Create juxtaposition type label for legend
                juxt_label = f"{fv_type}-{hv_type}"
                juxt_types_displayed[new_color] = juxt_label
                
                try:
                    p_intersect =  fv_poly.intersection(hv_poly)
                    if p_intersect.geom_type == 'MultiPolygon':
                        polylist = list(p_intersect.geoms)
                        for poly in polylist:
                            xp,yp = poly.exterior.xy
                            plt.fill(xp,yp,color=new_color)
                            ym = max(yp)
                            xm = list(xp)[list(yp).index(max(yp))]
                            juxt_list.append([list(fv_df)[i-1]+'-'+list(fv_df)[i],list(hv_df)[j-1]+'-'+list(hv_df)[j],z_color.loc[i-2,'Alias'],z_color.loc[j-2,'Alias'],round(xm,0),round(ym,0),fv_type,hv_type])
                    else:
                        try:
                            xp,yp = p_intersect.exterior.xy
                            plt.fill(xp,yp,color=new_color)
                            ym = max(yp)
                            xm = list(xp)[list(yp).index(max(yp))]
                            juxt_list.append([list(fv_df)[i-1]+'-'+list(fv_df)[i],list(hv_df)[j-1]+'-'+list(hv_df)[j],z_color.loc[i-2,'Alias'],z_color.loc[j-2,'Alias'],round(xm,2),round(ym,2),fv_type,hv_type])
                        except:
                            if p_intersect.geom_type == 'GeometryCollection':
                                for geom in p_intersect.geoms:
                                    if geom.geom_type == 'Polygon':
                                        xp,yp = geom.exterior.xy
                                        plt.fill(xp,yp,color=new_color)
                                        ym = max(yp)
                                        xm = list(xp)[list(yp).index(max(yp))]
                                        juxt_list.append([list(fv_df)[i-1]+'-'+list(fv_df)[i],list(hv_df)[j-1]+'-'+list(hv_df)[j],z_color.loc[i-2,'Alias'],z_color.loc[j-2,'Alias'],round(xm,0),round(ym,0),fv_type,hv_type])
                except:
                    warning = 'Topolygy Error, juxtaposition polygon not displayed properly'
                    #print(warning)
        
        for i in range(1,fv_df.shape[1]):
            plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], linewidth = linewidth, alpha = 0.1)
        for i in range(1,fv_df.shape[1]):
            plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', linewidth = linewidth, alpha = 0.1)
            
        if fv == 1:
            for i in range(1,fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], linewidth = linewidth, label=f'{horizon_label} (FW)')
        if hv == 1:
            for i in range(1,fv_df.shape[1]):
                horizon_label = h_color.loc[i-1,'Alias'] if h_color.loc[i-1,'Alias'] else h_color.loc[i-1,'Horizon']
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', linewidth = linewidth, label=f'{horizon_label} (HW)')
        juxt_df = pd.DataFrame(juxt_list,columns=['FV_Zone','HV_Zone','FV_Alias','HV_Alias','Length','Elevation','FV_Lith','HV_Lith'])
        if apex == 1:
            plt.scatter(juxt_df['Length'], juxt_df['Elevation'], marker = 'x', color = 'red')
        if apexid == 1:
            for jindex, jrow in juxt_df.iterrows():
                plt.text(jrow['Length'], jrow['Elevation'],jindex, color = 'darkred')

         # Draw horizontal lines if enabled 
        if self.hline_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline_elevation_var.get(), xmin=self.hline_xmin_var.get(), xmax=self.hline_xmax_var.get(), colors=self.hline_color_var.get(), linestyles=self.hline_style_var.get(), linewidth=1.5, label=self.hline_name_var.get())
        
        if self.hline2_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline2_elevation_var.get(), xmin=self.hline2_xmin_var.get(), xmax=self.hline2_xmax_var.get(), colors=self.hline2_color_var.get(), linestyles=self.hline2_style_var.get(), linewidth=1.5, label=self.hline2_name_var.get())
        
        if self.hline3_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline3_elevation_var.get(), xmin=self.hline3_xmin_var.get(), xmax=self.hline3_xmax_var.get(), colors=self.hline3_color_var.get(), linestyles=self.hline3_style_var.get(), linewidth=1.5, label=self.hline3_name_var.get())

        if self.hline4_enabled_var.get() and self.hline_color_var.get().lower() != 'none':
            plt.hlines(y=self.hline4_elevation_var.get(), xmin=self.hline4_xmin_var.get(), xmax=self.hline4_xmax_var.get(), colors=self.hline4_color_var.get(), linestyles=self.hline4_style_var.get(), linewidth=1.5, label=self.hline4_name_var.get())


        if disp_orgpoints == 1:
            for i in range(len(list(ld_dict.keys()))):
                #print(list(ld_dict.keys())[i])
                #print(h_color)
                #print(self.horizon_colors[list(ld_dict.keys())[i]])
                zfv = []
                for zfvi in range(0,len(ld_dict[list(ld_dict.keys())[i]]['fv']['l'])):
                    zfv.append(zfvi)
                zhv = []
                for zhvi in range(0,len(ld_dict[list(ld_dict.keys())[i]]['hv']['l'])):
                    zhv.append(zhvi)
            
                z2 = len(ld_dict[list(ld_dict.keys())[i]]['hv']['l'])

                plt.scatter(ld_dict[list(ld_dict.keys())[i]]['fv']['l'],ld_dict[list(ld_dict.keys())[i]]['fv']['d'], marker = '^', color = self.horizon_colors[list(ld_dict.keys())[i]])
                plt.scatter(ld_dict[list(ld_dict.keys())[i]]['hv']['l'],ld_dict[list(ld_dict.keys())[i]]['hv']['d'], marker = 'v', color = self.horizon_colors[list(ld_dict.keys())[i]])
        
        plt.title(title)
        ur, ul = strike_to_compass(self.strike)
        # invert x axis if specified, invert compas directions
        if invertx:
            plt.gca().invert_xaxis()
            plt.title(ul, loc='right')
            plt.title(ur, loc='left')
        else:
            plt.title(ur, loc='right')
            plt.title(ul, loc='left')
        #plt.title(ul, loc='left')
        #plt.title(ur, loc='right')
        plt.xlabel(f"Distance along mean strike ({self.unit_xy})")
        plt.ylabel(f"Elevation  ({self.z_select_to_unit()})")
        
        # Add legend at best location if enabled
        if showlegend:
            # Get current legend handles and labels from the plot
            handles, labels = plt.gca().get_legend_handles_labels()
            
            # Add juxtaposition type patches to legend if any exist
            if len(juxt_types_displayed) > 0:
                # Add separator
                if len(handles) > 0:
                    handles.append(plt.Line2D([0], [0], color='none'))
                    labels.append('─── Juxtaposition ───')
                
                # Define the desired order of juxtaposition types
                juxt_order = {
                    'green': 'Good Res-Good Res',
                    'yellow': 'Good Res-Poor Res',
                    'orange': 'Poor Res-Poor Res',
                    'black': 'Res-SR',
                    'LightGray': 'Res-No Res',
                    'DarkGray': 'No Res-No Res',
                    'azure': 'Undefined-Any'
                }
                
                # Add patches in order, only for types that are displayed
                for color, default_label in juxt_order.items():
                    if color in juxt_types_displayed:
                        # Use the actual label from the data
                        juxt_label = juxt_types_displayed[color]
                        juxt_patch = Patch(facecolor=color, alpha=1.0, label=juxt_label)
                        handles.append(juxt_patch)
                        labels.append(juxt_label)
            
            # Display legend with all handles
            self.scenariolegend_handles = handles
            self.scenariolegend_labels = labels
            if len(handles) > 0:
                plt.legend(handles=handles, labels=labels, loc='best', fontsize=8, framealpha=0.9)
        
        if gridlines == 1:
            plt.grid(alpha=0.5)
        return(fig,juxt_df,warning)



    def z_select_to_unit(self):
        """
        Convert z_select string to unit string for axis labeling. z_options = ['Z', 'TWT auto', 'Depth 1']
        """
        if self.z_select.get() == 'Z':
            return f" {self.unit_depth} or ms twt"
        elif self.z_select.get() == 'Depth 1':
            return f"{self.unit_depth}"
        elif self.z_select.get() == 'TWT auto':
            return 'ms twt'
        else:
            return ''  # Default to empty if unknown


    def show_about(self):
        about_text = f"""EFA Juxtaposition Analysis

Version: {self.VERSION}
Build Date: {self.BUILD_DATE}
Author: {self.AUTHOR}

Features:
• Interactive geological analysis
• Mouse hover functionality on plots
• Clipboard integration for all plots
• Professional visualization tools
• Session save/load capabilities
• CSV export functionality

License: MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

© 2025 - Equinor ASA"""
        messagebox.showinfo("About EFA", about_text)
    
    def show_help(self):
        """Display comprehensive help window with text and images"""
        help_window = tk.Toplevel(self)
        help_window.title("EFA Juxtaposition Analysis - User Guide")
        try:
            help_window.iconbitmap('help_images/efa_icon.ico')
        except (FileNotFoundError, tk.TclError):
            # Icon file not found or invalid - continue without icon
            pass
        help_window.geometry("900x700")
        
        # Create main container with canvas for scrolling
        main_frame = ttk.Frame(help_window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_frame, bg='white')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        # Create frame inside canvas for content
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add content to scrollable frame
        self._populate_help_content(scrollable_frame)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Add close button at bottom
        button_frame = ttk.Frame(help_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(button_frame, text="Close", command=help_window.destroy).pack(side=tk.RIGHT)
        
        # Cleanup mouse wheel binding when window closes
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            help_window.destroy()
        help_window.protocol("WM_DELETE_WINDOW", on_closing)
    
    def _populate_help_content(self, frame):
        """Populate the help window with formatted content"""
        # Configure text styles
        title_font = ('Arial', 16, 'bold')
        heading_font = ('Arial', 12, 'bold')
        subheading_font = ('Arial', 11, 'bold')
        body_font = ('Arial', 10)
        
        # Main title
        title_label = ttk.Label(frame, text="EFA Juxtaposition Analysis - User Guide", 
                               font=title_font, foreground='#0066cc')
        title_label.pack(pady=(20, 10), padx=20)
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', padx=20, pady=5)
        
        # Table of Contents
        toc_frame = ttk.LabelFrame(frame, text="Table of Contents", padding=10)
        toc_frame.pack(fill='x', padx=20, pady=10)
        
        toc_text = """1. Getting Started
2. Data Input
3. Data Manipulation
4. Plot Settings
5. Plot Types
6. Throw Plot
7. Zone Juxtaposition Plot
8. Lithology Juxtaposition Plot
9. Juxtaposition Scenario Plot
10. Exporting Results
11. Session Management"""
        
        toc_label = ttk.Label(toc_frame, text=toc_text, font=body_font, justify='left')
        toc_label.pack(anchor='w')
        
        # Section 1: Getting Started
        self._add_help_section(frame, "1. Getting Started", heading_font, body_font,
            """The EFA (Efficient Fault Analysis) Juxtaposition tool is designed for quick analysis of fault displacement and juxtaposition for single faults. It uses mapped fault contact points exported from Petrel, to generate throw profiles and juxtaposition plots, and calculate statistics on fault displacement.
            
Fault contact points represent the mapped footwall and hanging wall intersections between horizons and a given fault plane. The fault contact points used in this workflow, have been mapped in Petrel, converted to multipoints, depth converted (if needed), and exported as Petrel points with attributes format. The tool supports both time and depth mapped data, and requieres at least one fault contact point file as input. A single fault contact point file contains both the footwall and hanging wall cut-off points for one seismic horizon. Multiple fault contact point files can be loaded to represent multiple horizons, and the tool supports vertical shifting of horizons to account for non-mapped stratigraphy or thin units not resolvable on seismic data.

Key Concepts:
• Footwall (FW): The rock mass below the fault plane
• Hanging wall (HW): The rock mass above the fault plane
• Juxtaposition: Alignment of different geological units across the fault
• Throw: The vertical displacement across the fault
• Fault Contact points (FC points): The Footwall and haning wall intersection points between a seismic horizon and the fault plane""")
        
        # Add fault diagram image
        self._add_help_image(frame, "help_images/fault_diagram.png", 
                             caption="Figure 1: Relationship between footwall, hanging wall, fault plane, and fault contact points")
        
        # Add ada load image
        self._add_help_image(frame, "help_images/example_datainput.png", 
                             caption="Figure 2: Example of data import and preview")

        # Section 2: Loading Data
        self._add_help_section(frame, "2. Data Input", heading_font, body_font,
            """Step 1: Select input file format:
• Petrel fault contact points, converted to points and exported as Petrel points with attributes format - recomended format
• Cegal fault contact points, converted to points and exported as Petrel points with attributes format

Step 2: Select input fault contact files and set correct order:
• Click 'Select Horizon Files' button
• In the file dialog, select one or several fault contact point files in the chosen format
• Each file must contain both footwall and hanging wall cut-off points for one seismic horizon
• Files will appear in the 'selected files' listbox
• If files are not in the correct order (from shallow to deep), click 'Sort File Order' and use buttons to move files up or down in the list

Step 3: Load data to database
• Click 'Load Data to Database' button
• The application will read the selected files and extract footwall and hanging wall cut-off points
• The data will now appear in the Data Preview window
• QC the file structure and data consistency to ensure it looks correct and all files are consistent.""")
   

        # Add qc plot image
        self._add_help_image(frame, "help_images/example_qcplot.png", 
                             caption="Figure 3: Example QC plot tab, where throw and juxtaposition of mapped points can be evaluated")
        
        # Section 3: Data conversion and horizon shift
        self._add_help_section(frame, "3. Data Manipulation", heading_font, body_font,
            """Purpose: Transforms XYZ coordinates to a 2D representation along the fault and execute horizon shifts

Step 1: Select Z-value field
• Z = vertical scale in Depth or TWT depending on if data were mapped in depth or time
• TWT auto = Two Way Time (ms), only appers in dataset if data has been depth converted
• Depth 1 = Depth in meters or feet, only appers in dataset if data has been depth converted

Step 2: Click 'Convert to Length/Depth'
• Algorithm converts the mapped 2D fault contact points to a 2D coordinate system represented by length along fault strike and depth
• Projects 3D points onto 2D fault plane
• Resamples the data to equal spacing along fault strike.
• Separates footwall and hangingwall data
• The converted data will appear in the 'Length/Depth Data Preview' window
• QC the data to ensure datapoints are in the correct order. Red data points indicate data out of order, theese data will be truncated when executing horizon shift.
• The QC plot, in the 'QC Plot' tab, can also be used to verify data quality and order. It shows both fault maped fault juxtaposition in addition to fault throw along strike.

Step 3: 'Edit Horizon Shift'
• This step is optional. It allows for vertical shifting one or several input fault-horion intersection files.
• Vertically shfiting horizons can e.g. account for non-mapped stratigraphy or thin units not resolvable on seismic data. It can also be used to test different uncertainty scenarios.
• Nearby well data can e.g be used as input to horizon shfiting to infer thicknesses used for shifting.
• To execute horizon shfits:
    1. Click 'Edit Horizon Shift' button
    2. Click on horizon to be shifted to highlight it
    3. In the lower part of the window, enter one or several shift values, and click 'Uptade Row' to add the shift(s) to the table
        • Shifts are relative to the original horizon position
        • Positive values shift the horizon upward
        • Negative values shift the horizon downward
        • Zero value includes the original horizon position, and must be included if the original horizon position is to be part of the analysis
        • Shifts are entered from shallow to deep, i.e. upward shifts before zero, and downward shifts after zero
        • Use 'nan' to remove created horizon shifts
    4. Repeat for other horizons as needed
    5. Click 'Save Changes' to store the shift values
  
Step 4: click 'Execute Shift'
• Applies the defined horizon shifts and displays them in the 'Shifted Data' tab
• Shifted horizons are used in the subsequent juxtaposition analysis""")
        
        
        # Horizon shift concept figure
        self._add_help_image(frame, "help_images/example_HorizonShift.png",
                           caption="Figure 4: Example of Horizon Shift Table in the application")
        
        # Horizon shift concept figure
        self._add_help_image(frame, "help_images/example_Horizon_Shift_Concept.png",
                           caption="Figure 5: Conceptual illustration of using a stratigraphic log to define horizon shifts of h1 and h4")

        self._add_help_image(frame, "help_images/example_shift_datatab.png",
                           caption="Figure 6: Example of shifted horizons displayed in the 'Shifted Data' tab")


        # Section 4: Horizon and zone names and color definitions
        self._add_help_section(frame, "4. Plot Settings", heading_font, body_font,
            """Purpose: In the 'Plot Settings' tab, define colors and names and lithology for horizons and zone units. Note that theese settings can be changed at any time.
            
Step 1: Define plot name
• Enter a descriptive name for the plots in the 'Plot Name' field

Step 2: Edit Horizon Alias and Colors
• If desiered write an alias name for each horizon in the 'Alias' column. This name will appear in the plot legends.
• Click on the color box to open a color picker and select a color for each horizon.

Step 3: Edit Zone Unit Colors and Names
• Define geological unit names for the units defined between each horizon.
• Select lithology for each zone unit in the 'Zone Unit Colors' table.
• Click on the color box to open a color picker and select a color for each zone unit.
    Note! If the color don't change, check that luminesence is not set to 0 in the color picker.
            
Step 4: click 'Generate All Plots'
• This will generate all four plot types using the current settings and display them in their respective tabs.
• Different output tables are also generated in the 'Data Output' tab for further analysis and export.      
            """)


        # Add plot settings image
        self._add_help_image(frame, "help_images/example_plot_settings.png", 
                             caption="Figure 7: Example of data import and preview")

        self._add_help_section(frame, "5. Plot Types", heading_font, body_font,
            """After clicking 'Generate All Plots' four different plot types are created and displayed in their respective tabs. Each plot type has specific features and functionalities as described below:
• Each plot tab contains a legend area, and a plot area.
• Tick boxes above the plots can be used to turn on/off different plot elements, display original points, invert x-axis, and show/hide legends.
• Buttons below the plot can be used to manipulate plot size, zoom in/out, and export data""")




        # Add plot settings image
        self._add_help_image(frame, "help_images/example_throw_plot.png", 
                             caption="Figure 8: Example of throw profile plot")

        self._add_help_section(frame, "6. Throw Plot", heading_font, body_font,
            """

The throw profile plot is displayed in the 'Throw Plot' tab:
• Shows throw (vertical displacement) along mean fault strike
• Each line represents one fault-horizon intersection
• Mean throw line (dotted) shows average throw for all horizons present at that location
• Additional throw statistics can be found in the 'Data Output' tab
• Note! If a horizon is shifted, the throw will be the same as the original horizon, unless truncated. If a horizon color is missing, it might thus be behind another one.""")

        # Add plot settings image
        self._add_help_image(frame, "help_images/example_zone_juxtaposition_plot.png", 
                             caption="Figure 9: Example of zone juxtaposition plot")

        self._add_help_section(frame, "7. Zone Juxtaposition Plot", heading_font, body_font,
            """
                 
The Zone Juxtaposition Plot is displayed in the 'Zone Juxtaposition Plot' tab:
• Displays which units are juxtaposed using the zone color definitions in the 'Plot Settings' tab
• Colors for the footwall and haning wall zones are displayed with 50% transparency to visualize overlap
• The plot can either be used to visualize e.g. formation colors for all zones, or only visualize juxtapositions for selected zones by setting the other colors to white
• Footwall horizons: Solid lines with ▲ markers
• Hangingwall horizons: Dashed lines with ▼ markers""")

        # Add plot settings image
        self._add_help_image(frame, "help_images/example_lithology_juxtaposition_plot.png", 
                             caption="Figure 10: Example of lithology juxtaposition plot")

        self._add_help_section(frame, "8. Lithology Juxtaposition Plot", heading_font, body_font,
            """

Lithology Juxtaposition Plot:
• Displays which lithology types are juxtaposed using the lithology color definitions in the 'Plot Settings' tab
• Colors for the footwall and haning wall zones are displayed with 50% transparency to visualize overlap
• Footwall horizons: Solid lines with ▲ markers
• Hangingwall horizons: Dashed lines with ▼ markers""")


        # Add plot settings image
        self._add_help_image(frame, "help_images/example_juxtaposition_scenario_plot.png", 
                             caption="Figure 11: Example of juxtaposition scenario plot")

        self._add_help_section(frame, "9. Juxtaposition Scenario Plot", heading_font, body_font,
            """

Juxtaposition Scenario Plot:
• Displays classified juxtaposition types based on lithology definitions in the 'Plot Settings' tab
• Different colors represent different juxtaposition types (e.g. Good Res-Good Res, Good Res-Poor Res, etc.)
• Colors only present in areas of juxtaposition between footwall and haning wall
• Red markers indicate the apex point of each juxtaposition scenario; mouse-over to get juxtaposition information
• Apex IDs correspond to Juxtaposition Scenarios entered in the 'Output tables' tab""")
        
        # Add example juxtaposition plot image
        self._add_help_image(frame, "help_images/example_output_tables.png",
                           caption="Figure 12: Example juxtaposition plot showing footwall and hanging wall horizons")
        
        
        # Section 10: Exporting
        self._add_help_section(frame, "10. Exporting Results", heading_font, body_font,
            """Copy to Clipboard:
• Edit menu → Copy [Plot Type] to Clipboard
• Paste directly into PowerPoint, Word, etc.
• High-resolution images maintained

Export All Plots:
• File menu → Export All Plots
• Saves all three plots as PNG files
• Automatic naming with timestamp

Export Data:
• CSV export buttons in each tab
• Length/depth data
• Juxtaposition results
• Scenario analysis data

Session Management:
• File menu → Save Session
• Saves all data, settings, and plots
• Load Session restores complete state""")
        
        # Section 11: Session Management
        self._add_help_section(frame, "11. Session Management", heading_font, body_font,
            """Save Session:
• File menu → Save Session
• Saves .pkl file with all data:
  - Loaded horizon files
  - Converted length/depth data
  - Horizon shifts
  - Color assignments
  - Plot settings
  - Current state

Load Session:
• File menu → Load Session
• Select previously saved .pkl file
• Restores complete working state
• Continue work from where you left off

Reset Application:
• File menu → Reset Application
• Clears all data and plots
• Returns to initial state
• Useful for starting new analysis

Keyboard Shortcuts:
• Ctrl+S: Save Session
• Ctrl+O: Load Session
• Ctrl+Q: Quit Application
• F1: Show Help (this window)""")
        
        # Tips and Best Practices
        tips_frame = ttk.LabelFrame(frame, text="💡 Tips and Best Practices", padding=10)
        tips_frame.pack(fill='x', padx=20, pady=10)
        
        tips_text = """• Save your session frequently to preserve work
• Use consistent units throughout (all meters or all feet)
• Check QC Plot after conversion to verify data quality
• Start with no horizon shifts, then test scenarios
• Use descriptive plot names for documentation
• Export plots at high resolution for publications, e.g. as .svg files
• Color-code horizons by formation for clarity
• Review mean strike/dip values for quality control"""
        
        tips_label = ttk.Label(tips_frame, text=tips_text, font=body_font, justify='left')
        tips_label.pack(anchor='w')
        
        # Troubleshooting
        trouble_frame = ttk.LabelFrame(frame, text="⚠️ Troubleshooting", padding=10)
        trouble_frame.pack(fill='x', padx=20, pady=10)
        
        trouble_text = """Problem: Plots are blank or incomplete
Solution: Check that horizons were converted to length/depth first

Problem: Colors don't match between plots
Solution: Use Edit Horizon Colors to standardize colors

Problem: Data looks incorrect
Solution: Check Z-axis interpretation (Depth vs Elevation)

Problem: Plot not showing after loading session
Solution: Click 'Generate All Plots' to refresh

Problem: Application is slow
Solution: Reduce number of data points or plot size"""
        
        trouble_label = ttk.Label(trouble_frame, text=trouble_text, font=body_font, justify='left')
        trouble_label.pack(anchor='w')
        
        # Footer
        footer_label = ttk.Label(frame, 
                                text=f"EFA Juxtaposition Analysis {self.VERSION} | © 2025 Equinor ASA | Author: {self.AUTHOR}",
                                font=('Arial', 9), foreground='gray')
        footer_label.pack(pady=(20, 20))
    
    def _add_help_section(self, parent, title, title_font, body_font, content):
        """Helper method to add a formatted help section"""
        # Section frame
        section_frame = ttk.Frame(parent)
        section_frame.pack(fill='x', padx=20, pady=10)
        
        # Section title
        title_label = ttk.Label(section_frame, text=title, font=title_font, 
                               foreground='#0066cc')
        title_label.pack(anchor='w', pady=(5, 5))
        
        # Section content
        content_label = ttk.Label(section_frame, text=content, font=body_font, 
                                 justify='left', wraplength=800)
        content_label.pack(anchor='w', padx=10)
        
        # Separator
        ttk.Separator(section_frame, orient='horizontal').pack(fill='x', pady=(10, 0))
    
    def _add_help_image(self, parent, image_path, caption=None, max_width=700):
        """Helper method to embed an image in the help window
        
        Args:
            parent: Parent frame to add image to
            image_path: Path to image file (PNG, JPG, etc.)
            caption: Optional caption text below image
            max_width: Maximum width for image (maintains aspect ratio)
        
        Returns:
            Label widget containing the image (or None if error)
        """
        try:
            # Create frame for image
            img_frame = ttk.Frame(parent)
            img_frame.pack(fill='x', padx=20, pady=10)
            
            # Load and resize image
            img = Image.open(image_path)
            
            # Calculate new size maintaining aspect ratio
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Create label with image
            img_label = ttk.Label(img_frame, image=photo)
            img_label.image = photo  # Keep a reference to prevent garbage collection
            img_label.pack(pady=5)
            
            # Add caption if provided
            if caption:
                caption_label = ttk.Label(img_frame, text=caption, 
                                         font=('Arial', 9, 'italic'),
                                         foreground='gray')
                caption_label.pack(pady=(0, 5))
            
            return img_label
            
        except FileNotFoundError:
            # If image file not found, show placeholder
            placeholder = ttk.Label(parent, 
                                   text=f"[Image: {image_path} - Not Found]",
                                   font=('Arial', 9, 'italic'),
                                   foreground='orange')
            placeholder.pack(padx=20, pady=5)
            return None
        except Exception as e:
            # Handle other errors gracefully
            error_label = ttk.Label(parent, 
                                   text=f"[Image Error: {str(e)}]",
                                   font=('Arial', 9, 'italic'),
                                   foreground='red')
            error_label.pack(padx=20, pady=5)
            return None
    
    def show_shortcuts(self):
        """Display keyboard shortcuts window"""
        shortcuts_window = tk.Toplevel(self)
        shortcuts_window.title("Keyboard Shortcuts")
        try:
            shortcuts_window.iconbitmap('help_images/efa_icon.ico')
        except (FileNotFoundError, tk.TclError):
            # Icon file not found or invalid - continue without icon
            pass
        shortcuts_window.geometry("500x400")
        
        # Create frame
        frame = ttk.Frame(shortcuts_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(frame, text="Keyboard Shortcuts", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Create shortcuts text
        shortcuts_text = tk.Text(frame, wrap=tk.WORD, font=('Courier', 10), 
                                height=20, width=60)
        shortcuts_text.pack(fill=tk.BOTH, expand=True)
        
        # Add shortcuts content
        shortcuts_content = """FILE OPERATIONS
Ctrl+S          Save Session
Ctrl+O          Load Session  
Ctrl+Q          Quit Application
Ctrl+R          Reset Application

CLIPBOARD OPERATIONS
Ctrl+C          Copy Active Plot to Clipboard
Ctrl+Shift+T    Copy Throw Plot
Ctrl+Shift+J    Copy Juxtaposition Plot
Ctrl+Shift+S    Copy Scenario Plot
Ctrl+Shift+L    Copy Legend

VIEW OPERATIONS
F5              Refresh All Plots
Ctrl+L          Toggle Grid Lines
Ctrl++          Increase Plot Size
Ctrl+-          Decrease Plot Size

HELP
F1              Show Help (User Guide)
Shift+F1        Show Keyboard Shortcuts
Ctrl+?          About Dialog

NAVIGATION
Ctrl+Tab        Next Tab
Ctrl+Shift+Tab  Previous Tab
Alt+1           Data Input Tab
Alt+2           Length/Depth Tab
Alt+3           Horizon Shifts Tab
Alt+4           QC Plot Tab
"""
        
        shortcuts_text.insert('1.0', shortcuts_content)
        shortcuts_text.config(state='disabled')
        
        # Close button
        ttk.Button(frame, text="Close", 
                  command=shortcuts_window.destroy).pack(pady=(10, 0))

    def create_throw_legend(self, hcolor_df):
        """
        Create a legend for the throw profile plot.
        """
        legend_items = []
        legend_items.append(Patch(facecolor='white', edgecolor='white', label='Horizons'))
        for index, row in hcolor_df.iterrows():
            horizon_label = row['Alias'] if row['Alias'] else row['Horizon']
            legend_items.append(Line2D([0], [0], color=row['Color'], lw=1, label=horizon_label))
        
        # Add mean throw if it's typically shown
        legend_items.append(Line2D([0], [0], color='black', linestyle='dotted', lw=1, label='Mean Throw'))
        
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.legend(handles=legend_items, loc='upper left')
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.axis('off')
        return fig

    def create_unit_legend(self, hcolor_df):
        """
        Create a legend for the juxtaposition unit plot using stored legend handles.
        Uses the exact legend from zone_unit_plot_method if available, otherwise creates from scratch.
        """
        # If we have stored legend handles from the actual plot, use those
        if hasattr(self, 'unitlegend_handles') and hasattr(self, 'unitlegend_labels'):
            legend_items = self.unitlegend_handles
            labels = self.unitlegend_labels
        else:
            # Fallback to creating legend from scratch
            legend_items = []
            legend_items.append(Patch(facecolor='white', edgecolor='white', label='Horizons'))
            for index, row in hcolor_df.iterrows():
                legend_items.append(Line2D([0], [0], color=row['Color'], lw=1, label=row['Alias'] + ' (FW)'))
                legend_items.append(Line2D([0], [0], color=row['Color'], linestyle='--', lw=1, label=row['Alias'] + ' (HW)'))
            
            legend_items.append(Patch(facecolor='white', edgecolor='white', label=''))
            legend_items.append(Patch(facecolor='white', edgecolor='white', label='Zone Unit Colors'))
            # Add zone unit colors
            if hasattr(self, 'zone_unit_colors'):
                for unit, color in self.zone_unit_colors.items():
                    legend_items.append(Patch(facecolor=color, edgecolor=color, label=unit))
            labels = [item.get_label() for item in legend_items]
        
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.legend(handles=legend_items, labels=labels, loc='upper left')
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.axis('off')
        return fig

    def create_lithology_legend(self, hcolor_df, zcolor_df):
        """
        Create a legend for the juxtaposition lithology plot.
        """
        legend_items = []
        legend_items.append(Patch(facecolor='white', edgecolor='white', label='Horizons'))
        for index, row in hcolor_df.iterrows():
            legend_items.append(Line2D([0], [0], color=row['Color'], lw=1, label=row['Alias'] + ' (FW)'))
            legend_items.append(Line2D([0], [0], color=row['Color'], linestyle='--', lw=1, label=row['Alias'] + ' (HW)'))
        
        legend_items.append(Patch(facecolor='white', edgecolor='white', label=''))
        legend_items.append(Patch(facecolor='white', edgecolor='white', label='Zone Lithology'))
        for index, row in zcolor_df.iterrows():
            ztype = ' (No Res.)'
            if row['Color'] == 'orange':
                ztype = ' (Poor Res.)'
            elif row['Color'] == 'yellow':
                ztype = ' (Good Res.)'
            elif row['Color'] == 'red':
                ztype = ' (SR)'
            elif row['Color'] == 'azure':
                ztype = ' (Undefined)'
            legend_items.append(Patch(facecolor=row['Color'], alpha=0.5, edgecolor=row['Color'], 
                                     label=row['Alias'] + ztype))
        
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.legend(handles=legend_items, loc='upper left')
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.axis('off')
        return fig

    def create_scenario_legend(self, hcolor_df):
        """
        Create a legend for the juxtaposition scenario plot.
        """
        legend_items = []
        legend_items.append(Patch(facecolor='white', edgecolor='white', label='Horizons'))
        for index, row in hcolor_df.iterrows():
            legend_items.append(Line2D([0], [0], color=row['Color'], lw=1, label=row['Alias'] + ' (FW)'))
            legend_items.append(Line2D([0], [0], color=row['Color'], linestyle='--', lw=1, label=row['Alias'] + ' (HW)'))
        
        legend_items.append(Patch(facecolor='white', edgecolor='white', label=''))
        legend_items.append(Patch(facecolor='white', edgecolor='white', label='Juxtaposition Scenario'))
        legend_items.append(Patch(facecolor='green', edgecolor='green', label='Good-Good'))
        legend_items.append(Patch(facecolor='yellow', edgecolor='yellow', label='Good-Poor'))
        legend_items.append(Patch(facecolor='orange', edgecolor='orange', label='Poor-Poor'))
        legend_items.append(Patch(facecolor='black', edgecolor='black', label='SR-res'))
        legend_items.append(Patch(facecolor='LightGray', edgecolor='LightGray', label='Res-noRes'))
        legend_items.append(Patch(facecolor='DarkGray', edgecolor='DarkGray', label='noRes-noRes'))
        legend_items.append(Patch(facecolor='azure', edgecolor='azure', label='Undefined-Any'))
        
        fig, ax = plt.subplots(figsize=(6, 8))
        ax.legend(handles=legend_items, loc='upper left')
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.axis('off')
        return fig

 

# add used functions with children from efa_app_functions below

def strike_to_compass(strike):
    """
    Convert strike in degrees to compass direction.
    """
    if strike >= 0 and strike < 11.25:
        return ['N','S']
    elif strike >= 11.25 and strike < 33.75:
        return ['NNE','SSW']
    elif strike >= 33.75 and strike < 56.25:
        return ['NE','SW']
    elif strike >= 56.25 and strike < 78.75:
        return ['ENE','WSW']
    elif strike >= 78.75 and strike < 101.25:
        return ['E','W']
    elif strike >= 101.25 and strike < 123.75:
        return ['ESE','WNW']
    elif strike >= 123.75 and strike < 146.25:
        return ['SE','NW']
    elif strike >= 146.25 and strike < 168.75:
        return ['SSE','NNW']
    elif strike >= 168.75 and strike < 191.25:
        return ['S','N']
    elif strike >= 191.25 and strike < 213.75:
        return ['SSW','NNE']
    elif strike >= 213.75 and strike < 236.25:
        return ['SW','NE']
    elif strike >= 236.25 and strike < 258.75:
        return ['WSW','ENE']
    elif strike >= 258.75 and strike < 281.25:
        return ['W','E']
    elif strike >= 281.25 and strike < 303.75:
        return ['WNW','ESE']
    elif strike >= 303.75 and strike < 326.25:
        return ['NW','SE']
    elif strike >= 326.25 and strike < 348.75:
        return ['NNW','SSE']
    elif strike >= 348.75 and strike <= 360:
        return ['N','S']
    else:
        return ['?','?']




def styledf_red_green(val):
    """
    Sets up color style for foot-wall and hanging-wall dataframes. 
    Highlights depth values 'out of order' red (lightsalmon) and NaN values orange.
    This function works on a row (axis=1), checking if depth values
    are in correct stratigraphic order across horizons.
    
    For geological horizons with negative depth values:
    - Depths should get more negative (deeper) from left to right
    - If current depth < previous depth (more negative = deeper) → CORRECT → green
    - If current depth >= previous depth (less negative = shallower) → OUT OF ORDER → red
    - If current depth is NaN → MISSING DATA → orange
    """
    import pandas as pd
    import numpy as np
    
    bg_color_list = []
    for i in range(len(val)):
        if i == 0:
            bg_color_list.append('whitesmoke')
        elif i == 1:
            # Check if first data value is NaN
            if pd.isna(val.iloc[i]) or np.isnan(val.iloc[i]) if isinstance(val.iloc[i], (int, float)) else False:
                bg_color_list.append('orange')  # NaN values
            else:
                bg_color_list.append('green')  # First data column - default green
        else:
            # Check if current value is NaN
            current_val = val.iloc[i]
            previous_val = val.iloc[i-1]
            
            if pd.isna(current_val) or (isinstance(current_val, (int, float)) and np.isnan(current_val)):
                bg_color_list.append('orange')  # NaN values
            elif pd.isna(previous_val) or (isinstance(previous_val, (int, float)) and np.isnan(previous_val)):
                # If previous value is NaN, we can't compare, so just mark as green if current is valid
                bg_color_list.append('green')
            else:
                # For geological horizons, depths should get more negative (deeper)
                # If current value < previous value, it's correct order (deeper than previous)
                # If current value >= previous value, it's out of order (shallower than previous)
                if current_val < previous_val:
                    bg_color_list.append('green')   # CORRECT ORDER - deeper
                else:
                    bg_color_list.append('red')  # OUT OF ORDER - shallower
    return bg_color_list


def create_styled_text_widget(parent_frame, df, title):
    """
    Create a styled text widget that displays a dataframe with color coding
    for out-of-order depth values on a row basis.
    """
    # Create frame for this dataframe
    frame = ttk.LabelFrame(parent_frame, text=title)
    frame.pack(fill='both', expand=True, padx=5, pady=5)
    
    # Create text widget with scrollbars
    text_frame = ttk.Frame(frame)
    text_frame.pack(fill='both', expand=True, padx=5, pady=5)
    
    text_widget = tk.Text(text_frame, height=10, wrap=tk.NONE, font=('Courier', 9))
    scrollbar_y = ttk.Scrollbar(text_frame, orient='vertical', command=text_widget.yview)
    scrollbar_x = ttk.Scrollbar(text_frame, orient='horizontal', command=text_widget.xview)
    text_widget.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
    
    # Configure tags for different background colors
    text_widget.tag_configure('whitesmoke', background='whitesmoke')
    text_widget.tag_configure('green', background='white', foreground='green')  # New color for correct order
    text_widget.tag_configure('red', background='white', foreground='red')    # New color for out of order
    text_widget.tag_configure('orange', background='white', foreground='orange')  # New color for NaN values
    text_widget.tag_configure('header', background='lightgray', font=('Courier', 9, 'bold'))
    text_widget.tag_configure('normal', background='white')
    
    # Get the string representation and split into lines
    df_string = df.to_string()
    lines = df_string.split('\n')
    
    # Insert header with styling
    header_line = lines[0] + '\n'
    text_widget.insert('end', header_line, 'header')
    
    # Process each data row
    for i, line in enumerate(lines[1:]):
        if line.strip():  # Skip empty lines
            row_idx = i
            if row_idx < len(df):
                # Get the row data and apply styling function
                row_data = df.iloc[row_idx]
                colors = styledf_red_green(row_data)
                
                # Split the line into parts
                parts = line.split()
                if len(parts) > 1:
                    # Insert row index/label (first part) - always normal
                    text_widget.insert('end', parts[0], 'normal')
                    
                    # Insert each data value with appropriate coloring
                    for j, value_str in enumerate(parts[1:]):
                        if j < len(colors):
                            color_tag = colors[j]
                        else:
                            color_tag = 'normal'
                        
                        # Add appropriate spacing
                        text_widget.insert('end', '  ', 'normal')
                        text_widget.insert('end', value_str, color_tag)
                    
                    text_widget.insert('end', '\n', 'normal')
                else:
                    text_widget.insert('end', line + '\n', 'normal')
            else:
                text_widget.insert('end', line + '\n', 'normal')
    
    text_widget.config(state='disabled')
    
    text_widget.grid(row=0, column=0, sticky='nsew')
    scrollbar_y.grid(row=0, column=1, sticky='ns')
    scrollbar_x.grid(row=1, column=0, sticky='ew')
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)
    
    return text_widget

def Rz(theta):
    """
    Create rotation matrix about the z-axis
    """
    return np.matrix([[ np.cos(theta), -np.sin(theta), 0 ],
                   [ np.sin(theta), np.cos(theta) , 0 ],
                   [ 0           , 0            , 1 ]])


def rotate_array(inn_array, R):
    """
    Rotate array of xyz-coordinates using rotation matrix R
    """
    outlist = []
    for row in inn_array:
        point_transpose = np.transpose([np.array(row)])
        rotated = R * point_transpose
        tlist = [rotated[0].item(),rotated[1].item(),rotated[2].item()]
        outlist.append(tlist)
    xyz_rot = np.array(outlist)
    return(xyz_rot)


def strikedip(Vn):
    """
    Function to calculate the strike and dip of a plane from an input vector that is normal to the plane
    E.g. strike,dip = strikedip(Vn), where Vn is a numpy vector
    """
    if Vn[2] < 0: # Test that vector is pointing up - else flip
        #print('flipped')
        Vn = -Vn
    Vn_hat = Vn / np.linalg.norm(Vn) #Unit normal vector
    transXY = np.array([[1,0,0],[0,1,0],[0,0,0]]) #Transformation matrix to map vector to XY-plane
    Vn_hatXY = np.dot(Vn_hat,transXY) #Map normal vector to XY-plane
    #print(Vn_hatXY)
    Vnorth = np.array([0,1,0]) #Define north vector
    azimuth = np.rad2deg(np.arccos(np.dot(Vn_hatXY,Vnorth)/(np.linalg.norm(Vn_hatXY)*np.linalg.norm(Vnorth)))) #angle betwen north vector and normal vector in xy plane
    dip = 90 - np.rad2deg(np.arccos(np.dot(Vn_hatXY,Vn_hat)/(np.linalg.norm(Vn_hatXY)*np.linalg.norm(Vn_hat)))) # Dip of normal vector
    if Vn_hatXY[0] > 0 and Vn_hatXY[1] > 0:
        strike = 270 + azimuth
    elif Vn_hatXY[0] < 0:
        strike = 270 - azimuth
    elif Vn_hatXY[0] > 0 and Vn_hatXY[1] < 0:
        strike = azimuth - 90
    elif Vn_hatXY[0] > 0 and Vn_hatXY[1] == 0:
        strike = azimuth - 90
    elif Vn_hatXY[0] == 0 and Vn_hatXY[1] > 0:
        strike = 270 + azimuth
    elif Vn_hatXY[0] == 0 and Vn_hatXY[1] < 0:
        strike = 270 - azimuth
    else:
        strike = 666 # This seems to occur when the when the normal vector to the triangle has zero length, and happens if two of the three coordinates in the triangle are equal. Should be discarded from dataset.
        #print('check')
        #print(Vn)
    return(strike, dip)


def planefit(points):
    """
    Calculates the best fitting plane to a set of points using singular value decomposition from np.linalg.
    """
    points = points.T
    svd = np.linalg.svd(points - np.mean(points, axis=1, keepdims=True))
    # Extract the left singular vectors
    left = svd[0]
    return(left[:,-1])



def xyz2ld(datadict, z = 'Depth 1', data_format = 'Petrel_FC'):
    """
    Convert xyz coordinates to length (along strike) - depth coordinates.

    Takes a dictionary of dataframes with x,y,z coordinates and returns a dictionary with length-depth coordinates, in addition to the strike and dip of best fitting fault plane
    """
    i = 0
    for key, value in datadict.items():
        df = value
        if i == 0:
            xyz_all = df[['X','Y',z]].to_numpy()#might need to use indexes in case the 'depth 1' tag changes, perhaps first convert to numpy array, then select index 0,1,5
        if i > 0:
            xyz_all = np.concatenate((xyz_all,df[['X','Y', z]].to_numpy()))
        i = i + 1
    xyz_pole = planefit(xyz_all)
    strike,dip = strikedip(xyz_pole)
    R = Rz(np.radians(strike))
    xyz_all_R = rotate_array(xyz_all,R)
    min = xyz_all_R[:,1].min()
    #
    ld_dict = {}
    for key, value in datadict.items():
        name = key
        df = value
        if data_format == 'Petrel_FC':
            fv = df.groupby('FaultContactType').get_group(1)
            hv = df.groupby('FaultContactType').get_group(2)
        elif data_format == 'Cegal_FC':
            fv = df.groupby('Contact type').get_group(1)
            hv = df.groupby('Contact type').get_group(2)
        fva = fv[['X', 'Y', z]].to_numpy()
        fvaR = rotate_array(fva,R)
        fva_len = fvaR[:,1]-min
        hva = hv[['X', 'Y', z]].to_numpy()
        hvaR = rotate_array(hva,R)
        hva_len = hvaR[:,1]-min
        fsort = fva_len.argsort()
        hsort = hva_len.argsort()
        ld_dict[name] = {'fv' : {'l': fva_len[fsort], 'd': fvaR[:,2][fsort]},'hv': {'l':hva_len[hsort], 'd':hvaR[:,2][hsort]}}#if to return xyz use same sorting on xyz and return
    return(ld_dict,strike,dip)


def ld_res2df(ld_dict,step=10):# this funciton is not in use and can be deleted if new function works 
    """
    Resamples the dength-depth juxtapositoin file to equal interval points and returns two dataframes, one for the footwall and one for the hangingwall
    Returns footwall and hangigall df
    """
    minlen = []
    maxlen = []
    for i in range(len(list(ld_dict.keys()))):
        #print(list(ld.keys())[i])
        minlen.append(min(ld_dict[list(ld_dict.keys())[i]]['fv']['l']))
        minlen.append(min(ld_dict[list(ld_dict.keys())[i]]['hv']['l']))
        maxlen.append(max(ld_dict[list(ld_dict.keys())[i]]['fv']['l']))
        maxlen.append(max(ld_dict[list(ld_dict.keys())[i]]['hv']['l']))
    minl = max(minlen)
    maxl = min(maxlen)
    x_re = np.arange(np.ceil(minl),int(maxl),step)
    #df = df = pd.DataFrame(x_re,columns=['length'])
    fv_df = pd.DataFrame(x_re,columns=['length'])
    hv_df = pd.DataFrame(x_re,columns=['length'])
    ld_res_dict = {}
    for i in range(len(list(ld_dict.keys()))):
        #x_re = np.arange(np.ceil(minl),int(maxl))
        ifoot = interpolate.interp1d(ld_dict[list(ld_dict.keys())[i]]['fv']['l'],ld_dict[list(ld_dict.keys())[i]]['fv']['d'])
        ihang = interpolate.interp1d(ld_dict[list(ld_dict.keys())[i]]['hv']['l'],ld_dict[list(ld_dict.keys())[i]]['hv']['d'])
        yf_re = ifoot(x_re)
        yh_re = ihang(x_re)
        #df[str(ld_dict[list(ld_dict.keys())[i]+'_fvd'])] = yf_re
        name = list(ld_dict.keys())[i]
        #df['h1_fvd'+'ba'] = yf_re
        fv_df[name] = yf_re
        hv_df[name] = yh_re
        ld_res_dict[list(ld_dict.keys())[i]] = {'fv': {'l': x_re, 'd': yf_re}, 'hv': {'l': x_re, 'd': yh_re}}
    return(fv_df,hv_df)


def ld_org2df(ld_dict, step=10):
    """
    Resamples the length-depth juxtaposition file to equal interval points and returns two dataframes,
    one for the footwall and one for the hangingwall. Preserves the entire range of data and fills
    with NaN where no data exist.
    """
    minlen = []
    maxlen = []
    for key in ld_dict:
        minlen.append(min(ld_dict[key]['fv']['l']))
        minlen.append(min(ld_dict[key]['hv']['l']))
        maxlen.append(max(ld_dict[key]['fv']['l']))
        maxlen.append(max(ld_dict[key]['hv']['l']))
    minl = min(minlen)
    #print('min:', minl)
    maxl = max(maxlen)
    #print('max:', maxl)
    x_re = np.arange(np.floor(minl), np.ceil(maxl) + step, step)
    #print('x_re:', x_re)
    fv_df = pd.DataFrame(x_re,columns=['length'])
    hv_df = pd.DataFrame(x_re,columns=['length'])
    ld_res_dict = {}
    for i in range(len(list(ld_dict.keys()))):
        #x_re = np.arange(np.ceil(minl),int(maxl))
        ifoot = interpolate.interp1d(ld_dict[list(ld_dict.keys())[i]]['fv']['l'],ld_dict[list(ld_dict.keys())[i]]['fv']['d'],bounds_error=False, fill_value=np.nan)
        ihang = interpolate.interp1d(ld_dict[list(ld_dict.keys())[i]]['hv']['l'],ld_dict[list(ld_dict.keys())[i]]['hv']['d'],bounds_error=False, fill_value=np.nan)
        yf_re = ifoot(x_re)
        yh_re = ihang(x_re)
        #df[str(ld_dict[list(ld_dict.keys())[i]+'_fvd'])] = yf_re
        name = list(ld_dict.keys())[i]
        #df['h1_fvd'+'ba'] = yf_re
        fv_df[name] = yf_re
        hv_df[name] = yh_re
        ld_res_dict[list(ld_dict.keys())[i]] = {'fv': {'l': x_re, 'd': yf_re}, 'hv': {'l': x_re, 'd': yh_re}}
    #print('min:', minlen)
    #print('max:', maxlen)
    return fv_df, hv_df

def overlap_trunk(fv_df,hv_df):
    """
    looks at input footwall and hangingwall dataframes: if deeper horizon is shallower then shallower horizon - if so, set deeper horizon equal to shallower horizon
    """
    for index, row in fv_df.iterrows():
        for i in range(1,len(row)):
            #if row.iloc[i] > row.iloc[i-1]:
            if fv_df.iloc[index,i] > fv_df.iloc[index,i-1]:
                fv_df.iloc[index,i] = fv_df.iloc[index,i-1]
    for index, row in hv_df.iterrows():
        for i in range(1,len(row)):
            if hv_df.iloc[index,i] > hv_df.iloc[index,i-1]:
                hv_df.iloc[index,i] = hv_df.iloc[index,i-1]
    return(fv_df,hv_df)


def horizon_shift_input(hdict):
    """
    Set default horizon shift value to zero dict --> return pandas dataframe
    """
    hlist = list(hdict.keys())
    feature_list = ["sh1", "sh2", "sh3", "sh4", "sh6", "sh7", "sh8", "sh9", "sh10", "sh11", "sh12", "sh13", "sh14", "sh15"]
    df = pd.DataFrame(index=hlist, columns=feature_list) 
    return(df)


def horizon_shift_execute_v2(fv_df, hv_df, shift_df):
    #print(fv_df)
    #print(hv_df)
    nfv_df = pd.DataFrame()
    nfv_df['length'] = fv_df['length']
    nhv_df = pd.DataFrame()
    nhv_df['length'] = hv_df['length']
    nh_list = []
    #print('dataframetapir')
    #print(shift_df)
    for index, row in shift_df.iterrows():
        #print('index:', index)
        for val in row:
            #print('tapå')
            #print('val:', val)
            # Check if val is a number and not NaN
            if isinstance(val, (int, float, np.integer, np.floating)) and not pd.isna(val):
                shift = float(val)
                #print('shift:', shift)
                if shift > 0:
                    #print('up')
                    shiftstring = "_up_"
                    #print('shiftstring:', shiftstring)
                    #print(fv_df)
                    #print(index)
                    #print(fv_df[index])
                    #print(fv_df[index] + shift)
                    nfv_df[index+shiftstring+str(shift)] = fv_df[index] + shift
                    nhv_df[index+shiftstring+str(shift)] = hv_df[index] + shift
                    nh_list.append(str(index)+shiftstring+str(shift))
                    #print('new horizon:', str(index)+shiftstring+str(shift))
                elif shift < 0:
                    #print('down')
                    shiftstring = "_down_"
                    nfv_df[index+shiftstring+str(shift)] = fv_df[index] + shift
                    nhv_df[index+shiftstring+str(shift)] = hv_df[index] + shift
                    nh_list.append(str(index)+shiftstring+str(shift))
                    #print('new horizon:', str(index)+shiftstring+str(shift))
                elif shift == 0:
                    #print('no shift')
                    shiftstring = ""
                    nfv_df[index+shiftstring] = fv_df[index]
                    nhv_df[index+shiftstring] = hv_df[index]
                    nh_list.append(str(index)+shiftstring)
                    #print('new horizon:', str(index)+shiftstring)
            else:
                #print('no shifting')
                pass
    #print(nfv_df)
    #print(nhv_df)
    return(nfv_df, nhv_df, nh_list)






def juxtaposition_color(zfv_color,zhv_color):
    """
    Function to map colors and juxtapositino scenario based on input footwall and hangingwall zone color
    """
    new_color = 'gray'
    fv_type = 'undefined'
    hv_type = 'undefined'
    if zfv_color == 'black' and zhv_color == 'black':# Mapping colors should perhaps be done outside in a defined color mapping function
        new_color = 'DarkGray'
        fv_type = 'No Res'
        hv_type = 'No Res'
    elif zfv_color == 'yellow' and zhv_color == 'yellow':
        new_color = 'green'
        fv_type = 'Good Res'
        hv_type = 'Good Res'
    elif zfv_color == 'orange' and zhv_color == 'orange':
        #new_color = 'red'# changed from red to orange as requested
        new_color = 'orange'
        fv_type = 'Poor Res'
        hv_type = 'Poor Res'
    elif zfv_color == 'yellow' and zhv_color == 'orange':
        new_color = 'yellow'
        fv_type = 'Good Res'
        hv_type = 'Poor Res'
    elif zfv_color == 'orange' and zhv_color == 'yellow':
        new_color = 'yellow'
        fv_type = 'Poor Res'
        hv_type = 'Good Res'
    elif zfv_color == 'yellow' and zhv_color == 'black':
        new_color = 'LightGray'
        fv_type = 'Good Res'
        hv_type = 'No Res'
    elif zfv_color == 'orange' and zhv_color == 'black':
        new_color = 'LightGray'
        fv_type = 'Poor Res'
        hv_type = 'No Res'
    elif zfv_color == 'black' and zhv_color == 'yellow':
        new_color = 'LightGray'
        fv_type = 'No Res'
        hv_type = 'Good Res'
    elif zfv_color == 'black' and zhv_color == 'orange':
        new_color = 'LightGray'
        fv_type = 'No Res'
        hv_type = 'Poor Res'
    elif zfv_color == 'black' and zhv_color == 'red':#add sr juxt
        new_color = 'DarkGray'
        fv_type = 'No Res'
        hv_type = 'SR'
    elif zfv_color == 'red' and zhv_color == 'black':#add sr juxt
        new_color = 'DarkGray'
        fv_type = 'SR'
        hv_type = 'No Res'
    elif zfv_color == 'yellow' and zhv_color == 'red':#add sr juxt
        new_color = 'black'
        fv_type = 'Good Res'
        hv_type = 'SR'
    elif zfv_color == 'red' and zhv_color == 'yellow':#add sr juxt
        new_color = 'black'
        fv_type = 'SR'
        hv_type = 'Good Res'
    elif zfv_color == 'orange' and zhv_color == 'red':#add sr juxt
        new_color = 'black'
        fv_type = 'Poor Res'
        hv_type = 'SR'
    elif zfv_color == 'red' and zhv_color == 'orange':#add sr juxt
        new_color = 'black'
        fv_type = 'SR'
        hv_type = 'Poor Res'
    elif zfv_color == 'red' and zhv_color == 'red':#add sr juxt
        new_color = 'DarkGray'
        fv_type = 'SR'
        hv_type = 'SR'
    #
    elif zfv_color == 'azure' and zhv_color == 'azure':
        new_color = 'azure'
        fv_type = 'Undefined'
        hv_type = 'Undefined'
    elif zfv_color == 'azure' and zhv_color == 'yellow':
        new_color = 'azure'
        fv_type = 'Undefined'
        hv_type = 'Good Res'
    elif zfv_color == 'azure' and zhv_color == 'orange':
        new_color = 'azure'
        fv_type = 'Undefined'
        hv_type = 'Poor Res'
    elif zfv_color == 'azure' and zhv_color == 'red':
        new_color = 'azure'
        fv_type = 'Undefined'
        hv_type = 'SR'
    elif zfv_color == 'azure' and zhv_color == 'black':
        new_color = 'azure'
        fv_type = 'Undefined'
        hv_type = 'No Res'
    #
    elif zfv_color == 'yellow' and zhv_color == 'azure':
        new_color = 'azure'
        fv_type = 'Good Res'
        hv_type = 'Undefined'
    elif zfv_color == 'orange' and zhv_color == 'azure':
        new_color = 'azure'
        fv_type = 'Poor Res'
        hv_type = 'Undefined'
    elif zfv_color == 'red' and zhv_color == 'azure':
        new_color = 'azure'
        fv_type = 'SR'
        hv_type = 'Undefined'
    elif zfv_color == 'black' and zhv_color == 'azure':
        new_color = 'azure'
        fv_type = 'No Res'
        hv_type = 'Undefined'
    return(new_color,fv_type,hv_type)


def interpolate_throw(fv_df, juxt_df, throwarray, h_color=None):
    """
    Interpolate throw values at juxtaposition apex points.
    
    Args:
        fv_df: Footwall dataframe with 'length' column
        juxt_df: Juxtaposition dataframe with 'Length' column
        throwarray: 2D numpy array where each row is throw for one horizon
        h_color: Horizon color dataframe with 'Horizon' and 'Alias' columns (optional)
    
    Returns:
        juxt_df with added throw columns for each horizon plus mean throw
    """
    lenlist = juxt_df['Length'].tolist()
    
    # Add individual horizon throw columns
    for i in range(throwarray.shape[0]):
        # Interpolate throw for this horizon
        int_throw = interpolate.interp1d(fv_df['length'], throwarray[i, :], 
                                         bounds_error=False, fill_value=np.nan)
        horizon_throw = int_throw(lenlist)
        
        # Create column name using alias if available, otherwise use index
        if h_color is not None and i < len(h_color):
            horizon_name = h_color.loc[i, 'Alias'] if h_color.loc[i, 'Alias'] else h_color.loc[i, 'Horizon']
            col_name = f'Throw_{horizon_name}'
        else:
            col_name = f'Throw_H{i+1}'
        
        juxt_df[col_name] = horizon_throw.round(2)
    
    # Add mean throw column at the end
    # Suppress RuntimeWarning about mean of empty slice (happens when all values are NaN)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        mean_throw_array = np.nanmean(throwarray, axis=0)
    int_throw_mean = interpolate.interp1d(fv_df['length'], mean_throw_array,
                                         bounds_error=False, fill_value=np.nan)
    lenthrow_mean = int_throw_mean(lenlist)
    juxt_df['Mean_Throw'] = lenthrow_mean.round(2)
    
    return juxt_df


def main():
    app = EFA_juxtaposition()
    app.mainloop()


if __name__ == "__main__":
    main()