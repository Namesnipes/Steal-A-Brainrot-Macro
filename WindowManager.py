import json
import sys
from time import sleep
import win32gui
import win32con
from PIL import ImageGrab
import numpy as np
from screen_ocr import Reader


class WindowManager:
    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        self.os_name = sys.platform

        self.hwnd = None  # Window handle
        self.ocr_reader = Reader.create_quality_reader()

    def _load_config(self, path):
        """Loads the JSON configuration file."""
        with open(path, 'r') as f:
            return json.load(f)

    def setup_window(self):
        """Finds, activates, and standardizes the target window using Windows API."""
        
        def enum_windows_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == self.config['window_title']:
                results.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if not windows:
            print(f"Error: {self.config['window_title']} window not found.")
            return False
        
        # Use the first window found
        self.hwnd = windows[0]
        
        try:
            # Activate window
            win32gui.SetForegroundWindow(self.hwnd)
            sleep(0.3)
            
            # Maximize window
            win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)
            sleep(0.3)
            
            # Move to position (0, 0)
            win32gui.SetWindowPos(self.hwnd, 0, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            sleep(0.3)
            
            # Resize window
            win32gui.SetWindowPos(self.hwnd, 0, 0, 0, 
                                self.config['standard_width'], 
                                self.config['standard_height'], 
                                win32con.SWP_NOMOVE | win32con.SWP_NOZORDER)
            sleep(0.5)
            
            print("Window setup complete!")
            return True

        except Exception as e:
            print(f"Error standardizing window: {e}")
            return False

    def get_center_coordinates(self):
        """Returns the center coordinates of the current window's client area."""
        if not self.hwnd:
            print("Error: Window not set up. Call setup_window() first.")
            return None
        
        # Get client area coordinates (handles window decorations automatically)
        client_rect = win32gui.GetClientRect(self.hwnd)
        left, top, right, bottom = client_rect
        
        center_x = (right - left) // 2
        center_y = (bottom - top) // 2
        
        # Convert to screen coordinates
        client_to_screen = win32gui.ClientToScreen(self.hwnd, (center_x, center_y))
        return client_to_screen

    def get_words_in_bounding_box(self, bounding_box):
        """
        Performs OCR on a screen region and returns a list of lowercase text lines.
        
        Args:
            bounding_box: A tuple (left, top, right, bottom) defining the area.
            ocr_reader: An initialized screen_ocr.Reader instance.

        Returns:
            A list of tuples, where each tuple contains:
            - A lowercase string of the detected line of text.
            - A tuple (x, y) for the line's center coordinates.
        """
        #convert make bounding_box screen coordinates
        screen_left, screen_top = win32gui.ClientToScreen(self.hwnd, (bounding_box[0], bounding_box[1]))
        screen_right, screen_bottom = win32gui.ClientToScreen(self.hwnd, (bounding_box[2], bounding_box[3]))

        result = self.ocr_reader.read_screen((screen_left, screen_top, screen_right, screen_bottom))

        output = []
        for line in result.result.lines:
            if not line.words:
                continue
                
            line_text = "".join(word.text + " " for word in line.words).strip().lower()
            
            first_word = line.words[0]
            last_word = line.words[-1]
            
            mid_y = int(first_word.top + (first_word.height / 2))
            mid_x = int((first_word.left + (last_word.left + last_word.width)) / 2)
            
            output.append((line_text, (mid_x, mid_y)))
            
        return output

    def save_screenshot(self, filename, bounding_box=None):
        """
        Saves a screenshot of the current window or a specified bounding box.

        :param filename: The name of the file to save the screenshot.
        :param bounding_box: Optional tuple (left, top, right, bottom) for a specific area.
                            If None, captures the entire client area.
        """
        if not self.hwnd:
            print("Error: Window not set up. Call setup_window() first.")
            return
        
        if bounding_box is None:
            # Get client area coordinates
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
            screen_left, screen_top = win32gui.ClientToScreen(self.hwnd, (left, top))
            screen_right, screen_bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))
            bounding_box = (screen_left, screen_top, screen_right, screen_bottom)

        screenshot = ImageGrab.grab(bbox=bounding_box)
        screenshot.save(filename)
        print(f"Screenshot saved as {filename}")
        
    def find_color(self, hex_color, threshold=10):
        """
        Finds the first occurrence of a color in the window's client area.

        :param hex_color: The hex color string (e.g., "D83228").
        :param threshold: The tolerance for color matching (0-255).
        :return: A tuple (x, y) of the client coordinates, or None if not found.
        """
        # 1. Get window client area and take a screenshot
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        
        # Adjust to screen coordinates for the screenshot
        screen_left, screen_top = win32gui.ClientToScreen(self.hwnd, (left, top))
        screen_right, screen_bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))

        screenshot = ImageGrab.grab(bbox=(screen_left, screen_top, screen_right, screen_bottom))
        img_np = np.array(screenshot)

        # 2. Convert hex to RGB
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        target_color = np.array([r, g, b])

        # 3. Find pixels within the threshold
        diff = np.abs(img_np - target_color)
        distance = np.sum(diff, axis=2)
        matching_pixels = np.where(distance <= threshold)

        # 4. Return the first match's client coordinates
        if matching_pixels[0].size > 0:
            # These are relative to the screenshot, which is the client area
            y, x = matching_pixels[0][0], matching_pixels[1][0]
            return int(x), int(y)

        return None