import threading
import time

class Line:
    """An empty line. Base class for other types of line.
    """
    def __init__(self, io):
        self.io = io
        if self.io is not None:
            self.io.append(self)
    
    def draw(self):
        """Draw the line's content into the line where the cursor is currently positioned.
        """
        if self.io is None:
            return
        print(self.io.terminal.move_x(0) + self.io.terminal.clear_eol, end='', flush=True)

class StringLine(Line):
    """A line of formatted text.
    """
    def __init__(self, io, message=''):
        self.message = message
        super().__init__(io)
    
    def draw(self):
        if self.io is None:
            return
        print(self.io.terminal.move_x(0), end='', flush=True)
        if len(self.message) > self.io.terminal.width:
            print(self.message[:self.io.terminal.width - 3], end=self.io.terminal.black_on_cyan('...'), flush=True)
        elif len(self.message) == self.io.terminal.width:
            print(self.message, end='', flush=True)
        else:
            print(self.message + self.io.terminal.clear_eol, end='', flush=True)

class PrefixLine(StringLine):
    def __init__(self, io, message='', prefix='**', prefix_color=None):
        if len(prefix) == 0:
            self.prefix = '    '
        elif len(prefix) == 1:
            self.prefix = ' ' + prefix + '  '
        elif len(prefix) == 2:
            self.prefix = ' ' + prefix + ' '
        elif len(prefix) == 3:
            self.prefix = prefix + ' '
        else:
            self.prefix = prefix
        self.prefix_color = prefix_color
        super().__init__(io, message=message)
    
    def draw(self):
        if self.io.terminal.width < 3:
            print(self.io.terminal.move_x(0) + self.io.terminal.clear_eol, end='', flush=True)
        elif self.io.terminal.width < 10:
            print(self.io.terminal.move_x(0) + self.message[:self.io.terminal.width - 3], end=self.io.terminal.black_on_cyan('...'), flush=True)
        elif len(self.message) + 7 > self.io.terminal.width:
            print(self.io.terminal.move_x(0) + '[' + self.formatted_prefix() + '] ' + self.message[:self.io.terminal.width - 10], end=self.io.terminal.black_on_cyan('...'), flush=True)
        elif len(self.message) + 7 == self.io.terminal.width:
            print(self.io.terminal.move_x(0) + '[' + self.formatted_prefix() + '] ' + self.message, end='', flush=True)
        else:
            print(self.io.terminal.move_x(0) + '[' + self.formatted_prefix() + '] ' + self.message + self.io.terminal.clear_eol, end='', flush=True)
        
    def formatted_prefix(self):
        if self.prefix_color is not None and self.io is not None:
            return getattr(self.io.terminal, self.prefix_color)(self.prefix[:4])
        else:
            return self.prefix[:4]

class TaskLine(PrefixLine):
    def __init__(self, io, thread, message=''):
        self.thread = thread
        self.progress = None
        self.state = None
        self.prefix_formatter = lambda x: x
        super().__init__(io, message=message, prefix='....')
    
    def draw(self):
        self.update_progress()
        super().draw()
    
    def formatted_prefix(self):
        return self.prefix_formatter(self.prefix)
    
    def join(self, update_interval=0.1):
        while self.thread.is_alive():
            if self.io is not None:
                self.io.update()
            if self.thread.is_alive():
                time.sleep(update_interval)
        if self.io is not None:
            self.io.update()
        self.thread.join()
        self.update_progress(progress=1.0)
        if self.io is not None:
            self.io.update()
    
    def start(self):
        self.thread.start()
    
    def update_progress(self, progress=None, state=None):
        if progress is not None:
            self.progress = progress
        progress = self.progress
        if state is not None:
            self.state = state
        state = self.state
        if progress is None:
            try:
                progress = self.thread.progress
            except AttributeError:
                progress = 0.0
        if state is None:
            try:
                state = self.thread.state
            except AttributeError:
                state = None
        self.prefix_formatter = lambda x: x
        if state is None:
            fifths = int(progress * 5)
            if fifths > 4:
                if state is None:
                    state = ' ok '
                    if self.io is not None:
                        self.prefix_formatter = self.io.terminal.green
                self.prefix = state
            else:
                self.prefix = '=' * fifths + '.' * (4 - fifths)
        else:
            self.prefix = state

class IO:
    def __init__(self, terminal=None):
        if terminal is None:
            import blessings
            terminal = blessings.Terminal()
        self.terminal = terminal
        self.lines = []
        self.max_lines = 1
        self.position = 0
        self.update_lock = threading.Lock()
    
    def __contains__(self, item):
        return item in self.lines
    
    def __delitem__(self, key):
        if key < self.max_lines - self.terminal.height:
            raise IndexError('Line has scrolled out of screen')
        del self.lines[key]
        self.update()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exception_type, exception_val, trace):
        """Update everything and print a newline after the last line
        """
        self.update()
        if len(self):
            print(flush=True)
        return exception_type is None # re-raise any exceptions
    
    def __getitem__(self, key):
        return self.lines[key]
    
    def __iter__(self):
        return iter(self.lines)
    
    def __len__(self):
        return len(self.lines)
    
    def __setitem__(self, key, value):
        self.lines[key] = value
        self.update()
    
    def append(self, line):
        self.lines.append(line)
        self.update()
    
    def clear(self):
        """Delete all lines.
        """
        self.lines = []
        self.update()
    
    def do(self, func, message='working', args=[], kwargs={}, update_interval=0.1, block=True):
        """Execute the function in a thread and display the message.
        
        If block is true, this method blocks until the function returns.
        """
        thread = threading.Thread(target=func, args=args[:], kwargs=kwargs.copy())
        line = TaskLine(self, thread=thread, message=message)
        line.start()
        if block:
            line.join(update_interval=update_interval)
        else:
            threading.Thread(target=line.join, kwargs={'update_interval': update_interval}).start()
    
    def insert(self, position, line):
        self.lines.insert(position, line)
        self.update()
    
    def print(self, *args, sep=' ', end='\n', file=None, flush=False):
        """Print the values to a new StringLine after the existing lines.
        
        Designed to be compatible with the built-in function "print". However, all keyword arguments other than "sep" are ignored.
        """
        PrefixLine(self, message=sep.join(str(arg) for arg in args))
    
    def update(self):
        with self.update_lock:
            self.max_lines = max(self.max_lines, len(self))
            starting_line = 0
            if self.max_lines > self.terminal.height:
                starting_line = self.max_lines - self.terminal.height
            prev_position = self.position
            while self.position > starting_line:
                print(self.terminal.move_up, end='', flush=True)
                self.position -= 1
            if len(self) > starting_line:
                for line in self.lines[starting_line:-1]:
                    line.io = self
                    line.draw()
                    print(flush=True)
                    self.position += 1
                self.lines[-1].draw()
            else:
                print(self.terminal.move_x(0) + self.terminal.clear_eol, end='', flush=True)
            if self.position < prev_position:
                print(self.terminal.move_down + self.terminal.move_x(0) + self.terminal.clear_eos + self.terminal.move_up, end='', flush=True)
