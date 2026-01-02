#!/usr/bin/env python3
"""
EFA Juxtaposition Analysis - Geological Analysis Tool

Copyright (C) 2025 John-Are Hansen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Contact: jareh@equinor.com
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
import pickle
from PIL import Image
import io

# Optional Windows clipboard support
try:
    import win32clipboard
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False



class EFA_juxtaposition(tk.Tk):
    VERSION = "0.9.6"
    BUILD_DATE = "2025-10-28"
    AUTHOR = "John-Are Hansen (jareh@equinor.com)"

    def __init__(self):
        super().__init__()
        self.title(f"EFA Juxtaposition Analysis v{self.VERSION}")
        self.geometry("1400x900")
        self.state('zoomed')  # Maximize window on Windows
        
        # Initialize variables from both apps
        self.datadict = {}
        self.innfiles = []
        self.z_select = StringVar(value='Z')
        self.num_horizons = IntVar(value=1)
        self.plot_name = StringVar(value="Analysis Plot")
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
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create frames for each tab - combining the best of both apps
        self.data_input_frame = ttk.Frame(self.notebook)
        self.data_manipulation_frame = ttk.Frame(self.notebook)
        self.plot_settings_frame = ttk.Frame(self.notebook)
        self.throw_profile_frame = ttk.Frame(self.notebook)
        self.juxtaposition_plot_frame = ttk.Frame(self.notebook)
        self.scenario_plot_frame = ttk.Frame(self.notebook)
        self.output_tables_frame = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.data_input_frame, text='Data Input')
        self.notebook.add(self.data_manipulation_frame, text='Data Manipulation')
        self.notebook.add(self.plot_settings_frame, text='Plot Settings')
        self.notebook.add(self.throw_profile_frame, text='Throw Profile')
        self.notebook.add(self.juxtaposition_plot_frame, text='Juxtaposition Plot')
        self.notebook.add(self.scenario_plot_frame, text='Juxt. Scenario Plot')
        self.notebook.add(self.output_tables_frame, text='Output Tables')
        
        # Setup each tab
        self.setup_data_input_tab()
        self.setup_data_manipulation_tab()
        self.setup_plot_settings_tab()
        self.setup_throw_profile_tab()
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
        ttk.Label(self.qc_plot_frame, text="Quality Control Plot", 
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
                create_styled_text_widget(container, self.fv_df, "Footwall Data (fv_df)")
            
            # Display hangingwall data with styling
            if self.hv_df is not None:
                create_styled_text_widget(container, self.hv_df, "Hangingwall Data (hv_df)")
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
                create_styled_text_widget(container, self.nfv_df, "Shifted Footwall Data (nfv_df)")
            
            # Display shifted hangingwall data with styling
            if self.nhv_df is not None:
                create_styled_text_widget(container, self.nhv_df, "Shifted Hangingwall Data (nhv_df)")
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
        horizon_frame = ttk.LabelFrame(self.color_scrollable_frame, text="Horizon Colors & Aliases")
        horizon_frame.pack(fill='x', padx=5, pady=5)
        
        self.horizon_alias_vars = {}
        self.horizon_color_vars = {}
        
        for i, horizon in enumerate(self.nh_list):
            row_frame = ttk.Frame(horizon_frame)
            row_frame.pack(fill='x', padx=5, pady=2)
            
            # Horizon name
            ttk.Label(row_frame, text=horizon[:15], width=15).pack(side='left', padx=2)
            
            # Alias entry
            alias_var = StringVar(value=self.horizon_aliases.get(horizon, horizon))
            self.horizon_alias_vars[horizon] = alias_var
            alias_entry = ttk.Entry(row_frame, textvariable=alias_var, width=15)
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
            zone_frame = ttk.LabelFrame(self.color_scrollable_frame, text="Zone Lithology & Aliases")
            zone_frame.pack(fill='x', padx=5, pady=5)
            
            self.zone_alias_vars = {}
            self.zone_lithology_vars = {}
            
            lithology_options = list(self.zone_lithology.keys())
            
            for zone in self.zone_names_aliases.keys():
                row_frame = ttk.Frame(zone_frame)
                row_frame.pack(fill='x', padx=5, pady=2)
                
                # Zone name
                ttk.Label(row_frame, text=zone[:15], width=15).pack(side='left', padx=2)
                
                # Alias entry
                alias_var = StringVar(value=self.zone_names_aliases.get(zone, zone))
                self.zone_alias_vars[zone] = alias_var
                alias_entry = ttk.Entry(row_frame, textvariable=alias_var, width=15)
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
                
                # Color indicator button - button to show color of selected lithlogy
                #color = self.zone_colors.get(zone, '#CCCCCC')
                #color_label = tk.Label(row_frame, width=3, bg=color, relief='solid', borderwidth=1)
                #color_label.pack(side='left', padx=2)
        
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
            self.zone_names_aliases[zone] = self.zone_alias_vars[zone].get()
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
            
            # Create zone color dataframe
            self.ezcolor_df = pd.DataFrame({
                'Zone': zone_list,
                'Alias': [self.zone_names_aliases.get(z, z) for z in zone_list],
                'Color': [self.zone_colors.get(z, '#E76F51') for z in zone_list]
            })
            #print('ezcolor_df', self.ezcolor_df)
    
    def setup_all_plots(self):
        """Setup all plot tabs"""
        self.setup_throw_profile_plot()
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
        self.legend_sidebar_throw = ttk.Frame(main_frame, width=300)
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

        ttk.Checkbutton(controls_frame, text="Display gridlines", 
                       variable=self.gridvarf0, command=self.update_throw_plot).pack(side='left', padx=5)
        ttk.Checkbutton(controls_frame, text="Display mean throw", 
                       variable=self.meanthrow_var, 
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
    

        
    def setup_juxtaposition_plot_tab(self):
        """Setup juxtaposition plot tab with legend sidebar"""
        main_frame = ttk.Frame(self.juxtaposition_plot_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Create legend sidebar
        self.legend_sidebar_juxt = ttk.Frame(main_frame, width=300)
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
        self.legend_sidebar_scenario = ttk.Frame(main_frame, width=300)
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
        def populate_legend_sidebar(sidebar, ecolor_df, ezcolor_df):
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
            
            if ecolor_df is not None and ezcolor_df is not None:
                try:
                    # Create legend using hlegend function
                    legend_fig = hlegend(ecolor_df, ezcolor_df)
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
                    # If hlegend fails, create a simple text-based legend
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
                    
                    # Add zone lithology legend
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

        # Populate legends for all plot tabs
        if hasattr(self, 'legend_sidebar_throw') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_throw, self.ecolor_df, self.ezcolor_df)
            
        if hasattr(self, 'legend_sidebar_juxt') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_juxt, self.ecolor_df, self.ezcolor_df)
            
        if hasattr(self, 'legend_sidebar_scenario') and self.ecolor_df is not None:
            populate_legend_sidebar(self.legend_sidebar_scenario, self.ecolor_df, self.ezcolor_df)

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
        
        ttk.Button(self.output_tables_frame, text="Export Tables to CSV", 
                  command=self.export_tables).pack(pady=10)
    
    def setup_output_tables_data(self):
        """Setup output tables data"""
        if hasattr(self, 'throwrange_df') and hasattr(self, 'juxtlist') and hasattr(self, 'throwarray'):
            self.juxt_df = interpolate_throw(self.fv_df, self.juxtlist, self.throwarray)
            
            self.create_table_display(self.throw_stats_frame, self.throwrange_df, "Horizon Throw Statistics")
            self.create_table_display(self.juxt_scenarios_frame, self.juxt_df, "Juxtaposition Scenarios")
            self.create_table_display(self.footwall_frame, self.nfv_df, "Foot-wall Data")
            self.create_table_display(self.hangingwall_frame, self.nhv_df, "Hanging-wall Data")
    
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
            self.plot_name.set("Analysis Plot")
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
            self.zone_lithology_vars = {}  # Reset zone lithology variables
            
            # Reset legend sidebar references
            self.legend_sidebar_throw = None
            self.legend_sidebar_juxt = None
            self.legend_sidebar_scenario = None
            
            # Reset figure references
            self.current_throw_fig = None
            self.current_juxt_fig = None
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
                    horizon_color = self.horizon_colors.get(horizon_name, colorlist[i % len(colorlist)])
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

    def throw_plot_method(self, fv_df=None, hv_df=None, h_color=None, title='', figsize=(6,12), gridlines=1, linewidth=1, meanthrow=1, z_select='Z'):
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
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Throw - ' + title
        fig = plt.figure(figsize=figsize)
        throwrange = []
        throwlist = []
        for i in range(1,fv_df.shape[1]):
            throw = fv_df.iloc[:,i]-hv_df.iloc[:,i]
            throwlist.append(throw)
            plt.plot(fv_df['length'],throw,color=h_color.loc[i-1,'Color'], linewidth = linewidth)
            tmin = round(np.nanmin(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            tmean = round(np.nanmean(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            tmax = round(np.nanmax(fv_df.iloc[:,i]-hv_df.iloc[:,i]),1)
            throwrange.append([h_color.loc[i-1,'Horizon'], h_color.loc[i-1,'Alias'],tmin,tmean,tmax])
        throwarray = np.array(throwlist)
        if meanthrow == 1:
            #plt.plot(fv_df['length'], throwarray.mean(0),color = 'black', linestyle = '--')
            plt.plot(fv_df['length'], np.nanmean(throwarray, axis=0),color = 'black', linestyle = 'dotted')
            #print(throwarray)
            #print(np.nanmean(throwarray, axis=0))
            
        plt.xlabel(f"Distance along mean strike {self.unit_xy}")
        plt.ylabel(f"Throw ({self.z_select_to_unit()})")
        # Place text in the upper left corner of the plot
        #ax = plt.gca()
        #xlim = ax.get_xlim()
        #ylim = ax.get_ylim()
        #plt.text(xlim[0], ylim[1]+25, 'ul', size=15, va='top', ha='left')
        # Place text in the upper right corner of the plot
        #plt.text(xlim[1], ylim[1]+25, 'ur', size=15, va='top', ha='right')
        plt.title(title)
        ur, ul = strike_to_compass(self.strike)
        plt.title(ul, loc='left')
        plt.title(ur, loc='right')
        if gridlines == 1:
            plt.grid(alpha = 0.5)
        throwrange_df = pd.DataFrame(throwrange,columns=['Horizon', 'Alias', 'min_Throw', 'mean_throw','max_throw'])
        return(fig,throwrange_df, throwarray)



    def zone_color_plot_method(self, fv_df=None, hv_df=None, ld_dict=None, h_color=None, z_color=None, title='', figsize=(6,12), fv=1, hv=1, fill=1, gridlines=1, linewidth=1, z_select='Z', disp_orgpoints=1):
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
        if disp_orgpoints == 1:
            disp_orgpoints = self.orgpoints.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Zone Lith. - ' + title
        fig = plt.figure(figsize = figsize)
        if fill == 1:
            if hv_df.shape[1] > 2:
                for i in range(2,hv_df.shape[1]):
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
                                 color=z_color.loc[i-2,'Color'], alpha=0.5)

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
                                 color=z_color.loc[i-2,'Color'], alpha=0.5)
        if fv == 1:
            for i in range(1,fv_df.shape[1]):
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], linewidth = linewidth)
        if hv == 1:
            for i in range(1,fv_df.shape[1]):
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', linewidth = linewidth)
        if fv == 0:
            for i in range(1,fv_df.shape[1]):
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], alpha = 0.1, linewidth = linewidth)
        if hv == 0:
            for i in range(1,fv_df.shape[1]):
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', alpha = 0.1, linewidth = linewidth)
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



        #if pointid == 1:
            #for ti,ftxt in enumerate(zfv):
                #plt.text(ld_dict[list(ld_dict.keys())[i]]['fv']['l'][ti],ld_dict[list(ld_dict.keys())[i]]['fv']['d'][ti], ftxt)
            #for hi,htxt in enumerate(zhv):
                #plt.text(ld_dict[list(ld_dict.keys())[i]]['hv']['l'][hi],ld_dict[list(ld_dict.keys())[i]]['hv']['d'][hi], htxt)
        
        plt.xlabel(f"Distance along mean strike {self.unit_xy}")
        plt.ylabel(f"Elevation ({self.z_select_to_unit()})")
        plt.title(title)
        ur, ul = strike_to_compass(self.strike)
        plt.title(ul, loc='left')
        plt.title(ur, loc='right')
        if gridlines == 1:
            plt.grid(alpha=0.5)
        return(fig)

    def zone_juxtscenario_plot_method(self, fv_df=None, hv_df=None, ld_dict=None, h_color=None, z_color=None, title='', figsize=(6,12), gridlines=1, linewidth=1, fv=1, hv=1, apex=1, apexid=1, z_select='Z', disp_orgpoints=1):
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
        if disp_orgpoints == 1:
            disp_orgpoints = self.orgpoints2.get()
        if z_select == 'Z':
            z_select = self.z_select.get()
            
        title = 'Juxtaposition Scenario - ' + title
        warning = ''
        fig = plt.figure(figsize=figsize)
        fv_poly_x = np.append(fv_df['length'].to_numpy(),fv_df['length'].to_numpy()[::-1])
        hv_poly_x = np.append(hv_df['length'].to_numpy(),hv_df['length'].to_numpy()[::-1])
        
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
                plt.plot(fv_df['length'],fv_df.iloc[:,i],color=h_color.loc[i-1,'Color'], linewidth = linewidth)
        if hv == 1:
            for i in range(1,fv_df.shape[1]):
                plt.plot(hv_df['length'],hv_df.iloc[:,i],color=h_color.loc[i-1,'Color'] ,linestyle='--', linewidth = linewidth)
        juxt_df = pd.DataFrame(juxt_list,columns=['FV_Zone','HV_Zone','FV_Alias','HV_Alias','Length','Elevation','FV_Lith','HV_Lith'])
        if apex == 1:
            plt.scatter(juxt_df['Length'], juxt_df['Elevation'], marker = 'x', color = 'red')
        if apexid == 1:
            for jindex, jrow in juxt_df.iterrows():
                plt.text(jrow['Length'], jrow['Elevation'],jindex, color = 'darkred')
        
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
        plt.title(ul, loc='left')
        plt.title(ur, loc='right')
        plt.xlabel(f"Distance along mean strike ({self.unit_xy})")
        plt.ylabel(f"Elevation  ({self.z_select_to_unit()})")
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

License: GNU General Public License v3.0
This is free software; you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

For source code and license details, visit:
https://www.gnu.org/licenses/gpl-3.0.html

© 2025 - John-Are Hansen"""
        messagebox.showinfo("About EFA", about_text)



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


