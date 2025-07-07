import threading
from WindowManager import WindowManager
from InputManager import InputManager
from GameActions import GameActions
from GuiManager import GuiManager # Import the new class
from time import sleep

from ActionQueue import ActionQueue

def main_bot_logic(settings, stop_event):
    """The main logic for the bot, to be run in a thread."""
    window_manager = WindowManager()
    if not window_manager.setup_window():
        print("Exiting: Could not set up game window.")
        return

    input_manager = InputManager(window_manager.hwnd)
    action_queue = ActionQueue()
    game_actions = GameActions(window_manager, input_manager, stop_event, action_queue)

    def run_task_in_loop(interval_seconds, task_func):
        """
        Runs a task function in an infinite loop, sleeping for the interval.
        This function is meant to be the `target` of a `threading.Thread`.
        """
        while True:
            task_func()
            sleep(interval_seconds)
        
    def addLoopToQueue(func, interval):
        thread = threading.Thread(
            target=run_task_in_loop,
            args=(interval, lambda: action_queue.add(func)),
            daemon=True,
        )
        thread.start()

    game_actions.align_camera()
    addLoopToQueue(game_actions.collect_money, 60)
    addLoopToQueue(game_actions.lock_base, 60)
    addLoopToQueue(game_actions.scan_npcs, 60)
    print("Starting bot actions in 1 second...")
    sleep(1)
    # Example of using settings
    print(f"Settings received: {settings}")
    
    # Example of checking the stop event in a loop
    while not stop_event.is_set():
        print("Bot is running...")
        # Check for stop signal periodically
        if stop_event.wait(timeout=1): # wait for 1s, or until event is set
            break
    
    print("Bot actions finished or stopped.")


if __name__ == "__main__":
    gui = GuiManager(app_logic_callback=main_bot_logic)
    gui.run()