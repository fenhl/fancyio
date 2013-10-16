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

class IO:
    def __init__(self, terminal=None):
        if terminal is None:
            import blessings
            terminal = blessings.Terminal()
        self.terminal = terminal
        self.lines = []
        self.max_lines = 1
        self.position = 0
    
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
    
    def insert(self, position, line):
        self.lines.insert(position, line)
        self.update()
    
    def print(self, *args, sep=' ', end='\n', file=None, flush=False):
        """Print the values to a new StringLine after the existing lines.
        
        Designed to be compatible with the built-in function "print". However, all keyword arguments other than "sep" are ignored.
        """
        StringLine(self, message=sep.join(str(arg) for arg in args))
    
    def update(self):
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
