import pydirectinput as pdi
from time import sleep
import win32gui

class InputManager:
    def __init__(self, hwnd):
        """
        Initializes the InputManager.
        :param hwnd: The handle to the target window.
        """
        self.hwnd = hwnd

    def _client_to_screen(self, x, y):
        """Converts client coordinates to screen coordinates."""
        return win32gui.ClientToScreen(self.hwnd, (x, y))

    def click(self, x, y, button='left'):
        """
        Moves the mouse to the specified client coordinates and clicks.
        :param x: The x-coordinate relative to the window's client area.
        :param y: The y-coordinate relative to the window's client area.
        :param button: 'left' or 'right' mouse button.
        """
        screen_x, screen_y = self._client_to_screen(x, y)
        pdi.moveTo(screen_x, screen_y)
        sleep(0.1)
        pdi.click(button=button)
    
    def move_mouse(self, x, y):
        """
        Moves the mouse to the specified client coordinates.
        :param x: The x-coordinate relative to the window's client area.
        :param y: The y-coordinate relative to the window's client area.
        """
        screen_x, screen_y = self._client_to_screen(x, y)
        pdi.moveTo(screen_x, screen_y)
    
    def drag_mouse(self, start_x, start_y, end_x, end_y, button='left'):
        """
        Drags the mouse from start to end client coordinates.
        :param start_x: The starting x-coordinate (client).
        :param start_y: The starting y-coordinate (client).
        :param end_x: The ending x-coordinate (client).
        :param end_y: The ending y-coordinate (client).
        :param button: 'left' or 'right' mouse button.
        """
        screen_start_x, screen_start_y = self._client_to_screen(start_x, start_y)
        screen_end_x, screen_end_y = self._client_to_screen(end_x, end_y)
        
        pdi.moveTo(screen_start_x, screen_start_y)
        sleep(0.1)
        pdi.dragTo(screen_end_x, screen_end_y, duration=0.5, button=button)
    
    def scroll(self, *args, **kwargs):
        """
        Scrolls the mouse wheel.
        :param args: Arguments for pydirectinput.scroll.
        :param kwargs: Keyword arguments for pydirectinput.scroll.
        """
        pdi.scroll(*args, **kwargs)

    def key_press(self, *args, **kwargs):
        """
        Sends a key press. This is not coordinate-dependent.
        :param key: The key to press (e.g., 'w').
        """
        pdi.press(*args, **kwargs)