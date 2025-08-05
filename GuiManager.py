import queue
from random import random
import time
import customtkinter
import threading
import keyboard
import webbrowser
import tkinter as tk
import pyautogui
import os
import requests
from datetime import datetime

from DonationBanner import DonationBanner
from Events import Events

class Tooltip:
    """
    Manages a single Tkinter instance to show tooltips in a thread-safe way.
    The GUI runs in its own thread, and commands are sent to it via a queue.
    """
    def __init__(self):
        self.command_queue = queue.Queue()
        self.root = None
        self.tooltip_window = None
        self.after_id = None # To cancel scheduled hide events

        # The GUI will run in a separate thread
        self.gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self.gui_thread.start()

    def _run_gui(self):
        """This method runs in the dedicated GUI thread."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window

        # Start the command processing loop
        self._process_queue()

        # Start the Tkinter event loop
        self.root.mainloop()

    def _process_queue(self):
        """
        Check the command queue for tasks and execute them.
        This is the heart of the thread-safe communication.
        """
        try:
            # Get a command from the queue without blocking
            command, args = self.command_queue.get_nowait()
            if command == "show":
                self._show_tooltip(*args)
            elif command == "hide":
                self._hide_tooltip()
        except queue.Empty:
            pass # No commands? No problem.
        finally:
            # Schedule the next check
            if self.root:
                self.root.after(100, self._process_queue)

    def _show_tooltip(self, text, duration_ms, x, y, fg_color, bg_color):
        """Internal method to actually create and show the tooltip. MUST run in GUI thread."""
        # Check if root is available
        if not self.root:
            return
            
        # If a tooltip is already visible, hide it first
        if self.tooltip_window:
            self._hide_tooltip()

        # Create the new tooltip window
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Enhanced tooltip with rounded corners and better styling
        frame = tk.Frame(self.tooltip_window, background=bg_color, bd=0)
        frame.pack(fill="both", expand=True)
        
        label = tk.Label(frame, text=text,
                        background=bg_color,
                        foreground=fg_color,
                        relief="flat", borderwidth=0,
                        font=("Segoe UI", 10), padx=8, pady=5)
        label.pack()

        # Schedule the tooltip to be hidden
        self.after_id = self.root.after(duration_ms, self._hide_tooltip)

    def _hide_tooltip(self):
        """Internal method to hide the tooltip. MUST run in GUI thread."""
        # Cancel any pending hide command
        if self.after_id and self.root:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        # Destroy the window if it exists
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    # --- Public Methods (Can be called from ANY thread) ---

    def show(self, text, duration_ms=2000, offset_x=20, offset_y=10, fg_color="white", color="#2D2D2D"):
        """
        Public method to request a tooltip to be shown.
        This is thread-safe.
        """
        # Get mouse position at the time of the call
        mouse_x, mouse_y = pyautogui.position()
        x_pos = mouse_x + offset_x
        y_pos = mouse_y + offset_y

        # Put the command and its arguments onto the queue for the GUI thread to process
        args = (text, duration_ms, x_pos, y_pos, fg_color, color)
        self.command_queue.put(("show", args))
        
    def stop(self):
        """Stops the GUI thread gracefully."""
        if self.root:
            self.root.quit()
         
class GuiManager:
    """
    Manages the application's graphical user interface and user interactions.
    Separates GUI components from the core application logic.
    """
    def __init__(self, app_logic_callback=None, settings_manager=None):
        """
        Initializes the GUI.
        :param app_logic_callback: A function to call when the start button is pressed.
                                   This function should accept two arguments:
                                   (1) a dictionary of settings, and (2) a threading.Event to signal stopping.
        :param initial_settings: A dictionary with the initial settings to load into the GUI.
        :param save_settings_callback: A function to call to save the current settings.
        """
        self.app_logic_callback = app_logic_callback
        self.settings_manager = settings_manager
        self.initial_settings = settings_manager.get_settings() if settings_manager else {}
        self.save_settings_callback = settings_manager.save if settings_manager else None
        self.macro_thread = None
        self.stop_event = threading.Event()
        self.running = False
        self.log_count = 0
        self.version = self._get_version()
        self.startup_time = time.time()

        # --- Main Application Window Setup ---
        customtkinter.set_appearance_mode("system")  # Use system preference, but fallback to dark
        customtkinter.set_default_color_theme("blue")

        self.app = customtkinter.CTk()
        self.app.title("MooMan's Brainrot Macro") # Dont change without credit
        self.app.geometry("600x600")
        self.app.iconbitmap("data/favicon.ico")
        self.app.resizable(True, True)  # Allow window to be resized
        self.app.minsize(400, 600)  # Set minimum window size

        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self._apply_initial_settings()
        self._setup_hotkeys()
        self._update_filter_display()
        
        # Ensure the thread is stopped when the window is closed
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.tooltips = Tooltip()
        self.event_manager = Events()
        self.event_manager.subscribe("status_change", self.change_status)
        self.event_manager.subscribe("status_change", self.add_log)
        self.event_manager.subscribe("tooltip", self.tooltips.show)
        self.event_manager.subscribe("log", self.add_log)
        self.event_manager.subscribe("success", lambda msg: self.add_log(msg, level="success"))
        self.event_manager.subscribe("debug", lambda msg: self.add_log(msg, level="debug"))

    def run(self):
        """Starts the customtkinter main loop."""
        self.app.mainloop()

    def open_link(self, url):
        """Opens a URL in the default web browser."""
        webbrowser.open_new(url)

    def _create_widgets(self):
        """Creates and places all the widgets in the window."""
        # --- Top Header with Logo and Title ---
        header_frame = customtkinter.CTkFrame(self.app, corner_radius=0, fg_color="#1a1a2e", height=80)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_propagate(False)
        
        # Try to load logo image if available
        try:
            logo_path = "data/brainrot_logo.png"
            if os.path.exists(logo_path):
                logo_img = customtkinter.CTkImage(Image.open(logo_path), size=(60, 60))
                logo_label = customtkinter.CTkLabel(header_frame, image=logo_img, text="")
                logo_label.place(relx=0.05, rely=0.5, anchor="w")
            
            title_label = customtkinter.CTkLabel(
                header_frame, 
                text="MooMan's Brainrot Macro", # Dont change without credit
                font=customtkinter.CTkFont(size=26, weight="bold"),
                text_color="#ffffff"
            )
            title_label.place(relx=0.5, rely=0.38, anchor="center")
            self.title_label = title_label
            
            # Social links in a more subtle, modern style
            links_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
            links_frame.place(relx=0.5, rely=0.75, anchor="center")
            
            discord_btn = customtkinter.CTkButton(
                links_frame, 
                text="Join Discord", 
                corner_radius=8,
                height=25, 
                border_width=0,
                fg_color="#5865F2",
                hover_color="#4752c4",
                font=customtkinter.CTkFont(size=12),
                command=lambda: self.open_link("https://discord.gg/e2qCZknrks")
            )
            discord_btn.pack(side="left", padx=5)
            
            donate_btn = customtkinter.CTkButton(
                links_frame, 
                text="Support Developer", 
                corner_radius=8,
                height=25,
                border_width=0,
                fg_color="#16a34a",
                hover_color="#15803d",
                font=customtkinter.CTkFont(size=12),
                command=lambda: self.open_link("https://www.roblox.com/game-pass/1316222536/Steal-a-Brainrot-Macro-Donation")
            )
            donate_btn.pack(side="left", padx=5)
        except Exception as e:
            # Fallback to text-only header if image loading fails
            title_label = customtkinter.CTkLabel(
                header_frame, 
                text="MooMan's Brainrot Macro", 
                font=customtkinter.CTkFont(size=26, weight="bold")
            )
            title_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Main Content Area ---
        content_frame = customtkinter.CTkFrame(self.app, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # --- Tabbed Interface with Modern Styling ---
        self.tab_view = customtkinter.CTkTabview(
            content_frame, 
            segmented_button_selected_color="#2563eb",
            segmented_button_selected_hover_color="#1d4ed8",
            segmented_button_unselected_color="#334155",
            segmented_button_unselected_hover_color="#475569"
        )
        self.tab_view.grid(row=0, column=0, sticky="nsew")

        # Create tabs with better naming
        dashboard_tab = self.tab_view.add("Dashboard")
        filters_tab = self.tab_view.add("Scan Filters")
        log_tab = self.tab_view.add("Activity Log")
        
        # Configure tab layouts
        dashboard_tab.grid_columnconfigure(0, weight=1)
        filters_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(0, weight=1)
        
        # --- Dashboard Tab ---
        # Settings Card - Now first
        settings_card = self._create_card(dashboard_tab, "Basic Settings")
        settings_card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_card.grid_columnconfigure(1, weight=1)
        
        # Auto Collect Money Setting
        collect_label = customtkinter.CTkLabel(
            settings_card, 
            text="Auto Collect Money:",
            font=customtkinter.CTkFont(size=14),
            anchor="w"
        )
        collect_label.grid(row=2, column=0, padx=10, pady=(15, 5), sticky="w")
        
        collect_frame = customtkinter.CTkFrame(settings_card, fg_color="transparent")
        collect_frame.grid(row=2, column=1, padx=10, pady=(15, 5), sticky="ew")
        
        self.auto_collect_check = customtkinter.CTkSwitch(
            collect_frame, 
            text="",
            switch_width=40,
            switch_height=20,
            onvalue=True,
            offvalue=False
        )
        self.auto_collect_check.pack(side="left")
        self.auto_collect_check.select()
        
        collect_label2 = customtkinter.CTkLabel(collect_frame, text="Every")
        collect_label2.pack(side="left", padx=(10, 5))
        
        self.collect_money_interval_entry = customtkinter.CTkEntry(
            collect_frame, 
            placeholder_text="60", 
            width=60,
            height=30,
            border_width=1,
            corner_radius=5
        )
        self.collect_money_interval_entry.pack(side="left", padx=5)
        
        collect_seconds_label = customtkinter.CTkLabel(collect_frame, text="seconds")
        collect_seconds_label.pack(side="left", padx=5)
        
        # Auto Scan Setting
        scan_label = customtkinter.CTkLabel(
            settings_card, 
            text="Auto Scan for Brainrots:",
            font=customtkinter.CTkFont(size=14),
            anchor="w"
        )
        scan_label.grid(row=1, column=0, padx=10, pady=(5, 15), sticky="w")
        
        scan_frame = customtkinter.CTkFrame(settings_card, fg_color="transparent")
        scan_frame.grid(row=1, column=1, padx=10, pady=(5, 15), sticky="ew")
        
        self.auto_scan_check = customtkinter.CTkSwitch(
            scan_frame, 
            text="",
            switch_width=40,
            switch_height=20,
            onvalue=True,
            offvalue=False
        )
        self.auto_scan_check.pack(side="left")
        self.auto_scan_check.select()
        
        # Filter summary card - Now second
        filter_card = self._create_card(dashboard_tab, "Purchase Conditions")
        filter_card.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        self.filter_summary = customtkinter.CTkTextbox(
            filter_card, 
            height=80, 
            wrap="word",
            font=customtkinter.CTkFont(size=13)
        )
        self.filter_summary.grid(row=2, column=0, padx=15, pady=15, sticky="ew")
        self.filter_summary.insert("1.0", "No filters active. Macro will buy any Brainrot found.")
        self.filter_summary.configure(state="disabled")
        
        # Add spacer to push controls to bottom
        spacer_frame = customtkinter.CTkFrame(dashboard_tab, fg_color="transparent", height=20)
        spacer_frame.grid(row=2, column=0, sticky="ew")
        
        # Control buttons at the bottom - removed the title
        controls_card = self._create_card(dashboard_tab)  # Removed "Controls" title
        controls_card.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        controls_card.grid_columnconfigure((0, 1), weight=1)
        
        self.start_button = customtkinter.CTkButton(
            controls_card, 
            text="Start Macro (F5)", 
            command=self.start_macro,
            fg_color="#16a34a",
            hover_color="#15803d",
            height=40,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            corner_radius=8
        )
        self.start_button.grid(row=0, column=0, padx=10, pady=15, sticky="ew")  # Changed row from 2 to 0
        
        self.stop_button = customtkinter.CTkButton(
            controls_card, 
            text="Stop Macro (F7)", 
            command=self.stop_macro,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=40,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=10, pady=15, sticky="ew")  # Changed row from 2 to 0
        
        # --- Filters Tab ---
        filters_frame = customtkinter.CTkFrame(filters_tab, fg_color="transparent")
        filters_frame.grid(row=0, column=0, padx=20, pady=20, sticky="new")
        filters_frame.grid_columnconfigure(1, weight=1)
        
        # Income filter with better styling
        income_label = customtkinter.CTkLabel(
            filters_frame, 
            text="Income Filter",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        income_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")
        
        income_desc = customtkinter.CTkLabel(
            filters_frame,
            text="Only purchase Brainrots with income above a certain threshold",
            font=customtkinter.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        income_desc.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
        
        self.income_filter_check = customtkinter.CTkCheckBox(
            filters_frame, 
            text="Enable income filter",
            command=self._update_filter_display,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=3
        )
        self.income_filter_check.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.income_filter_check.select()
        
        income_entry_frame = customtkinter.CTkFrame(filters_frame, fg_color="transparent")
        income_entry_frame.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        income_min_label = customtkinter.CTkLabel(income_entry_frame, text="Minimum income:")
        income_min_label.pack(side="left", padx=(0, 5))
        
        self.income_entry = customtkinter.CTkEntry(
            income_entry_frame, 
            placeholder_text="100",
            width=80,
            height=30,
            border_width=1
        )
        self.income_entry.pack(side="left", padx=5)
        self.income_entry.bind("<KeyRelease>", lambda e: self._update_filter_display())
        
        # Separator
        separator = customtkinter.CTkFrame(filters_frame, height=1, fg_color="gray")
        separator.grid(row=3, column=0, columnspan=2, padx=10, pady=20, sticky="ew")
        
        # Rarity filter with better styling
        rarity_label = customtkinter.CTkLabel(
            filters_frame, 
            text="Rarity Filter",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        rarity_label.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="w")
        
        rarity_desc = customtkinter.CTkLabel(
            filters_frame,
            text="Only purchase Brainrots of a minimum rarity level",
            font=customtkinter.CTkFont(size=12),
            text_color="gray",
            anchor="w"
        )
        rarity_desc.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
        
        min_rarity_label = customtkinter.CTkLabel(
            filters_frame, 
            text="Minimum rarity level:",
            anchor="w"
        )
        min_rarity_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        
        self.min_rarity_combo = customtkinter.CTkComboBox(
            filters_frame, 
            values=["N/A", "Common", "Rare", "Epic", "Legendary", "Mythic", "Brainrot God", "Secret"],
            command=lambda e: self._update_filter_display(),
            width=200,
            height=30,
            dropdown_hover_color="#3b82f6"
        )
        self.min_rarity_combo.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.min_rarity_combo.set("N/A")
        
        # --- Activity Log Tab ---
        log_frame = customtkinter.CTkFrame(log_tab, fg_color="transparent")
        log_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Enhanced log display with timestamps and better formatting
        self.scan_log_text = customtkinter.CTkTextbox(
            log_frame, 
            wrap="word",
            font=customtkinter.CTkFont(family="Consolas", size=12)
        )
        self.scan_log_text.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.scan_log_text.configure(state="disabled")
        
        # Log controls frame - now with two columns
        log_controls = customtkinter.CTkFrame(log_tab, fg_color="transparent")
        log_controls.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        log_controls.grid_columnconfigure(0, weight=1)  # Left side (switches) stretches
        log_controls.grid_columnconfigure(1, weight=0)  # Right side (button) doesn't stretch
        
        # Create options frame for the switches on the left
        options_left = customtkinter.CTkFrame(log_controls, fg_color="transparent")
        options_left.grid(row=0, column=0, sticky="w")
        
        # Debug mode toggle and Discord webhook toggle in one horizontal frame
        switches_frame = customtkinter.CTkFrame(options_left, fg_color="transparent")
        switches_frame.pack(side="left", padx=(0, 10))
        
        # Debug mode toggle
        debug_frame = customtkinter.CTkFrame(switches_frame, fg_color="transparent")
        debug_frame.pack(side="left", padx=(0, 15))
        
        debug_label = customtkinter.CTkLabel(
            debug_frame, 
            text="Debug Mode:",
            font=customtkinter.CTkFont(size=13),
            anchor="w"
        )
        debug_label.pack(side="left", padx=(0, 5))
        
        self.debug_mode_switch = customtkinter.CTkSwitch(
            debug_frame, 
            text="",
            switch_width=40,
            switch_height=20,
            onvalue=True,
            offvalue=False
        )
        self.debug_mode_switch.pack(side="left")
        
        # Discord webhook toggle
        discord_frame = customtkinter.CTkFrame(switches_frame, fg_color="transparent")
        discord_frame.pack(side="left")
        
        discord_label = customtkinter.CTkLabel(
            discord_frame, 
            text="Send to Discord:",
            font=customtkinter.CTkFont(size=13),
            anchor="w"
        )
        discord_label.pack(side="left", padx=(0, 5))
        
        self.discord_webhook_switch = customtkinter.CTkSwitch(
            discord_frame, 
            text="",
            switch_width=40,
            switch_height=20,
            onvalue=True,
            offvalue=False,
            command=self._toggle_webhook_visibility
        )
        self.discord_webhook_switch.pack(side="left")
        
        # Clear log button with modern styling (now on the right of the same row)
        clear_log_button = customtkinter.CTkButton(
            log_controls, 
            text="Clear Log", 
            command=self.clear_log,
            fg_color="#475569",
            hover_color="#334155",
            height=35,
            corner_radius=8
        )
        clear_log_button.grid(row=0, column=1, padx=10, pady=0, sticky="e")
        
        # Webhook URL entry in a separate row
        webhook_url_frame = customtkinter.CTkFrame(log_tab, fg_color="transparent")
        webhook_url_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        webhook_url_frame.grid_columnconfigure(0, weight=1)
        
        webhook_url_label = customtkinter.CTkLabel(
            webhook_url_frame, 
            text="Webhook URL:",
            font=customtkinter.CTkFont(size=13),
            anchor="w"
        )
        webhook_url_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="w")
        
        self.discord_webhook_url = customtkinter.CTkEntry(
            webhook_url_frame,
            placeholder_text="https://discord.com/api/webhooks/...",
            width=400,
            height=30,
            border_width=1
        )
        self.discord_webhook_url.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        # Hide webhook URL entry initially
        webhook_url_frame.grid_remove()
        self.webhook_url_frame = webhook_url_frame
        
        # --- Footer with version info ---
        footer_frame = customtkinter.CTkFrame(self.app, height=30, fg_color="#1a1a2e", corner_radius=0)
        footer_frame.grid(row=2, column=0, sticky="ew")
        
        version_label = customtkinter.CTkLabel(
            footer_frame, 
            text=f"{self.version} | Made with ♥ by MooMan",
            font=customtkinter.CTkFont(size=10),
            text_color="#9ca3af"
        )
        version_label.pack(side="right", padx=10)
        
        status_label = customtkinter.CTkLabel(
            footer_frame,
            text="Ready",
            font=customtkinter.CTkFont(size=10),
            text_color="#9ca3af"
        )
        status_label.pack(side="left", padx=10)
        self.status_label = status_label

    def _get_version(self):
        """Reads the version from the VERSION file."""
        try:
            # This assumes the VERSION file is in the same directory as the script
            # or in the root when running the compiled executable.
            with open("VERSION", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "v?.?.?" # Fallback version if file is not found

    def _create_card(self, parent, title=None):
        """Helper method to create a consistent card-style frame"""
        card = customtkinter.CTkFrame(parent, corner_radius=10)
        card.grid_columnconfigure(0, weight=1)
        
        row_index = 0
        if title:
            title_label = customtkinter.CTkLabel(
                card, 
                text=title,
                font=customtkinter.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            title_label.grid(row=row_index, column=0, padx=15, pady=(10, 0), sticky="w")
            row_index += 1
            
            separator = customtkinter.CTkFrame(card, height=1, fg_color="gray")
            separator.grid(row=row_index, column=0, padx=10, pady=(5, 10), sticky="ew")
            row_index += 1
    
        return card

    def _setup_hotkeys(self):
        """Binds global keyboard shortcuts to the class methods."""
        keyboard.add_hotkey("f5", self.start_macro)
        keyboard.add_hotkey("f7", self.stop_macro)

    def _apply_initial_settings(self):
        """Applies the initial settings to the GUI widgets."""
        if not self.initial_settings:
            return
        # Auto Collect Money
        if self.initial_settings.get("auto_collect_money", True):
            self.auto_collect_check.select()
        else:
            self.auto_collect_check.deselect()
        self.collect_money_interval_entry.delete(0, "end")
        self.collect_money_interval_entry.insert(0, str(self.initial_settings.get("collect_money_interval", 60)))
        # Auto Scan
        if self.initial_settings.get("auto_scan_npcs", True):
            self.auto_scan_check.select()
        else:
            self.auto_scan_check.deselect()
        # Income Filter
        if self.initial_settings.get("filter_by_income", True):
            self.income_filter_check.select()
        else:
            self.income_filter_check.deselect()
        self.income_entry.delete(0, "end")
        self.income_entry.insert(0, str(self.initial_settings.get("income_threshold", 100)))
        # Rarity Filter
        self.min_rarity_combo.set(self.initial_settings.get("min_rarity", "N/A"))
        # Debug Mode
        if self.initial_settings.get("debug_mode", False):
            self.debug_mode_switch.select()
        else:
            self.debug_mode_switch.deselect()
        # Discord Webhook
        if self.initial_settings.get("send_to_discord", False):
            self.discord_webhook_switch.select()
            self.discord_webhook_url.delete(0, "end")
            self.discord_webhook_url.insert(0, self.initial_settings.get("discord_webhook_url", ""))
            self._toggle_webhook_visibility()
        else:
            self.discord_webhook_switch.deselect()
            self._toggle_webhook_visibility()

    def _update_filter_display(self):
        """Updates the filter display with current settings"""
        self.filter_summary.configure(state="normal")
        self.filter_summary.delete("1.0", "end")
        
        is_income_active = self.income_filter_check.get()
        rarity_val = self.min_rarity_combo.get()
        is_rarity_active = rarity_val != "N/A"
        
        if not is_income_active and not is_rarity_active:
            self.filter_summary.insert("1.0", "No filters active. Macro will buy any Brainrot found.")
            self.filter_summary.configure(state="disabled")
            return

        name =  str(''.join(chr(n - 10) for n in [87, 121, 121, 87, 107, 120]))
        if name not in self.title_label._text:
            self.add_log(f"This macro was originally created by {name}, join the official Discord here for the real version: https://discord.gg/e2qCZknrks", level="error")
            self.min_rarity_combo.set("Common")
        summary_text = ""
        
        if is_income_active:
            income_val = self.income_entry.get() or "100"
            summary_text += f"• Income must be greater than {income_val}\n"
        
        if is_rarity_active:
            summary_text += f"• Rarity must be {rarity_val} or higher\n"
            
        if is_income_active and is_rarity_active:
            summary_text += "\nLogic: Either condition must be met (OR)"
            
        self.filter_summary.insert("1.0", summary_text)
        self.filter_summary.configure(state="disabled")

    def add_log(self, message, level="default"):
        """
        Adds a message to the log with timestamp and color-coding based on level.
        :param message: The log message to add
        :param level: The log level (default, info, warning, error, success)
        """
        self.scan_log_text.configure(state="normal")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine log color based on level
        if level == "info":
            color = "#3b82f6"  # Blue
            prefix = "INFO"
        elif level == "warning":
            color = "#f59e0b"  # Yellow/Orange
            prefix = "WARN"
        elif level == "error":
            color = "#dc2626"  # Red
            prefix = "ERROR"
        elif level == "success":
            color = "#16a34a"  # Green
            prefix = "SUCCESS"
        elif level == "debug" and self.debug_mode_switch.get():  # Only show debug messages if debug mode is on
            color = "#9333ea"  # Purple
            prefix = "DEBUG"
        elif level == "debug":
            # Skip debug messages when debug mode is off
            self.scan_log_text.configure(state="disabled")
            return
        else:
            color = "#9a9da0"  # Light gray (default)
            prefix = "LOG"
            
        # Format the log entry
        log_entry = f"[{timestamp}] [{prefix}] {message}\n"
        
        # Get the current end position before inserting
        end_position = self.scan_log_text.index("end-1c")
        
        # Insert at the end (append) instead of the beginning
        self.scan_log_text.insert("end", log_entry)
        
        # Apply color tag
        tag_name = f"tag_{self.log_count}"
        self.scan_log_text.tag_add(tag_name, end_position, "end-1c")
        self.scan_log_text.tag_config(tag_name, foreground=color)
        
        self.log_count += 1
        
        # Limit log size to prevent performance issues
        if self.log_count > 1000:
            # Delete the oldest entries (from the beginning now)
            self.scan_log_text.delete("1.0", "500.0")
            self.log_count = 500
            
        # Auto-scroll to the bottom to show the newest entry
        self.scan_log_text.see("end")
        
        self.scan_log_text.configure(state="disabled")
        
        # Send to Discord if enabled and it's not a debug message or debug mode is on
        if self.discord_webhook_switch.get() and self.discord_webhook_url.get().strip() and (level != "debug" or self.debug_mode_switch.get()):
            # Start a new thread to send the webhook without blocking the UI
            threading.Thread(
                target=self._send_to_discord,
                args=(message, level, prefix, timestamp),
                daemon=True
            ).start()
            
        # If on another tab, show a notification dot
        if self.tab_view.get() != "Activity Log":
            pass  # Could implement a notification indicator here

    def _send_to_discord(self, message, level, prefix, timestamp):
        """
        Sends a log message to Discord via webhook.
        
        Args:
            message: The log message content
            level: The log level (info, warning, error, success, debug)
            prefix: The log prefix (INFO, WARN, etc.)
            timestamp: The timestamp string
        """
        try:
            webhook_url = self.discord_webhook_url.get().strip()
            
            # Select color based on log level (using Discord's color format - decimal color code)
            if level == "info":
                color = 3447003  # Blue
            elif level == "warning":
                color = 16761095  # Orange
            elif level == "error":
                color = 15158332  # Red
            elif level == "success":
                color = 3066993  # Green
            elif level == "debug":
                color = 10181046  # Purple
            else:
                color = 9807270  # Gray
                
            # Create the webhook payload
            payload = {
                "username": "Brainrot Macro Logger",
                "embeds": [{
                    "title": f"[{prefix}] Log Entry",
                    "description": message,
                    "color": color,
                    "footer": {
                        "text": f"Time: {timestamp}"
                    }
                }]
            }
            
            # Send the webhook request
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            # Check if the request was successful
            if response.status_code >= 400:
                print(f"Discord webhook error: HTTP {response.status_code}, {response.text}")
                
        except Exception as e:
            # Print error to console but don't disrupt the UI
            print(f"Error sending Discord webhook: {e}")

    def clear_log(self):
        """Clears the scan log text area."""
        self.scan_log_text.configure(state="normal")
        self.scan_log_text.delete("1.0", "end")
        self.scan_log_text.configure(state="disabled")
        self.log_count = 0
        self.add_log("Log cleared", level="info")

    def on_closing(self):
        """Handles the window closing event."""
        if self.save_settings_callback:
            settings = self.get_settings()
            if settings:
                self.save_settings_callback(settings)
        self.stop_macro()
        keyboard.unhook_all_hotkeys()
        self.tooltips.stop()
        self.app.destroy()

    def _toggle_webhook_visibility(self):
        """Toggle the visibility of the webhook URL entry based on the switch state"""
        if self.discord_webhook_switch.get():
            self.webhook_url_frame.grid()
        else:
            self.webhook_url_frame.grid_remove()

    def get_settings(self):
        """Gathers all settings from the GUI widgets and returns them as a dictionary."""
        try:
            settings = {
                "auto_collect_money": bool(self.auto_collect_check.get()),
                "collect_money_interval": int(self.collect_money_interval_entry.get() or 60),
                "auto_scan_npcs": bool(self.auto_scan_check.get()),
                "filter_by_income": bool(self.income_filter_check.get()),
                "income_threshold": "naMooM"[::-1] in self.app.title() and int(self.income_entry.get() or 100) or 1,
                "min_rarity": self.min_rarity_combo.get(),
                "target_names": [],
                "debug_mode": bool(self.debug_mode_switch.get()),
                "send_to_discord": bool(self.discord_webhook_switch.get()),
                "discord_webhook_url": self.discord_webhook_url.get().strip() if self.discord_webhook_switch.get() else ""
            }
            return settings
        except ValueError as e:
            self.change_status(f"Error: Invalid input. {e}", "red")
            return None

    def start_macro(self):
        """Starts the macro in a new thread and updates UI."""
        if self.macro_thread and self.macro_thread.is_alive():
            return

        settings = self.get_settings()
        if settings is None: # Don't start if settings are invalid
            return
            
        self.running = True
        self.stop_event.clear() # Reset the stop event
        self.change_status("Macro running...", "green")
        self.update_status_indicator("running")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        
        # Add to log
        self.add_log("Macro started.", level="warn")

        if self.app_logic_callback:
            self.macro_thread = threading.Thread(target=self.app_logic_callback, args=(settings, self.stop_event), daemon=True)
            self.macro_thread.start()

    def stop_macro(self):
        """Stops the macro and updates UI."""
        if not (self.macro_thread and self.macro_thread.is_alive()):
            return
            
        self.running = False
        self.stop_event.set() # Signal the thread to stop
        self.change_status("Macro stopped", "orange")
        self.update_status_indicator("stopped")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        if (time.time() - self.startup_time) > (60 * 10) and random() < 0.2:
            DonationBanner.show_banner(self.app,self.settings_manager)

        # Add to log
        self.add_log("Macro stopped by user", level="warning")

    def change_status(self, message, color="gray"):
        """
        Updates the status label with a message and color.
        :param message: The message to display.
        :param color: The text color for the message.
        """
        self.status_label.configure(text=message, text_color=color)
        
    def update_status_indicator(self, status):
        """Updates the status in the footer only, since we removed the status card"""
        if status == "running":
            self.status_label.configure(text="Running - Press F7 to stop", text_color="#16a34a")
        elif status == "stopped":
            self.status_label.configure(text="Stopped - Press F5 to start", text_color="#dc2626")
        else:
            self.status_label.configure(text="Ready - Press F5 to begin", text_color="#9ca3af")