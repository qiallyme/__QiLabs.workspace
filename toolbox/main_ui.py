import os
import queue
import threading
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- AUTO-IMPORTS START ---
from tools.build.tool_template import CustomModuleTool
from tools.dev.export_blueprint import ExportBlueprintTool
from tools.dev.extractor import TextExtractorTool
from tools.dev.git_push import GitPushTool
from tools.dev.repo_triage import RepoTriageTool
from tools.dev.rule_tester import RuleTesterTool
from tools.docs.pdf_splitter import BulkPdfSplitterTool
from tools.finance.firefly_bills_importer import FireflyBillsImporterTool
from tools.finance.tax_compiler import TaxPdfCompilerTool
from tools.finance.zai_ledger_importer import ZaiLedgerImporterTool
from tools.media.video_converter import VideoConverterTool
from tools.organize.archivist import ArchiveRouterTool
from tools.organize.bloat_destroyer import DestroyerTool
from tools.organize.downloads_inspector import DownloadsInspectorTool
from tools.organize.file_cleaner import FilenameCleanerTool
from tools.organize.folder_flattener import FolderFlattenerTool
from tools.organize.unlock_downloads import UnblockDownloadsTool
from tools.organize.unzip_sync import UnzipSyncTool
from tools.organize.vault_router import VaultRouterTool
from tools.system.qilabs_structure_checker import QiLabsStructureCheckerTool
from tools.system.sys_directory_markmind_mapper import DirectoryMarkmindMapperTool
from tools.system.sys_docs_compiler import SysDocsCompilerTool
# --- AUTO-IMPORTS END ---


class SnapshotVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class SnapshotText:
    def __init__(self, value):
        self._value = value

    def get(self, *_args, **_kwargs):
        return self._value