def hlegend(hcolor_df,zcolor_df):
    """
    Create a legend for the horizon plots.
    """
    custum_legend = []
    custum_legend.append(Patch(facecolor='white', edgecolor='white', label='Horizons'))
    for index, row in hcolor_df.iterrows():
        #custum_legend.append(Line2D([0], [0], color=hcolor_df[i-1], lw=1, label=list(fv_df)[i]+'_footwall'))
        custum_legend.append(Line2D([0], [0], color=row['Color'], lw=1, label = row['Alias'] +'_footwall'))
        custum_legend.append(Line2D([0], [0], color=row['Color'],linestyle='--', lw=1, label = row['Alias'] +'_hangingwall'))
        #print(index)
        #print(row)
    custum_legend.append(Patch(facecolor='white', edgecolor='white', label=''))
    custum_legend.append(Patch(facecolor='white', edgecolor='white', label='Zone Lithology'))
    for index, row in zcolor_df.iterrows():
        ztype = '_No Res.'
        if row['Color'] == 'orange':
            ztype = '_Poor Res.'
        elif row['Color'] == 'yellow':
            ztype = '_Good Res.'
        elif row['Color'] == 'red':
            ztype = '_SR'
        elif row['Color'] == 'azure':
            ztype = '_Undefined'
        custum_legend.append(Patch(facecolor=row['Color'], alpha = 0.5,edgecolor=row['Color'], label=row['Alias'] + ztype))
    # Fixed symbol patches below
    custum_legend.append(Patch(facecolor='white', edgecolor='white', label=''))
    custum_legend.append(Patch(facecolor='white', edgecolor='white', label='Juxtaposition Scenario'))
    custum_legend.append(Patch(facecolor='green', edgecolor='green', label='Good-Good'))
    custum_legend.append(Patch(facecolor='yellow', edgecolor='yellow', label='Good-Poor'))
    #custum_legend.append(Patch(facecolor='red', edgecolor='red', label='Intermediate-Intermediate'))
    custum_legend.append(Patch(facecolor='orange', edgecolor='orange',label='Poor-Poor'))#changed from red to orange as requested
    custum_legend.append(Patch(facecolor='black', edgecolor='black', label='SR-res'))
    custum_legend.append(Patch(facecolor='LightGray', edgecolor='LightGray', label='Res-noRes'))
    custum_legend.append(Patch(facecolor='DarkGray', edgecolor='DarkGray', label='noRes-noRes'))
    custum_legend.append(Patch(facecolor='azure', edgecolor='azure', label='Undefined-Any'))
    fig, ax = plt.subplots()
    ax.legend(handles=custum_legend,loc='upper left')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.axis('off')
    return(fig)


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


def interpolate_throw(fv_df, juxt_df, throwarray):
    int_throw = interpolate.interp1d(fv_df['length'], np.nanmean(throwarray, axis=0))
    lenlist = juxt_df['Length'].tolist()
    lenthrow = int_throw(lenlist)
    juxt_df['Mean_Throw'] = lenthrow.round(2)
    return(juxt_df)


def main():
    app = EFA_juxtaposition()
    app.mainloop()


if __name__ == "__main__":
    main()