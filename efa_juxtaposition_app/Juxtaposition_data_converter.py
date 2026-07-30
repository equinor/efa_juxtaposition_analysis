import io
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd


def _is_non_numeric(value):
    try:
        float(str(value).strip())
    except (TypeError, ValueError):
        return True
    return False


def load_dataframe_from_text(text, sep=None):
    """Parse raw text (file contents or clipboard) into a pandas DataFrame.

    When ``sep`` is None the delimiter is sniffed by the python engine. The
    first row is treated as a header only when every cell in it is non-numeric.
    Values are kept as strings so they can be edited without reformatting.
    """
    if text is None:
        return pd.DataFrame()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized.strip():
        return pd.DataFrame()

    df = pd.read_csv(
        io.StringIO(normalized),
        sep=sep,
        engine="python",
        header=None,
        skip_blank_lines=True,
        dtype=str,
    )

    first_row = df.iloc[0].tolist()
    if all(_is_non_numeric(v) for v in first_row):
        df.columns = [str(v).strip() for v in first_row]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [f"col{i + 1}" for i in range(df.shape[1])]
    return df


class EditableTable(ttk.Frame):
    """A ttk.Treeview backed table whose cells can be edited in place."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._columns = []
        self._editor = None

        toolbar = tk.Frame(self)
        toolbar.pack(fill="x")
        tk.Button(toolbar, text="Add Row", command=self.add_row).pack(
            side="left", padx=2, pady=2
        )
        tk.Button(
            toolbar, text="Delete Row", command=self.delete_selected_rows
        ).pack(side="left", padx=2, pady=2)

        container = tk.Frame(self)
        container.pack(expand=True, fill="both")
        self.tree = ttk.Treeview(container, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._begin_edit)

    def set_dataframe(self, df):
        """Replace the table contents with the rows/columns of ``df``."""
        self._cancel_edit()
        self.tree.delete(*self.tree.get_children())

        columns = [str(c) for c in df.columns]
        # Treeview needs unique column identifiers even if headers repeat.
        seen = {}
        unique = []
        for name in columns:
            if name in seen:
                seen[name] += 1
                unique.append(f"{name}.{seen[name]}")
            else:
                seen[name] = 0
                unique.append(name)
        self._columns = unique

        self.tree["columns"] = unique
        for original, ident in zip(columns, unique):
            self.tree.heading(ident, text=original)
            self.tree.column(ident, width=100, anchor="w", stretch=True)

        for _, row in df.iterrows():
            values = ["" if pd.isna(v) else v for v in row.tolist()]
            self.tree.insert("", "end", values=values)

    def get_dataframe(self):
        """Return the current (possibly edited) table contents as a DataFrame."""
        headers = [self.tree.heading(ident)["text"] for ident in self._columns]
        rows = [self.tree.item(iid)["values"] for iid in self.tree.get_children()]
        return pd.DataFrame(rows, columns=headers)

    def add_row(self):
        if not self._columns:
            return
        self.tree.insert("", "end", values=["" for _ in self._columns])

    def delete_selected_rows(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)

    def _cancel_edit(self):
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None

    def _begin_edit(self, event):
        self._cancel_edit()
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            self._edit_heading(event)
            return
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, width, height = bbox
        column_name = self._columns[int(col_id[1:]) - 1]
        current = self.tree.set(row_id, column_name)

        editor = tk.Entry(self.tree)
        editor.place(x=x, y=y, width=width, height=height)
        editor.insert(0, current)
        editor.focus_set()
        editor.select_range(0, tk.END)

        def commit(_event=None):
            self.tree.set(row_id, column_name, editor.get())
            self._cancel_edit()

        editor.bind("<Return>", commit)
        editor.bind("<KP_Enter>", commit)
        editor.bind("<Escape>", lambda _e: self._cancel_edit())
        editor.bind("<FocusOut>", commit)
        self._editor = editor

    def _edit_heading(self, event):
        col_id = self.tree.identify_column(event.x)
        if not col_id:
            return
        column_ident = self._columns[int(col_id[1:]) - 1]

        # Derive the heading position/size from the first data cell in the
        # column so it stays aligned even when horizontally scrolled.
        children = self.tree.get_children()
        if not children:
            return
        cell_box = self.tree.bbox(children[0], col_id)
        if not cell_box:
            return
        x, cell_y, width, _cell_height = cell_box
        current = self.tree.heading(column_ident)["text"]

        editor = tk.Entry(self.tree)
        editor.place(x=x, y=0, width=width, height=cell_y)
        editor.insert(0, current)
        editor.focus_set()
        editor.select_range(0, tk.END)

        def commit(_event=None):
            new_name = editor.get().strip()
            if new_name:
                self.tree.heading(column_ident, text=new_name)
            self._cancel_edit()

        editor.bind("<Return>", commit)
        editor.bind("<KP_Enter>", commit)
        editor.bind("<Escape>", lambda _e: self._cancel_edit())
        editor.bind("<FocusOut>", commit)
        self._editor = editor


class DataConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("DataConverter")
        self.root.geometry("1000x500")

        self.file_paths = {"Footwall": None, "Hangingwall": None}

        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)

        footwall_button = tk.Button(
            button_frame,
            text="Import Footwall XYZ",
            command=self.import_footwall,
            width=20,
            height=2,
        )
        footwall_button.pack(side="left", padx=5)

        footwall_paste_button = tk.Button(
            button_frame,
            text="Paste Footwall (Excel)",
            command=self.paste_footwall,
            width=20,
            height=2,
        )
        footwall_paste_button.pack(side="left", padx=5)

        hangingwall_button = tk.Button(
            button_frame,
            text="Import Hangingwall XYZ",
            command=self.import_hangingwall,
            width=20,
            height=2,
        )
        hangingwall_button.pack(side="left", padx=5)

        hangingwall_paste_button = tk.Button(
            button_frame,
            text="Paste Hangingwall (Excel)",
            command=self.paste_hangingwall,
            width=20,
            height=2,
        )
        hangingwall_paste_button.pack(side="left", padx=5)

        self.status_label = tk.Label(root, text="No file loaded.")
        self.status_label.pack(pady=5)

        paned = tk.PanedWindow(root, orient="horizontal", sashrelief="raised")
        paned.pack(expand=True, fill="both", padx=10, pady=10)
        self.paned = paned

        footwall_frame = tk.LabelFrame(paned, text="Footwall XYZ")
        self.footwall_name = tk.Label(
            footwall_frame, text="No file imported.", anchor="w"
        )
        self.footwall_name.pack(fill="x", padx=2, pady=2)
        self.footwall_table = EditableTable(footwall_frame)
        self.footwall_table.pack(expand=True, fill="both")
        paned.add(footwall_frame)

        hangingwall_frame = tk.LabelFrame(paned, text="Hangingwall XYZ")
        self.hangingwall_name = tk.Label(
            hangingwall_frame, text="No file imported.", anchor="w"
        )
        self.hangingwall_name.pack(fill="x", padx=2, pady=2)
        self.hangingwall_table = EditableTable(hangingwall_frame)
        self.hangingwall_table.pack(expand=True, fill="both")
        paned.add(hangingwall_frame)

        # Centre the sash once the panes have their real size so both start
        # out equally wide.
        paned.bind("<Configure>", self._center_sash_once)

        self.tables = {
            "Footwall": self.footwall_table,
            "Hangingwall": self.hangingwall_table,
        }
        self.name_labels = {
            "Footwall": self.footwall_name,
            "Hangingwall": self.hangingwall_name,
        }

        export_button = tk.Button(
            root,
            text="Export to Petrel points w. attributes",
            command=self.export_petrel,
            height=2,
        )
        export_button.pack(pady=10)

    def _center_sash_once(self, event):
        # Only run once, after the paned window has a usable width.
        if event.width > 1:
            self.paned.sash_place(0, event.width // 2, 0)
            self.paned.unbind("<Configure>")

    def import_footwall(self):
        self.import_data("Footwall")

    def import_hangingwall(self):
        self.import_data("Hangingwall")

    def paste_footwall(self):
        self.paste_data("Footwall")

    def paste_hangingwall(self):
        self.paste_data("Hangingwall")

    def paste_data(self, wall_type):
        try:
            raw = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(
                "Paste error",
                "The clipboard is empty. Copy rows from Excel first (Ctrl+C).",
            )
            return

        # Excel copies cells as tab-separated values with newline row breaks.
        try:
            df = load_dataframe_from_text(raw, sep="\t")
        except Exception as exc:  # noqa: BLE001 - surface any parse failure
            messagebox.showerror("Paste error", f"Could not parse clipboard:\n{exc}")
            return

        if df.empty:
            messagebox.showwarning(
                "Paste error", "No usable rows found on the clipboard."
            )
            return

        self.file_paths[wall_type] = "<pasted from Excel>"
        self.status_label.config(text=f"Pasted {wall_type} from clipboard")
        self.name_labels[wall_type].config(text="Pasted from Excel")
        self.tables[wall_type].set_dataframe(df)

    def import_data(self, wall_type):
        path = filedialog.askopenfilename(
            title=f"Select a {wall_type} XYZ file",
            filetypes=[
                ("Data files", "*.csv *.txt *.tsv *.xyz"),
                ("CSV files", "*.csv"),
                ("XYZ files", "*.xyz"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            messagebox.showerror("Import error", f"Could not read file:\n{exc}")
            return

        try:
            df = load_dataframe_from_text(content, sep=None)
        except Exception as exc:  # noqa: BLE001 - surface any parse failure
            messagebox.showerror("Import error", f"Could not parse file:\n{exc}")
            return

        if df.empty:
            messagebox.showwarning(
                "Import error", "No usable rows found in the file."
            )
            return

        self.file_paths[wall_type] = path
        self.status_label.config(text=f"Loaded {wall_type}: {path}")
        self.name_labels[wall_type].config(text=os.path.basename(path))
        self.tables[wall_type].set_dataframe(df)

    def export_petrel(self):
        footwall = self.footwall_table.get_dataframe()
        hangingwall = self.hangingwall_table.get_dataframe()

        if footwall.empty or hangingwall.empty:
            messagebox.showwarning(
                "Export error",
                "Both footwall and hangingwall data are required before export.",
            )
            return

        if list(footwall.columns) != list(hangingwall.columns):
            messagebox.showerror(
                "Export error",
                "Footwall and hangingwall tables must have identical columns.",
            )
            return

        if footwall.shape[1] < 3:
            messagebox.showwarning(
                "Export error",
                "At least three columns are required (X, Y, Z). Additional "
                "attribute columns are optional.",
            )
            return

        footwall = footwall.copy()
        hangingwall = hangingwall.copy()

        # The first three columns are always X, Y, Z; any further columns are
        # exported as additional DOUBLE attributes. Insert FaultContactType
        # right after Z so it precedes the optional extra attributes.
        footwall.insert(3, "FaultContactType", "1")
        hangingwall.insert(3, "FaultContactType", "2")

        merged = pd.concat([footwall, hangingwall], ignore_index=True)

        path = filedialog.asksaveasfilename(
            title="Export to Petrel points with attributes",
            defaultextension="",
            filetypes=[
                ("Petrel points", "*.*"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        # Build the Petrel "Points with attributes" header from the columns.
        header = [
            "# Petrel Points with attributes",
            "# Unit in X and Y direction: m",
            "# Unit in depth: m",
            "VERSION 1",
            "BEGIN HEADER",
        ]
        for index, column in enumerate(merged.columns):
            name = str(column)
            if index < 3:
                header.append(name)
            elif name == "FaultContactType":
                header.append(f"INT,{name}")
            else:
                header.append(f"DOUBLE,{name}")
        header.append("END HEADER")

        data_lines = [
            " ".join("" if pd.isna(v) else str(v) for v in row)
            for row in merged.itertuples(index=False, name=None)
        ]

        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(header + data_lines) + "\n")
        except OSError as exc:
            messagebox.showerror("Export error", f"Could not write file:\n{exc}")
            return

        self.status_label.config(text=f"Exported Petrel points: {path}")
        messagebox.showinfo(
            "Export complete",
            f"Wrote {len(data_lines)} points to:\n{path}",
        )


def main():
    root = tk.Tk()
    DataConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