class QiOneShell:
    BG = "#0b1020"
    PANEL = "#121a2b"
    PANEL_2 = "#182338"
    PANEL_3 = "#202d45"
    SIDEBAR = "#0d1423"
    BORDER = "#2a3b58"
    TEXT = "#edf3ff"
    MUTED = "#8ea2c7"
    ACCENT = "#4ecdc4"
    ACCENT_2 = "#7ee7de"
    ACCENT_3 = "#315c8d"
    SUCCESS = "#47d16c"
    DANGER = "#ff6b6b"
    WARNING = "#ffc857"
    INFO = "#6ea8fe"
    CONSOLE_BG = "#08111e"
    CONSOLE_TEXT = "#d4f7db"
    SEARCH_BG = "#10192a"

    def __init__(self, root):
        self.root = root
        self.root.title("QiOne Desktop Tools")
        self.root.geometry("1480x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg=self.BG)

        # --- AUTO-REGISTER START ---
        self.tools = [CustomModuleTool(), ExportBlueprintTool(), TextExtractorTool(), GitPushTool(), RepoTriageTool(), RuleTesterTool(), BulkPdfSplitterTool(), FireflyBillsImporterTool(), TaxPdfCompilerTool(), ZaiLedgerImporterTool(), VideoConverterTool(), ArchiveRouterTool(), DestroyerTool(), DownloadsInspectorTool(), FilenameCleanerTool(), FolderFlattenerTool(), UnblockDownloadsTool(), UnzipSyncTool(), VaultRouterTool(), QiLabsStructureCheckerTool(), DirectoryMarkmindMapperTool(), SysDocsCompilerTool()]
        # --- AUTO-REGISTER END ---

        self.tool_specs = self._build_tool_specs(self.tools)
        self.active_tool = None
        self.active_tool_card = None
        self.run_sessions = []
        self.run_counter = 0
        self.shared_path = tk.StringVar(value=os.getcwd())
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="0 running  0 completed")
        self.selected_tool_var = tk.StringVar(value="No tool selected")
        self.selected_bucket_var = tk.StringVar(value="Choose a tool from the left rail.")
        self.ui_queue = queue.Queue()

        self.setup_styles()
        self.build_shell()
        self.search_var.trace_add("write", lambda *_args: self.refresh_tool_list())
        self.root.after(50, self.process_ui_queue)

        if self.tool_specs:
            self.load_tool(self.tool_specs[0]["tool"])

    def _build_tool_specs(self, tools):
        specs = []
        for tool in tools:
            module_parts = tool.__module__.split(".")
            bucket = module_parts[1] if len(module_parts) > 2 else "misc"
            specs.append({
                "tool": tool,
                "bucket": bucket,
                "bucket_label": bucket.replace("_", " ").title(),
                "name": tool.get_name(),
            })
        return sorted(specs, key=lambda spec: (spec["bucket"], spec["name"].lower()))

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.BG)
        style.configure("Header.TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 22, "bold"))
        style.configure("SubHeader.TLabel", background=self.BG, foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("CardBody.TLabel", background=self.PANEL, foreground=self.MUTED, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self.BG, foreground=self.ACCENT_2, font=("Segoe UI", 9, "bold"))
        style.configure("Qi.Horizontal.TProgressbar", troughcolor=self.PANEL_3, background=self.ACCENT, bordercolor=self.BORDER, lightcolor=self.ACCENT, darkcolor=self.ACCENT)
        style.configure("Qi.TNotebook", background=self.PANEL, borderwidth=0)
        style.configure("Qi.TNotebook.Tab", background=self.PANEL_2, foreground=self.MUTED, padding=(12, 8), borderwidth=0)
        style.map("Qi.TNotebook.Tab", background=[("selected", self.PANEL_3)], foreground=[("selected", self.TEXT)])

    def make_card(self, parent, *, fill="x", expand=False, pad=16):
        card = tk.Frame(parent, bg=self.PANEL, highlightthickness=1, highlightbackground=self.BORDER, bd=0)
        card.pack(fill=fill, expand=expand, pady=(0, 14))
        inner = tk.Frame(card, bg=self.PANEL, padx=pad, pady=pad)
        inner.pack(fill="both", expand=True)
        return card, inner

    def build_shell(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(outer, bg=self.SIDEBAR, width=300)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = tk.Frame(outer, bg=self.BG, padx=18, pady=18)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.build_sidebar()
        self.build_main_area()

    def build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=self.SIDEBAR, padx=20, pady=18)
        brand.pack(fill="x")

        tk.Label(brand, text="QiOne Toolbox", bg=self.SIDEBAR, fg=self.TEXT, font=("Segoe UI Semibold", 19)).pack(anchor="w")
        tk.Label(brand, text="Admin and developer operations cockpit", bg=self.SIDEBAR, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        search_wrap = tk.Frame(self.sidebar, bg=self.SIDEBAR, padx=18, pady=4)
        search_wrap.pack(fill="x")

        self.search_entry = tk.Entry(
            search_wrap,
            textvariable=self.search_var,
            bg=self.SEARCH_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
        )
        self.search_entry.pack(fill="x", ipady=10, padx=2)

        rail_header = tk.Frame(self.sidebar, bg=self.SIDEBAR, padx=20, pady=8)
        rail_header.pack(fill="x", pady=(0, 2))
        tk.Label(rail_header, text="TOOLS", bg=self.SIDEBAR, fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.tool_count_label = tk.Label(rail_header, text="", bg=self.SIDEBAR, fg=self.ACCENT_2, font=("Segoe UI", 9, "bold"))
        self.tool_count_label.pack(side="right")

        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=self.SIDEBAR, highlightthickness=0, bd=0)
        sidebar_scrollbar = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_inner = tk.Frame(self.sidebar_canvas, bg=self.SIDEBAR)

        self.sidebar_inner.bind("<Configure>", lambda _event: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_inner, anchor="nw", width=280)
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)

        # Mouse wheel scrolling for Windows
        def _on_sidebar_mousewheel(event):
            self.sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_sidebar_wheel(_event=None):
            self.sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel)

        def _unbind_sidebar_wheel(_event=None):
            self.sidebar_canvas.unbind_all("<MouseWheel>")

        self.sidebar_canvas.bind("<Enter>", _bind_sidebar_wheel)
        self.sidebar_canvas.bind("<Leave>", _unbind_sidebar_wheel)
        self.sidebar_inner.bind("<Enter>", _bind_sidebar_wheel)
        self.sidebar_inner.bind("<Leave>", _unbind_sidebar_wheel)

        self.sidebar_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        sidebar_scrollbar.pack(side="right", fill="y", pady=(0, 10))

        self.refresh_tool_list()

    def build_main_area(self):
        topbar = tk.Frame(self.main_area, bg=self.BG)
        topbar.pack(fill="x", pady=(0, 14))

        left = tk.Frame(topbar, bg=self.BG)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="QiOne Desktop Tools", style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, text="Parallel runs, isolated tool sessions, and repo utility workflows.", style="SubHeader.TLabel").pack(anchor="w", pady=(2, 0))

        right = tk.Frame(topbar, bg=self.BG)
        right.pack(side="right")
        ttk.Label(right, textvariable=self.status_var, style="Status.TLabel").pack(anchor="e")
        tk.Label(right, textvariable=self.summary_var, bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="e", pady=(4, 0))

        _, path_inner = self.make_card(self.main_area)
        tk.Label(path_inner, text="Workspace Target", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(path_inner, text="Each launched run snapshots this path and the current tool settings.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        path_row = tk.Frame(path_inner, bg=self.PANEL)
        path_row.pack(fill="x")

        self.path_entry = tk.Entry(
            path_row,
            textvariable=self.shared_path,
            bg=self.SEARCH_BG,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 10))

        self.make_button(path_row, "Repo Root", self.use_repo_root, bg=self.PANEL_3, fg=self.TEXT).pack(side="right", padx=(8, 0))
        self.make_button(path_row, "Browse", self.browse, bg=self.ACCENT, fg="#08111e").pack(side="right")

        body = tk.PanedWindow(self.main_area, orient="horizontal", bg=self.BG, sashwidth=8, showhandle=False)
        body.pack(fill="both", expand=True)

        editor_panel = tk.Frame(body, bg=self.BG, width=470)
        runner_panel = tk.Frame(body, bg=self.BG)
        body.add(editor_panel, minsize=360)
        body.add(runner_panel, minsize=480)

        self.build_editor_panel(editor_panel)
        self.build_runner_panel(runner_panel)

    def build_editor_panel(self, parent):
        _, tool_inner = self.make_card(parent, fill="both", expand=True)

        header = tk.Frame(tool_inner, bg=self.PANEL)
        header.pack(fill="x", pady=(0, 10))

        label_col = tk.Frame(header, bg=self.PANEL)
        label_col.pack(side="left", fill="x", expand=True)

        tk.Label(label_col, textvariable=self.selected_tool_var, bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(label_col, textvariable=self.selected_bucket_var, bg=self.PANEL, fg=self.ACCENT_2, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 0))

        hint = tk.Frame(tool_inner, bg=self.PANEL_2, padx=12, pady=10)
        hint.pack(fill="x", pady=(0, 12))
        tk.Label(
            hint,
            text="Launches create independent run sessions, so you can keep scans, imports, and builds running together.",
            bg=self.PANEL_2,
            fg=self.MUTED,
            justify="left",
            wraplength=360,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        settings_shell = tk.Frame(tool_inner, bg=self.PANEL)
        settings_shell.pack(fill="both", expand=True)

        self.tool_settings_canvas = tk.Canvas(settings_shell, bg=self.PANEL, highlightthickness=0, bd=0)
        settings_scroll = ttk.Scrollbar(settings_shell, orient="vertical", command=self.tool_settings_canvas.yview)
        self.tool_ui_container = tk.Frame(self.tool_settings_canvas, bg=self.PANEL)

        self.tool_ui_container.bind("<Configure>", lambda _event: self.tool_settings_canvas.configure(scrollregion=self.tool_settings_canvas.bbox("all")))
        self.tool_settings_canvas.create_window((0, 0), window=self.tool_ui_container, anchor="nw", width=420)
        self.tool_settings_canvas.configure(yscrollcommand=settings_scroll.set)

        def _on_settings_mousewheel(event):
            self.tool_settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_settings_wheel(_event=None):
            self.tool_settings_canvas.bind_all("<MouseWheel>", _on_settings_mousewheel)

        def _unbind_settings_wheel(_event=None):
            self.tool_settings_canvas.unbind_all("<MouseWheel>")

        self.tool_settings_canvas.bind("<Enter>", _bind_settings_wheel)
        self.tool_settings_canvas.bind("<Leave>", _unbind_settings_wheel)
        self.tool_ui_container.bind("<Enter>", _bind_settings_wheel)
        self.tool_ui_container.bind("<Leave>", _unbind_settings_wheel)

        self.tool_settings_canvas.pack(side="left", fill="both", expand=True)
        settings_scroll.pack(side="right", fill="y")

        _, action_inner = self.make_card(parent)
        tk.Label(action_inner, text="Launch", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(action_inner, text="Queue a dry run or a live execution without interrupting existing sessions.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 10))

        btn_row = tk.Frame(action_inner, bg=self.PANEL)
        btn_row.pack(fill="x")

        self.make_button(btn_row, "Queue Scan", lambda: self.queue_run(False), bg=self.SUCCESS, fg="#08111e", expand=True).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.make_button(btn_row, "Queue Execute", lambda: self.queue_run(True), bg=self.DANGER, fg="white", expand=True).pack(side="left", fill="x", expand=True, padx=6)
        self.make_button(btn_row, "Cancel Active View", self.cancel_selected_run, bg=self.WARNING, fg="#08111e", expand=True).pack(side="left", fill="x", expand=True, padx=(6, 0))

    def build_runner_panel(self, parent):
        _, run_inner = self.make_card(parent)

        header = tk.Frame(run_inner, bg=self.PANEL)
        header.pack(fill="x", pady=(0, 10))
        title_col = tk.Frame(header, bg=self.PANEL)
        title_col.pack(side="left", fill="x", expand=True)
        tk.Label(title_col, text="Run Queue", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(title_col, text="Each card represents an isolated execution session.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        action_col = tk.Frame(header, bg=self.PANEL)
        action_col.pack(side="right")
        self.make_button(action_col, "Clear Completed", self.clear_completed_sessions, bg=self.PANEL_3, fg=self.TEXT).pack(side="right")

        self.run_list_canvas = tk.Canvas(run_inner, bg=self.PANEL, highlightthickness=0, bd=0, height=240)
        run_scroll = ttk.Scrollbar(run_inner, orient="vertical", command=self.run_list_canvas.yview)
        self.run_list_inner = tk.Frame(self.run_list_canvas, bg=self.PANEL)

        self.run_list_inner.bind("<Configure>", lambda _event: self.run_list_canvas.configure(scrollregion=self.run_list_canvas.bbox("all")))
        self.run_list_canvas.create_window((0, 0), window=self.run_list_inner, anchor="nw", width=730)
        self.run_list_canvas.configure(yscrollcommand=run_scroll.set)

        def _on_runlist_mousewheel(event):
            self.run_list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_runlist_wheel(_event=None):
            self.run_list_canvas.bind_all("<MouseWheel>", _on_runlist_mousewheel)

        def _unbind_runlist_wheel(_event=None):
            self.run_list_canvas.unbind_all("<MouseWheel>")

        self.run_list_canvas.bind("<Enter>", _bind_runlist_wheel)
        self.run_list_canvas.bind("<Leave>", _unbind_runlist_wheel)
        self.run_list_inner.bind("<Enter>", _bind_runlist_wheel)
        self.run_list_inner.bind("<Leave>", _unbind_runlist_wheel)

        self.run_list_canvas.pack(side="left", fill="both", expand=True)
        run_scroll.pack(side="right", fill="y")

        _, console_inner = self.make_card(parent, fill="both", expand=True)
        console_header = tk.Frame(console_inner, bg=self.PANEL)
        console_header.pack(fill="x", pady=(0, 10))
        tk.Label(console_header, text="Run Console", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(console_header, text="Select a run card to focus its logs.", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(12, 0))

        self.console_notebook = ttk.Notebook(console_inner, style="Qi.TNotebook")
        self.console_notebook.pack(fill="both", expand=True)

        self.empty_console = tk.Frame(self.console_notebook, bg=self.CONSOLE_BG)
        tk.Label(
            self.empty_console,
            text="No runs launched yet.\nQueue a scan or execute run to start collecting logs.",
            bg=self.CONSOLE_BG,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            justify="center",
        ).pack(expand=True)
        self.console_notebook.add(self.empty_console, text="Overview")

    def make_button(self, parent, text, command, *, bg, fg, expand=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            font=("Segoe UI", 10, "bold" if expand else "normal"),
            cursor="hand2",
        )

    def refresh_tool_list(self):
        for widget in self.sidebar_inner.winfo_children():
            widget.destroy()

        search = self.search_var.get().strip().lower()
        visible_specs = [spec for spec in self.tool_specs if search in spec["name"].lower() or search in spec["bucket_label"].lower()]

        self.tool_count_label.configure(text=f"{len(visible_specs)} shown")

        current_bucket = None
        for spec in visible_specs:
            if spec["bucket"] != current_bucket:
                current_bucket = spec["bucket"]
                tk.Label(
                    self.sidebar_inner,
                    text=spec["bucket_label"].upper(),
                    bg=self.SIDEBAR,
                    fg=self.MUTED,
                    font=("Segoe UI", 8, "bold"),
                    padx=12,
                    pady=6,
                    anchor="w",
                ).pack(fill="x", pady=(10, 2))

            card = tk.Frame(
                self.sidebar_inner,
                bg=self.ACCENT_3 if spec["tool"] == self.active_tool else "#142038",
                highlightthickness=1,
                highlightbackground=self.ACCENT if spec["tool"] == self.active_tool else self.BORDER,
                bd=0,
                cursor="hand2",
            )
            card.pack(fill="x", padx=8, pady=4)

            inner = tk.Frame(card, bg=card["bg"], padx=12, pady=10, cursor="hand2")
            inner.pack(fill="both", expand=True)

            title = tk.Label(inner, text=spec["name"], bg=card["bg"], fg=self.TEXT, font=("Segoe UI", 10, "bold"), anchor="w", justify="left", wraplength=228, cursor="hand2")
            title.pack(anchor="w")

            subtitle = tk.Label(inner, text=spec["bucket_label"], bg=card["bg"], fg=self.ACCENT_2 if spec["tool"] == self.active_tool else self.MUTED, font=("Segoe UI", 8), anchor="w", cursor="hand2")
            subtitle.pack(anchor="w", pady=(4, 0))

            for widget in (card, inner, title, subtitle):
                widget.bind("<Button-1>", lambda _event, tool=spec["tool"]: self.load_tool(tool))

        if not visible_specs:
            tk.Label(
                self.sidebar_inner,
                text="No tools match the current search.",
                bg=self.SIDEBAR,
                fg=self.MUTED,
                font=("Segoe UI", 9),
                padx=12,
                pady=18,
                anchor="w",
                justify="left",
            ).pack(fill="x")

        self.sidebar_canvas.after_idle(lambda: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        self.sidebar_canvas.after_idle(lambda: self.sidebar_canvas.yview_moveto(0))

    def browse(self):
        path = filedialog.askdirectory(title="Select target directory")
        if path:
            self.shared_path.set(path)
            self.status_var.set("Target directory updated")

    def use_repo_root(self):
        self.shared_path.set(os.getcwd())
        self.status_var.set("Target reset to repo root")

    def load_tool(self, tool):
        self.active_tool = tool
        bucket = "Misc"
        module_parts = tool.__module__.split(".")
        if len(module_parts) > 2:
            bucket = module_parts[1].replace("_", " ").title()

        self.selected_tool_var.set(tool.get_name())
        self.selected_bucket_var.set(f"{bucket} bucket")
        self.status_var.set(f"Loaded: {tool.get_name()}")

        for widget in self.tool_ui_container.winfo_children():
            widget.destroy()

        tool.build_ui(self.tool_ui_container)
        self.refresh_tool_list()

    def capture_tool_state(self, tool):
        snapshot = {}
        for name, value in vars(tool).items():
            if isinstance(value, tk.Variable):
                snapshot[name] = ("variable", self.snapshot_variable_value(value))
            elif isinstance(value, tk.Text):
                snapshot[name] = ("text", value.get("1.0", tk.END))
        return snapshot

    def snapshot_variable_value(self, variable):
        try:
            return variable.get()
        except tk.TclError:
            try:
                return variable._tk.globalgetvar(variable._name)
            except Exception:
                return ""

    def create_execution_tool(self, tool_class, snapshot):
        tool = tool_class()
        for name, payload in snapshot.items():
            state_type, value = payload
            if state_type == "variable":
                setattr(tool, name, SnapshotVar(value))
            elif state_type == "text":
                setattr(tool, name, SnapshotText(value))
        if hasattr(tool, "cancel_requested"):
            tool.cancel_requested = False
        if hasattr(tool, "reset_run_state"):
            tool.reset_run_state()
        return tool

    def get_tool_outcome(self, tool):
        if hasattr(tool, "get_run_status"):
            return tool.get_run_status()
        return "success", ""

    def queue_run(self, is_live):
        if not self.active_tool:
            messagebox.showinfo("No Tool Selected", "Choose a tool before launching a run.")
            return

        target_path = self.shared_path.get().strip()
        if not os.path.isdir(target_path):
            messagebox.showerror("Invalid Directory", "The selected target directory does not exist.")
            self.status_var.set("Invalid target directory")
            return

        if is_live and not messagebox.askyesno(
            "Confirm Live Execution",
            "Launch a live run against the selected directory?\n\nThis will not stop existing runs.",
        ):
            return

        snapshot = self.capture_tool_state(self.active_tool)
        run_tool = self.create_execution_tool(self.active_tool.__class__, snapshot)
        session = self.create_run_session(run_tool, self.active_tool.get_name(), target_path, is_live)

        self.status_var.set(f"Queued: {session['name']}")
        self.append_run_log(session, f"[{session['started_at']}] Session queued")
        self.append_run_log(session, f"Mode: {session['mode']}")
        self.append_run_log(session, f"Target: {session['path']}")
        self.append_run_log(session, "-" * 56)

        thread = threading.Thread(target=self._run_session, args=(session,), daemon=True)
        session["thread"] = thread
        thread.start()
        self.select_run(session)
        self.update_summary()

    def create_run_session(self, tool, name, path, is_live):
        self.run_counter += 1
        started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_id = f"R{self.run_counter:02d}"
        mode = "EXECUTE" if is_live else "SCAN"

        if len(self.console_notebook.tabs()) == 1 and self.console_notebook.tabs()[0] == str(self.empty_console):
            self.console_notebook.forget(self.empty_console)

        card = tk.Frame(self.run_list_inner, bg=self.PANEL_2, highlightthickness=1, highlightbackground=self.BORDER, bd=0)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=self.PANEL_2, padx=12, pady=12)
        inner.pack(fill="both", expand=True)

        header = tk.Frame(inner, bg=self.PANEL_2)
        header.pack(fill="x")

        title = tk.Label(header, text=f"{session_id}  {name}", bg=self.PANEL_2, fg=self.TEXT, font=("Segoe UI", 10, "bold"), anchor="w")
        title.pack(side="left", fill="x", expand=True)

        status_var = tk.StringVar(value="Queued")
        status_label = tk.Label(header, textvariable=status_var, bg=self.PANEL_2, fg=self.INFO, font=("Segoe UI", 9, "bold"))
        status_label.pack(side="right")

        meta = tk.Label(inner, text=f"{mode}  {path}", bg=self.PANEL_2, fg=self.MUTED, font=("Segoe UI", 8), anchor="w", justify="left", wraplength=640)
        meta.pack(fill="x", pady=(6, 8))

        progress = ttk.Progressbar(inner, mode="determinate", style="Qi.Horizontal.TProgressbar")
        progress.pack(fill="x")

        card_buttons = tk.Frame(inner, bg=self.PANEL_2)
        card_buttons.pack(fill="x", pady=(10, 0))

        view_btn = self.make_button(card_buttons, "View", lambda: self.select_run(session), bg=self.PANEL_3, fg=self.TEXT)
        view_btn.pack(side="left")

        cancel_btn = self.make_button(card_buttons, "Cancel", lambda: self.cancel_session(session), bg=self.WARNING, fg="#08111e")
        cancel_btn.pack(side="left", padx=8)

        remove_btn = self.make_button(card_buttons, "Remove", lambda: self.remove_session(session), bg=self.PANEL_3, fg=self.TEXT)
        remove_btn.pack(side="left")
        remove_btn.configure(state="disabled")

        tab = tk.Frame(self.console_notebook, bg=self.CONSOLE_BG)
        tab_header = tk.Frame(tab, bg=self.CONSOLE_BG)
        tab_header.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(tab_header, text=f"{session_id}  {name}", bg=self.CONSOLE_BG, fg=self.TEXT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(tab_header, text=f"{mode}  {path}", bg=self.CONSOLE_BG, fg=self.MUTED, font=("Segoe UI", 8)).pack(side="right")

        text_wrap = tk.Frame(tab, bg=self.CONSOLE_BG)
        text_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        log_text = tk.Text(
            text_wrap,
            bg=self.CONSOLE_BG,
            fg=self.CONSOLE_TEXT,
            insertbackground=self.CONSOLE_TEXT,
            font=("Cascadia Code", 10),
            borderwidth=0,
            relief="flat",
            padx=12,
            pady=12,
            wrap="word",
        )
        log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=log_text.yview)
        log_scroll.pack(side="right", fill="y")
        log_text.configure(yscrollcommand=log_scroll.set)

        self.console_notebook.add(tab, text=f"{session_id} {mode}")

        session = {
            "id": session_id,
            "name": name,
            "mode": mode,
            "path": path,
            "tool": tool,
            "is_live": is_live,
            "started_at": started_at,
            "status": status_var,
            "status_label": status_label,
            "progress": progress,
            "card": card,
            "tab": tab,
            "log_text": log_text,
            "cancel_button": cancel_btn,
            "remove_button": remove_btn,
            "view_button": view_btn,
            "complete": False,
            "thread": None,
        }

        self.run_sessions.append(session)

        for widget in (card, inner, title, meta, progress):
            widget.bind("<Button-1>", lambda _event, target=session: self.select_run(target))

        return session

    def append_run_log(self, session, message):
        self.enqueue_ui(self._append_run_log, session, message)

    def _append_run_log(self, session, message):
        session["log_text"].insert(tk.END, f"{message}\n")
        session["log_text"].see(tk.END)

    def set_run_progress(self, session, value):
        self.enqueue_ui(self._set_run_progress, session, value)

    def _set_run_progress(self, session, value):
        session["progress"].configure(value=max(0, min(100, value)))

    def set_session_status(self, session, label, color):
        self.enqueue_ui(self._set_session_status, session, label, color)

    def _set_session_status(self, session, label, color):
        session["status"].set(label)
        session["status_label"].configure(fg=color)

    def _run_session(self, session):
        self.set_session_status(session, "Running", self.ACCENT_2)
        try:
            session["tool"].execute(
                session["path"],
                session["is_live"],
                lambda message: self.append_run_log(session, message),
                lambda value: self.set_run_progress(session, value),
            )
            if getattr(session["tool"], "cancel_requested", False):
                final_status = ("Canceled", self.WARNING)
            else:
                run_status, run_message = self.get_tool_outcome(session["tool"])
                if run_message:
                    self.append_run_log(session, f"Outcome: {run_message}")
                if run_status == "failed":
                    final_status = ("Failed", self.DANGER)
                elif run_status == "warning":
                    final_status = ("Completed with issues", self.WARNING)
                else:
                    final_status = ("Completed", self.SUCCESS)
                    self.set_run_progress(session, 100)
        except Exception:
            self.append_run_log(session, "ERROR: Unhandled exception")
            self.append_run_log(session, traceback.format_exc())
            final_status = ("Failed", self.DANGER)
        finally:
            self.enqueue_ui(self.finish_session, session, final_status[0], final_status[1])

    def finish_session(self, session, label, color):
        session["complete"] = True
        session["cancel_button"].configure(state="disabled")
        session["remove_button"].configure(state="normal")
        self._set_session_status(session, label, color)
        self.status_var.set(f"{label}: {session['name']}")
        self.update_summary()

    def select_run(self, session):
        for item in self.run_sessions:
            is_selected = item is session
            item["card"].configure(highlightbackground=self.ACCENT if is_selected else self.BORDER)
            bg = self.PANEL_3 if is_selected else self.PANEL_2
            item["card"].configure(bg=bg)
            item["card"].winfo_children()[0].configure(bg=bg)
            for child in item["card"].winfo_children()[0].winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=bg)
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Label):
                            grandchild.configure(bg=bg)
                elif isinstance(child, tk.Label):
                    child.configure(bg=bg)

        self.console_notebook.select(session["tab"])

    def cancel_session(self, session):
        if session["complete"]:
            return
        if hasattr(session["tool"], "cancel_requested"):
            session["tool"].cancel_requested = True
        self.set_session_status(session, "Canceling", self.WARNING)
        self.append_run_log(session, "Cancellation requested by user.")
        self.status_var.set(f"Cancel requested: {session['name']}")

    def cancel_selected_run(self):
        current = self.console_notebook.select()
        for session in self.run_sessions:
            if str(session["tab"]) == current:
                self.cancel_session(session)
                return

    def remove_session(self, session):
        if not session["complete"]:
            return
        if str(session["tab"]) in self.console_notebook.tabs():
            self.console_notebook.forget(session["tab"])
        session["card"].destroy()
        self.run_sessions = [item for item in self.run_sessions if item is not session]
        if not self.run_sessions and self.empty_console not in [self.root.nametowidget(tab) for tab in self.console_notebook.tabs()]:
            self.console_notebook.add(self.empty_console, text="Overview")
        self.update_summary()
        self.status_var.set("Run removed")

    def clear_completed_sessions(self):
        completed = [session for session in list(self.run_sessions) if session["complete"]]
        for session in completed:
            self.remove_session(session)
        if completed:
            self.status_var.set("Completed runs cleared")

    def update_summary(self):
        running = sum(1 for session in self.run_sessions if not session["complete"])
        completed = sum(1 for session in self.run_sessions if session["complete"])
        self.summary_var.set(f"{running} running  {completed} completed")

    def enqueue_ui(self, callback, *args):
        self.ui_queue.put((callback, args))

    def process_ui_queue(self):
        try:
            while True:
                callback, args = self.ui_queue.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        try:
            self.root.after(50, self.process_ui_queue)
        except tk.TclError:
            return


if __name__ == "__main__":
    app_root = tk.Tk()
    shell = QiOneShell(app_root)
    app_root.mainloop()
