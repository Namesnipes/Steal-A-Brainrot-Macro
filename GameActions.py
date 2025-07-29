import re
from time import sleep
from Events import Events
from Helper import human_readable_to_long
import time
import random

class GameActions:
    def __init__(self, window_manager, input_manager, stop_event, action_queue):
        self.window_manager = window_manager
        self.input_manager = input_manager
        self.stop_event = stop_event
        self.plot_side_right = None  # Will be set based on camera alignment
        self.action_queue = action_queue
        self.status_update = Events().change_status
        self.tooltip = Events().tooltip
        self.debug = Events().debug
        self.log = Events().log
        self.success = Events().success
        self.ALL_RARITIES = [
        "common", "rare", "epic", "legendary", 
        "mythic", "brainrot", "secret"
    ]
        

    def safe_sleep(self, duration):
        """
        Sleeps for the specified duration, ensuring the window is still active.
        """
        if self.stop_event.is_set():
            raise Exception("Bot stopped by user.")
        sleep(duration)
        if self.stop_event.is_set():
            raise Exception("Bot stopped by user.")

    def reset_bot(self, no_drag=False):
        self.status_update("Resetting character...")
        self.input_manager.key_press('esc')
        self.safe_sleep(0.3)
        self.input_manager.key_press('r')
        self.safe_sleep(0.3)
        self.input_manager.key_press('enter')
        self.safe_sleep(5)
        # if is red
        r, g, b = self.window_manager.get_color_at_pixel(70, 397)
        r2, g2, b2 = self.window_manager.get_color_at_pixel(730, 400) 
        if not no_drag:
            self.input_manager.drag_mouse(100, 100, 100, 500, button='right')
        self.safe_sleep(0.5)
        self.debug(f"red1: ({r}) red2: ({r2})")
        if not (r > 120) and not (r2 > 120) and self.plot_side_right is not None:
            self.input_manager.key_press(self.plot_side_right and 'left' or 'right', duration=0.75)


    def align_camera(self):
        """
        Drag right click down then use OCR to find whether "Cash Multi" is on right or left side of the screen.
        """
        x, y = self.window_manager.get_center_coordinates()
        self.input_manager.click(x, y)
        self.safe_sleep(0.5)
        self.status_update("Aligning camera...")
        self.input_manager.scroll(clicks=1000)
        self.safe_sleep(0.5)
        self.input_manager.scroll(clicks=-9, interval=0.1)
        self.safe_sleep(0.5)
        self.reset_bot(no_drag=True)
        self.safe_sleep(0.5)
        # find if the word "CASH" is on the right or left side of the screen
        def ocr_multi():
            bounding_box = (55, 188, 731, 380)
            ocr_results, obj = self.window_manager.get_words_in_bounding_box(bounding_box)
            self.debug(f"OCR Results: {ocr_results}")
            cash_words = [[word,coords] for word, coords in ocr_results if 'cash' in word.lower() or 'collect' in word.lower()]
            if len(cash_words) > 0:
                cash_x, _ = cash_words[0][1]
                self.debug(f"Cash X Coordinate: {cash_x}")
                if cash_x > self.window_manager.get_center_coordinates()[0]:
                    self.plot_side_right = True
                    self.debug("Cash Multi is on the right side.")
                    return True
                else:
                    self.plot_side_right = False
                    self.debug("Cash Multi is on the left side.")
                    return True
            else:
                self.debug(f"Cash Multi not found in OCR results. Results: {ocr_results}")
                #self.window_manager.save_screenshot("debug_cash_multi_not_found.png", bounding_box)

        for i in range(5):
            if ocr_multi():
                break
            self.safe_sleep(0.1)

        self.input_manager.drag_mouse(100, 100, 100, 500, button='right')
        self.safe_sleep(0.5)
        return

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

    def scan_npcs(self, min_rarity=None, min_income=100, stop_time=None):
        """
        Scan for NPCs and accept them based on rarity and income.

        Args:
            rarities (list, optional): A list of desired rarities (e.g., ["Legendary", "Brainrot God"]).
                                    If None or empty, any rarity is accepted. Defaults to None.
            min_income (int, optional): The minimum income to accept. Defaults to 100.
            stop_time (int, optional): Time in seconds to run the scan for. Defaults to None.
        """
        if not min_rarity or min_rarity == "N/A":
            target_rarities = None
        else:
            try:
                # Find the index of the minimum rarity (case-insensitive).
                lower_all_rarities = [r.lower() for r in self.ALL_RARITIES]
                min_rarity = min_rarity.lower().replace(" god", "")
                start_index = lower_all_rarities.index(min_rarity.lower())
                
                # Create a list of accepted rarities from the minimum index onwards.
                accepted_rarity_list = self.ALL_RARITIES[start_index:]
                
                # Convert to a set for efficient lookups.
                target_rarities = set(accepted_rarity_list)
                self.debug(f"Scanning for rarities: {', '.join(accepted_rarity_list)}")
            except ValueError:
                # Handle cases where the provided min_rarity is not valid.
                self.debug(f"Warning: Minimum rarity '{min_rarity}' is not valid. Defaulting to accept all rarities.")
                target_rarities = None

        start_time = time.time()
        self.reset_bot()
        self.status_update("Scanning NPCs...")
        hold_time = 1.7
        if self.plot_side_right:
            self.input_manager.key_press('a', duration=hold_time)
        else:
            self.input_manager.key_press('d', duration=hold_time)

        self.input_manager.move_mouse(13, 65)
        self.safe_sleep(0.5)
        last_mouse_move_time = time.time()

        while True:
            # Periodically move the mouse to prevent being idle
            if time.time() - last_mouse_move_time >= 60:
                x_coord = random.randint(12, 13)  # Random number between 12 and 13
                self.input_manager.click(x_coord, 65)
                last_mouse_move_time = time.time()

            if stop_time is not None and time.time() - start_time >= stop_time:
                self.debug(f"Scan stopped after {stop_time} seconds")
                break

            bounding_box = (148, 95, 610, 514)
            ocr_results_raw, result_object = self.window_manager.get_words_in_bounding_box(bounding_box)
            
            # --- Initialize variables for this scan ---
            found_income = None
            income_str = "N/A"
            found_rarity = None

            ## CHANGED ## Process OCR results word-by-word.
            for word, _ in ocr_results_raw:
                # Check 1: Is this word an income string?
                income_match = re.search(r"\$(.+)/s", word)
                if income_match:
                    try:
                        income_str = income_match.group(1)
                        found_income = human_readable_to_long(income_str)
                    except (ValueError, TypeError) as e:
                        self.debug(f"Invalid income number '{income_str}': {e}")
                    continue # Word processed, move to the next one

                # Check 2: Is this word a known rarity keyword?
                # Using .lower() for case-insensitive matching.
                for rarity in self.ALL_RARITIES:
                    if result_object.find_matching_words(rarity):
                        found_rarity = rarity
                        break

            # --- Decision Logic ---
            # Condition 1: Is the income high enough?
            income_ok = found_income is not None and found_income >= min_income
            # Condition 2: Is the rarity one we're looking for?
            rarity_ok = target_rarities is not None and (found_rarity and found_rarity in target_rarities)

            # false positives
            if found_income is not None and found_income > 1000 and found_rarity in ["common", "rare", "epic"]:
                income_ok = False 
                rarity_ok = False 
            if found_income is not None and found_income > 10000 and found_rarity in ["legendary"]:
                income_ok = False 
                rarity_ok = False  

            if not found_rarity and ocr_results_raw:
                self.debug(f"Unknown rarity found in OCR results: {ocr_results_raw}")

            if income_ok or rarity_ok:
                tooltip_text = f"FOUND!\nRarity: {found_rarity.title() if found_rarity is not None else '???'}\nIncome: ${income_str}/s"
                self.tooltip(tooltip_text, color="green")
                self.success(f"Match found! Rarity: {found_rarity}, Income: {found_income}.")
                self.input_manager.key_press('e', duration=0.5)
            else:
                rarity_display = found_rarity.title() if found_rarity else "???"
                income_display = f"${income_str}/s" if found_income is not None else "???"
                tooltip_text = f"Rarity: {rarity_display}\nIncome: {income_display}"
                self.tooltip(tooltip_text, color="red")
                if ocr_results_raw:
                    self.debug(f"Skipping. Rarity:'{found_rarity}' (Match:{rarity_ok}) | Income:{found_income} (Match:{income_ok})")

            if self.action_queue.get_queue_size() > 0:
                raise Exception("Action queue is not empty, stopping scan.")

            self.safe_sleep(0.2)
