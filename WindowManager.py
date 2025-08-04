import json
import sys
from time import sleep
import win32gui
import win32con
from PIL import ImageGrab
import numpy as np
from screen_ocr import Reader
from Events import Events
from pathlib import Path

class WindowManager:
    def __init__(self, config_path='data/config.json'):
        """
        :param config_path: Optional override (relative to this file) for the JSON config.
                            Defaults to 'data/config.json' next to WindowManager.py.
        """
        # 1) Determine base directory (where this file lives)
        base_dir = Path(__file__).parent
        # 2) Resolve config file path
        cfg_file = base_dir / config_path

        # 3) Create parent dirs and a default empty config if missing
        if not cfg_file.exists():
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text("{}", encoding="utf-8")

        # 4) Load the JSON config
        self.config = self._load_config(cfg_file)

        # Rest of initialization
        self.os_name    = sys.platform
        self.hwnd       = None
        self.ocr_reader = Reader.create_quality_reader()
        self.debug      = Events().debug  # for debug logging

    def _load_config(self, path: Path):
        """Load JSON config from the given pathlib.Path, raising on invalid JSON."""
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in config at {path}: {e}")

    def setup_window(self):
        """Find, activate, and standardize the target window via Win32 API."""
        def enum_cb(hwnd, results):
            title = win32gui.GetWindowText(hwnd)
            if win32gui.IsWindowVisible(hwnd) and title == self.config.get("window_title"):
                results.append(hwnd)

        windows = []
        win32gui.EnumWindows(enum_cb, windows)

        if not windows:
            self.debug(f"Error: '{self.config.get('window_title')}' window not found.")
            return False

        self.hwnd = windows[0]
        try:
            # Bring to front & maximize
            win32gui.SetForegroundWindow(self.hwnd)
            sleep(0.3)
            win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)
            sleep(0.3)

            # Move to (0,0)
            win32gui.SetWindowPos(
                self.hwnd, 0, 0, 0, 0, 0,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER
            )
            sleep(0.3)

            # Resize to standard dimensions
            win32gui.SetWindowPos(
                self.hwnd, 0, 0, 0,
                self.config["standard_width"],
                self.config["standard_height"],
                win32con.SWP_NOMOVE | win32con.SWP_NOZORDER
            )
            sleep(0.5)

            self.debug("Window setup complete!")
            return True

        except Exception as e:
            self.debug(f"Error standardizing window: {e}")
            return False

    def get_center_coordinates(self):
        """Return the center of the client area in screen coordinates."""
        if not self.hwnd:
            self.debug("Error: Call setup_window() first.")
            return None

        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        cx = (right - left) // 2
        cy = (bottom - top) // 2
        return win32gui.ClientToScreen(self.hwnd, (cx, cy))

    def get_words_in_bounding_box(self, bounding_box):
        """
        OCR on a client-area box.
        Returns a list of (text, (x,y)) and the full OCR result object.
        """
        sl, st = win32gui.ClientToScreen(self.hwnd, (bounding_box[0], bounding_box[1]))
        sr, sb = win32gui.ClientToScreen(self.hwnd, (bounding_box[2], bounding_box[3]))
        result = self.ocr_reader.read_screen((sl, st, sr, sb))

        output = []
        for line in result.result.lines:
            if not line.words:
                continue
            text = " ".join(w.text for w in line.words).strip().lower()
            fw, lw = line.words[0], line.words[-1]
            mid_x = int((fw.left + (lw.left + lw.width)) / 2)
            mid_y = int(fw.top + fw.height / 2)
            output.append((text, (mid_x, mid_y)))

        return output, result

    def save_screenshot(self, filename, bounding_box=None):
        """Save a screenshot of the client area (or a sub-region) to disk."""
        if not self.hwnd:
            self.debug("Error: Call setup_window() first.")
            return

        if bounding_box is None:
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
            sl, st = win32gui.ClientToScreen(self.hwnd, (left, top))
            sr, sb = win32gui.ClientToScreen(self.hwnd, (right, bottom))
            bounding_box = (sl, st, sr, sb)

        img = ImageGrab.grab(bbox=bounding_box)
        img.save(filename)
        self.debug(f"Screenshot saved as {filename}")

    def find_color(self, hex_color, threshold=10):
        """
        Find the first pixel matching hex_color ± threshold.
        Returns client-area (x, y) or None.
        """
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        sl, st = win32gui.ClientToScreen(self.hwnd, (left, top))
        sr, sb = win32gui.ClientToScreen(self.hwnd, (right, bottom))
        arr = np.array(ImageGrab.grab(bbox=(sl, st, sr, sb)))

        target = np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])
        dist = np.sum(np.abs(arr - target), axis=2)
        ys, xs = np.where(dist <= threshold)
        if ys.size:
            return int(xs[0]), int(ys[0])
        return None

    def get_color_at_pixel(self, x, y):
        """Get the RGB tuple at a given client-area pixel."""
        if not self.hwnd:
            self.debug("Error: Call setup_window() first.")
            return None

        sx, sy = win32gui.ClientToScreen(self.hwnd, (x, y))
        pix = ImageGrab.grab(bbox=(sx, sy, sx+1, sy+1)).getpixel((0, 0))
        if isinstance(pix, tuple):
            return pix[:3] if len(pix) >= 3 else (pix[0], pix[0], pix[0])
        return (pix, pix, pix)
