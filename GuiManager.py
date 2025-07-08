import queue
from time import sleep
import customtkinter
import threading
import keyboard
import webbrowser
import tkinter as tk
import pyautogui

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

        label = tk.Label(self.tooltip_window, text=text,
                         background=bg_color,
                         foreground=fg_color,
                         relief="solid", borderwidth=1,
                         font=("Arial", 9))
        label.pack(padx=5, pady=3)

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

    def show(self, text, duration_ms=2000, offset_x=20, offset_y=10, fg_color="black", bg_color="#FFFFCC"):
        """
        Public method to request a tooltip to be shown.
        This is thread-safe.
        """
        # Get mouse position at the time of the call
        mouse_x, mouse_y = pyautogui.position()
        x_pos = mouse_x + offset_x
        y_pos = mouse_y + offset_y

        # Put the command and its arguments onto the queue for the GUI thread to process
        args = (text, duration_ms, x_pos, y_pos, fg_color, bg_color)
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
    def __init__(self, app_logic_callback=None):
        """
        Initializes the GUI.
        :param app_logic_callback: A function to call when the start button is pressed.
                                   This function should accept two arguments:
                                   (1) a dictionary of settings, and (2) a threading.Event to signal stopping.
        """
        self.app_logic_callback = app_logic_callback
        self.macro_thread = None
        self.stop_event = threading.Event()

        # --- Main Application Window Setup ---
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")

        self.app = customtkinter.CTk()
        self.app.title("MooMan's Macro")
        self.app.geometry("500x520")

        self.app.grid_columnconfigure(0, weight=1)
        self.app.grid_rowconfigure(1, weight=1)

        self._create_widgets()
        self._setup_hotkeys()
        
        # Ensure the thread is stopped when the window is closed
        self.app.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.tooltips = Tooltip()
        self.event_manager = Events()
        self.event_manager.subscribe("status_change", self.change_status)
        self.event_manager.subscribe("tooltip", self.tooltips.show)  # Print debug messages to console

    def run(self):
        """Starts the customtkinter main loop."""
        self.app.mainloop()

    def open_link(self, url):
        """Opens a URL in the default web browser."""
        webbrowser.open_new(url)

    def _create_widgets(self):
        """Creates and places all the widgets in the window."""
        # --- Top Title ---
        title_frame = customtkinter.CTkFrame(self.app, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="ew")
        title_label = customtkinter.CTkLabel(title_frame, text="MooMan's Brainrot Macro", font=customtkinter.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=(10, 0))

        discord_link = "https://discord.gg/ur8an4mb"
        sub_label = customtkinter.CTkLabel(title_frame, text="Join our Discord community!", text_color="#60a5fa", cursor="hand2", font=customtkinter.CTkFont(underline=True))
        sub_label.pack(pady=(0, 10))
        sub_label.bind("<Button-1>", lambda e: self.open_link(discord_link))

        # --- Tabbed Interface for Settings ---
        tab_view = customtkinter.CTkTabview(self.app, segmented_button_selected_color="#2c74b3")
        tab_view.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        macro_tab = tab_view.add("⚙️ Macro Settings")
        npc_scan_tab = tab_view.add("🔎 NPC Scan Filters")
        macro_tab.grid_columnconfigure(0, weight=1)
        npc_scan_tab.grid_columnconfigure(1, weight=1)

        # --- Populate "Macro Settings" Tab ---
        # NOTE: All input widgets are now instance attributes (self.*)

        # -- Auto Collect Money Setting --
        collect_frame = customtkinter.CTkFrame(macro_tab, fg_color="transparent")
        collect_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        self.auto_collect_check = customtkinter.CTkCheckBox(collect_frame, text="Auto Collect Money every")
        self.auto_collect_check.pack(side="left", padx=(0, 5))
        self.auto_collect_check.select()

        self.collect_money_interval_entry = customtkinter.CTkEntry(collect_frame, placeholder_text="60", width=50)
        self.collect_money_interval_entry.pack(side="left", padx=5)
        
        collect_seconds_label = customtkinter.CTkLabel(collect_frame, text="seconds")
        collect_seconds_label.pack(side="left", padx=5)

        # -- Auto Scan for NPCs Setting --
        scan_frame = customtkinter.CTkFrame(macro_tab, fg_color="transparent")
        scan_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.auto_scan_check = customtkinter.CTkCheckBox(scan_frame, text="Auto Scan for NPCs")
        self.auto_scan_check.pack(side="left")
        self.auto_scan_check.select()


        # --- Populate "NPC Scan Filters" Tab ---
        self.income_filter_check = customtkinter.CTkCheckBox(npc_scan_tab, text="Only buy NPCs with income >")
        self.income_filter_check.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.income_entry = customtkinter.CTkEntry(npc_scan_tab, placeholder_text="100")
        self.income_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        min_rarity_label = customtkinter.CTkLabel(npc_scan_tab, text="Only buy with minimum rarity:")
        min_rarity_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.min_rarity_combo = customtkinter.CTkComboBox(npc_scan_tab, values=["Any", "Common", "Uncommon", "Rare", "Epic", "Legendary"])
        self.min_rarity_combo.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.min_rarity_combo.set("Any")

        target_names_label = customtkinter.CTkLabel(npc_scan_tab, text="🎯 Target specific names (comma-separated):")
        target_names_label.grid(row=3, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")
        self.target_names_textbox = customtkinter.CTkTextbox(npc_scan_tab, height=80)
        self.target_names_textbox.grid(row=4, column=0, columnspan=2, padx=10, pady=0, sticky="ew")
        self.target_names_textbox.insert("0.0", "Tim Cheese, Noobini Pizzanini")

        # --- Bottom Buttons and Status Label ---
        # NOTE: These are also instance attributes to be controlled by methods.
        bottom_frame = customtkinter.CTkFrame(self.app)
        bottom_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        bottom_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_button = customtkinter.CTkButton(bottom_frame, text="Start (F5)", command=self.start_macro, fg_color="#28a745", hover_color="#218838")
        self.start_button.grid(row=0, column=0, padx=(0, 5), pady=10, sticky="ew")

        self.stop_button = customtkinter.CTkButton(bottom_frame, text="Stop (F7)", command=self.stop_macro, fg_color="#dc3545", hover_color="#c82333")
        self.stop_button.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="ew")
        self.stop_button.configure(state="disabled")

        self.status_label = customtkinter.CTkLabel(self.app, text="Status: Idle", text_color="gray", anchor="w")
        self.status_label.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

    def _setup_hotkeys(self):
        """Binds global keyboard shortcuts to the class methods."""
        keyboard.add_hotkey("f5", self.start_macro)
        keyboard.add_hotkey("f7", self.stop_macro)

    def get_settings(self):
        """Gathers all settings from the GUI widgets and returns them as a dictionary."""
        try:
            settings = {
                "auto_collect_money": bool(self.auto_collect_check.get()),
                "collect_money_interval": int(self.collect_money_interval_entry.get() or 60),
                "auto_scan_npcs": bool(self.auto_scan_check.get()),
                "filter_by_income": bool(self.income_filter_check.get()),
                "income_threshold": int(self.income_entry.get() or 100),
                "min_rarity": self.min_rarity_combo.get(),
                "target_names": [name.strip() for name in self.target_names_textbox.get("0.0", "end-1c").split(',') if name.strip()]
            }
            return settings
        except ValueError as e:
            self.status_label.configure(text=f"Error: Invalid input. {e}", text_color="red")
            return None

    def start_macro(self):
        """Starts the macro in a new thread and updates UI."""
        if self.macro_thread and self.macro_thread.is_alive():
            return

        settings = self.get_settings()
        if settings is None: # Don't start if settings are invalid
            return
            
        print("Macro Started! (F5)")
        self.stop_event.clear() # Reset the stop event
        self.status_label.configure(text="Status: Running...", text_color="green")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        if self.app_logic_callback:
            self.macro_thread = threading.Thread(target=self.app_logic_callback, args=(settings, self.stop_event), daemon=True)
            self.macro_thread.start()

    def stop_macro(self):
        """Stops the macro and updates UI."""
        if not (self.macro_thread and self.macro_thread.is_alive()):
            return
            
        print("Macro Stopped! (F7)")
        self.stop_event.set() # Signal the thread to stop
        self.status_label.configure(text="Status: Stopped", text_color="orange")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
    
    def change_status(self, message, color="gray"):
        """
        Updates the status label with a message and color.
        :param message: The message to display.
        :param color: The text color for the message.
        """
        print(message)
        self.status_label.configure(text=message, text_color=color)

    def on_closing(self):
        """Handles the window closing event."""
        self.stop_macro()
        keyboard.unhook_all_hotkeys()
        self.app.destroy()