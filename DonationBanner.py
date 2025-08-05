import tkinter as tk
import webbrowser
from tkinter import font as tkfont

class DonationBanner:
    """A Wikipedia-style donation banner that appears when a macro is stopped."""
    
    def __init__(self, parent, settings_manager=None):
        self.parent = parent
        self.settings_manager = settings_manager
        
        # Create a new toplevel window instead of embedding in parent
        self.window = tk.Toplevel(parent)
        self.window.title("Support Steal-a-Brainrot Macro")
        self.window.configure(bg="#FFDD99")
        self.window.geometry("500x220")
        
        # Make window appear on top
        self.window.attributes('-topmost', True)
        
        # Center the window relative to parent
        if parent:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 110
            self.window.geometry(f"+{x}+{y}")
        
        # Banner title
        title_font = tkfont.Font(family="Arial", size=12, weight="bold")
        title = tk.Label(
            self.window, 
            text="⚠️ Support Steal-a-Brainrot Macro ⚠️", 
            bg="#FFDD99", 
            font=title_font
        )
        title.pack(pady=(10, 5))
        
        # Banner message
        message = tk.Label(
            self.window,
            text=("I'm just one developer working hard to add new features to and improve "
                  "this macro. If this macro has helped you, please show your support"
                  " with a donation. Your support directly funds new features and continued development!"),
            bg="#FFDD99",
            wraplength=450,
            justify="center"
        )
        message.pack(pady=(0, 10))
        
        # Donation buttons frame
        buttons_frame = tk.Frame(self.window, bg="#FFDD99")
        buttons_frame.pack(pady=(0, 5))
        
        # Donation buttons
        self.create_donation_button(
            buttons_frame, 
            "Small Donation", 
            "https://www.roblox.com/game-pass/1365523118/Steal-a-Brainrot-Macro-Donation-Small",
            0
        )
        
        self.create_donation_button(
            buttons_frame, 
            "Medium Donation", 
            "https://www.roblox.com/game-pass/1316222536/Steal-a-Brainrot-Macro-Donation-Medium",
            1
        )
        
        self.create_donation_button(
            buttons_frame, 
            "Large Donation", 
            "https://www.roblox.com/game-pass/1366939027/Steal-a-Brainrot-Macro-Donation-Large",
            2
        )
        
        # Buttons frame for the bottom row
        bottom_buttons_frame = tk.Frame(self.window, bg="#FFDD99")
        bottom_buttons_frame.pack(pady=(5, 0))
        
        # Close button
        close_button = tk.Button(
            bottom_buttons_frame, 
            text="Maybe later", 
            command=self.window.destroy,
            bg="#EEEEEE",
            width=10,
            font=("Arial", 8)
        )
        close_button.grid(row=0, column=0, padx=5)
        
        # "I'm poor" button
        poor_button = tk.Button(
            bottom_buttons_frame, 
            text="Already Donated", 
            command=self.mark_as_poor,
            bg="#EEEEEE",
            width=13,
            font=("Arial", 8)
        )
        poor_button.grid(row=0, column=1, padx=5)
    
    def create_donation_button(self, parent, text, url, column):
        button = tk.Button(
            parent,
            text=text,
            bg="#4CAF50",
            fg="white",
            padx=10,
            command=lambda u=url: webbrowser.open(u)
        )
        button.grid(row=0, column=column, padx=5)
    
    def mark_as_poor(self):
        """Mark the user as poor so they don't see donation banners anymore."""
        if self.settings_manager:
            # Get current settings
            settings = self.settings_manager.get_settings()
            # Update the im_poor setting
            settings["im_poor"] = True
            # Save the updated settings
            self.settings_manager.save(settings)
        
        # Close the window
        self.window.destroy()
    
    @classmethod
    def show_banner(cls, parent, settings_manager=None):
        """Create and display the donation banner if the user is not marked as poor."""
        # Check if user is marked as poor
        if settings_manager and settings_manager.get_settings().get('im_poor', False):
            return None  # Don't show banner
        
        # Show the banner
        banner = cls(parent, settings_manager)
        return banner