from WindowManager import WindowManager
from InputManager import InputManager
from GameActions import GameActions
from GuiManager import GuiManager # Import the new class
from time import sleep

from ActionQueue import ActionQueue
from Events import Events

def main_bot_logic(settings, stop_event):
    """The main logic for the bot, to be run in a thread."""
    window_manager = WindowManager()
    if not window_manager.setup_window():
        print("Exiting: Could not set up game window.")
        return

    input_manager = InputManager(window_manager.hwnd)
    action_queue = ActionQueue()
    game_actions = GameActions(window_manager, input_manager, stop_event, action_queue)

    log = Events().change_status
    logdb = Events().debug
    game_actions.align_camera()
    log("Starting bot actions in 1 second...")
    sleep(1)

    logdb(f"Settings received: {settings}")
    
    while not stop_event.is_set():
        # --- Handle Money Collection ---
        if settings.get("auto_collect_money"):
                game_actions.collect_money()

        # --- Handle NPC Scanning ---
        if settings.get("auto_scan_npcs"):
            game_actions.scan_npcs(min_income=settings.get("income_threshold", 100), stop_time=settings.get("collect_money_interval", 60))

        # Wait for a short duration to prevent a busy loop, checking for the stop event
        if stop_event.wait(timeout=1):
            break
    
    print("Bot actions finished or stopped.")


if __name__ == "__main__":
    gui = GuiManager(app_logic_callback=main_bot_logic)
    gui.run()