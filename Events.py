class Events:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Events, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_subscribers'):
            self._subscribers = {}

    def subscribe(self, event_name, callback):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def emit(self, event_name, *args, **kwargs):
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                callback(*args, **kwargs)
    
    def change_status(self, message, color="gray"):
        self.emit("status_change", message, color)
    
    def tooltip(self, message, color="red"):
        """
        Emits a tooltip event with the given message.
        This is used to show tooltips in the GUI.
        """
        self.emit("tooltip", message, color=color)
    
    def debug(self, message):
        self.emit("debug", message)
    
    def log(self, message):
        self.emit("log", message)

    def success(self, message):
        self.emit("success", message)