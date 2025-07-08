import re
from time import sleep
from Events import Events
from Helper import human_readable_to_long
import time

class GameActions:
    def __init__(self, window_manager, input_manager, stop_event, action_queue):
        self.window_manager = window_manager
        self.input_manager = input_manager
        self.stop_event = stop_event
        self.plot_side_right = None  # Will be set based on camera alignment
        self.action_queue = action_queue
        self.status_update = Events().change_status
        self.tooltip = Events().tooltip

    def safe_sleep(self, duration):
        """
        Sleeps for the specified duration, ensuring the window is still active.
        """
        if self.stop_event.is_set():
            raise Exception("Bot stopped by user.")
        sleep(duration)

    def reset_bot(self, no_drag=False):
        self.status_update("Resetting character...")
        self.input_manager.key_press('esc')
        self.safe_sleep(0.3)
        self.input_manager.key_press('r')
        self.safe_sleep(0.3)
        self.input_manager.key_press('enter')
        self.safe_sleep(5)
        # Drag right click down
        if not no_drag:
            self.input_manager.drag_mouse(100, 100, 100, 500, button='right')
        self.safe_sleep(0.5)

    def align_camera(self):
        """
        Drag right click down then use OCR to find whether "Cash Multi" is on right or left side of the screen.
        """
        self.reset_bot(no_drag=True)
        self.status_update("Aligning camera...")
        # find if the word "CASH" is on the right or left side of the screen
        bounding_box = (114, 91, 772, 513)
        ocr_results = self.window_manager.get_words_in_bounding_box(bounding_box)
        print(f"OCR Results: {ocr_results}")
        cash_words = [[word,coords] for word, coords in ocr_results if 'cash' in word.lower() or 'collect' in word.lower()]
        if len(cash_words) > 0:
            cash_x, _ = cash_words[0][1]
            print(self.window_manager.get_center_coordinates()[0])
            print(f"Cash Multi found at x-coordinate: {cash_x}")
            if cash_x > self.window_manager.get_center_coordinates()[0]:
                self.plot_side_right = True
                print("Cash Multi is on the right side.")
            else:
                self.plot_side_right = False
                print("Cash Multi is on the left side.")
        else:
            print(f"Cash Multi not found in OCR results. Results: {ocr_results}")
            self.window_manager.save_screenshot("debug_cash_multi_not_found.png", bounding_box)
            return
        self.input_manager.drag_mouse(100, 100, 100, 500, button='right')

    def lock_base(self):
        """
        Lock the base
        """
        self.reset_bot()
        self.status_update("Collecting money...")
        hold_time = 1.8
        if self.plot_side_right:
            self.input_manager.key_press('d', duration=hold_time)
        else:
            self.input_manager.key_press('a', duration=hold_time)
    
    def collect_money(self):
        """
        Collect money by pressing 'e' and then 'enter'.
        """
        self.reset_bot()
        self.status_update("Collecting money...")
        first_to_last_time = 1
        self.input_manager.key_press(self.plot_side_right and 'd' or 'a', duration=0.55)
        self.safe_sleep(0.5)
        self.input_manager.key_press('w', duration=0.4)
        self.safe_sleep(0.4)
        self.input_manager.key_press(self.plot_side_right and 'd' or 'a', duration=first_to_last_time)
        self.safe_sleep(0.5)
        self.input_manager.key_press('s', duration=0.7)
        self.safe_sleep(0.5)
        self.input_manager.key_press(self.plot_side_right and 'a' or 'd', duration=first_to_last_time)
        self.safe_sleep(0.5)

    def scan_npcs(self, rarities=[], min_income=100, stop_time=None):
        """
        Scan for NPCs with the given target names.
        
        Args:
            target_names (list): List of target names to scan for.
            hold_time (float): Time to hold the key for scanning.
            accuracy (float): Accuracy threshold for OCR.
        """
        start_time = time.time()
        self.reset_bot()
        self.status_update("Scanning NPCs...")
        hold_time = 1.7
        if self.plot_side_right:
            self.input_manager.key_press('a', duration=hold_time)
        else:
            self.input_manager.key_press('d', duration=hold_time)
        
        #run ocr in loop with window manager
        while True:
            # Check if stop_time has been reached
            if stop_time is not None and time.time() - start_time >= stop_time:
                print(f"Scan stopped after {stop_time} seconds")
                break
                
            bounding_box = (148, 109, 610, 514)
            ocr_results1 = self.window_manager.get_words_in_bounding_box(bounding_box)
            # check for words in the format $<number>/ with regex
            pattern = r"\$(.+)/s"
            ocr_results = [match_obj for word, _ in ocr_results1 if (match_obj := re.search(pattern, word))]
            print(f"OCR Results: {ocr_results}")
            if len(ocr_results) == 1 and ocr_results[0]:
                try:
                    income = human_readable_to_long(ocr_results[0].group(1))
                    self.tooltip(f"${income}/s")
                    if income >= min_income:
                        print(f"Found NPC with income: {income}")
                        self.input_manager.key_press('e', duration=0.5)
                except (ValueError, TypeError) as e:
                    print(f"Invalid number '{ocr_results[0].group(1)}': {e}")
            if self.action_queue.get_queue_size() > 0:
                raise Exception("Action queue is not empty, stopping scan.")
            self.safe_sleep(0.2)
