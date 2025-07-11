from WindowManager import WindowManager
from InputManager import InputManager
from GameActions import GameActions
from GuiManager import GuiManager # Import the new class
from time import sleep

from ActionQueue import ActionQueue
from Events import Events

def main_bot_logic(settings, stop_event):
    """The main logic for the bot, to be run in a thread."""
    # --- Initialization ---
    log = Events().change_status
    logdb = Events().debug

    log("Initializing bot components...")
    window_manager = WindowManager()
    if not window_manager.setup_window():
        log("Exiting: Could not set up game window.", "red")
        return

    input_manager = InputManager(window_manager.hwnd)
    action_queue = ActionQueue()
    game_actions = GameActions(window_manager, input_manager, stop_event, action_queue)

    # --- Preparation ---
    log("Preparing game window...")
    while True:
        game_actions.align_camera()
        game_actions.collect_money()
    log("Starting bot actions in 1 second...")
    sleep(1)

    logdb(f"Settings received: {settings}")
    log("Bot is running. Press F7 to stop.", "green")

    # --- Main Loop ---
    while not stop_event.is_set():
        # The bot alternates between collecting money and scanning for Brainrots.
        # The duration of the scan is determined by the money collection interval.

        # 1. Handle Money Collection
        if settings.get("auto_collect_money"):
            game_actions.collect_money()

        if stop_event.is_set(): break

        # 2. Handle Brainrot Scanning
        if settings.get("auto_scan_npcs"):
            scan_duration = settings.get("collect_money_interval") if settings.get("auto_collect_money") else None
            
            game_actions.scan_npcs(
                min_income=settings.get("income_threshold"),
                min_rarity=settings.get("min_rarity"),
                stop_time=scan_duration
            )

        # If no actions are enabled, wait before checking again to avoid a busy loop.
        if not settings.get("auto_collect_money") and not settings.get("auto_scan_npcs"):
            if stop_event.wait(timeout=1):
                break
    
    log("Bot actions finished or stopped.", "orange")


if __name__ == "__main__":
    gui = GuiManager(app_logic_callback=main_bot_logic)
    gui.run()