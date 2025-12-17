import curses

class KeyBind:
    def __init__(self, keys, func, desc=None):
        self.keys = keys if isinstance(keys, (list, tuple)) else [keys]
        self.func = func
        self.desc = desc

    def __call__(self, context):
        return self.func(context)

class SaveBind(KeyBind):
    def __init__(self, func=None):
        keys = [ord('s')]
        action = func if func else (lambda ctx: ctx.save() if hasattr(ctx, 'save') else None)
        super().__init__(keys, action, "Save")

class ExitBind(KeyBind):
    def __init__(self, func=None):
        keys = [27]
        super().__init__(keys, func, "Back / Cancel")

class ConfirmBind(KeyBind):
    def __init__(self, func=None):
        keys = [ord('\n'), 10, curses.KEY_ENTER]
        super().__init__(keys, func, "Select / Confirm")

class ToggleBind(KeyBind):
    def __init__(self, func=None):
        keys = [ord(' ')]
        super().__init__(keys, func, "Toggle")

class NavigationBind(KeyBind):
    def __init__(self, direction, func):
        keys = []
        if direction == 'UP':
            keys = [curses.KEY_UP, ord('k')]
        elif direction == 'DOWN':
            keys = [curses.KEY_DOWN, ord('j')]
        elif direction == 'LEFT':
            keys = [curses.KEY_LEFT, ord('h')]
        elif direction == 'RIGHT':
            keys = [curses.KEY_RIGHT, ord('l')]
        elif direction == 'HOME':
            keys = [curses.KEY_HOME]
        elif direction == 'END':
            keys = [curses.KEY_END]
        elif direction == 'PGUP':
            keys = [curses.KEY_PPAGE]
        elif direction == 'PGDN':
            keys = [curses.KEY_NPAGE]
            
        super().__init__(keys, func, f"Navigate {direction.title()}")
