from datetime import date
from datetime import datetime
import sys
import termios
import threading
import time
from datetime import timedelta
import tty

__version__ = '0.5.0'

def _getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            yield sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class Line:
    """An empty line. Base class for other types of line.
    """
    def __init__(self, io):
        self.io = io
        if self.io is not None:
            self.io.append(self)
    
    def activate(self):
        """Pass control to the line. By default, lines return immediately. Subclasses may read input or do other things instead.
        """
        pass
    
    def draw(self):
        """Draw the line's content into the line where the cursor is currently positioned.
        """
        if self.io is None:
            return
        print(self.io.terminal.move_x(0) + self.io.terminal.clear_eol, end='', flush=True)
    
    def is_interactive(self):
        """Returns a boolean representing whether or not this line has an interactive mode.
        
        If this returns False, the line will be skipped when moving up or down using the arrow keys.
        """
        return False

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
            print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message[:self.io.terminal.width - 10], end=self.io.terminal.black_on_cyan('...'), flush=True)
        elif len(self.message) + 7 == self.io.terminal.width:
            print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message, end='', flush=True)
        else:
            print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message + self.io.terminal.clear_eol, end='', flush=True)
        
    def formatted_prefix(self):
        interactive = self.is_interactive()
        ret = self.io.terminal.bold('[') if interactive else '['
        if self.prefix_color is not None and self.io is not None:
            ret += getattr(self.io.terminal, self.prefix_color)(self.prefix[:4])
        else:
            ret += self.prefix[:4]
        ret += self.io.terminal.bold(']') if interactive else ']'
        return ret + ' '

class InputLine(PrefixLine):
    def __init__(self, io, message='', prefix='????', prefix_color='yellow'):
        self.answer = ''
        self.position = 0
        self.submitted = False
        super().__init__(io, message=message, prefix=prefix, prefix_color=prefix_color)
    
    def activate(self):
        if self.io is None or self.submitted:
            return
        self.io.update()
        sequence = ''
        for ch in self.io._getch:
            if self.io is None or self.submitted:
                return
            if sequence == '\x1b':
                if ch == '[':
                    sequence += ch
                else:
                    self.answer = self.answer[:self.position] + sequence + ch + self.answer[self.position:]
                    self.position += 2
                    sequence = ''
            elif sequence == '\x1b[':
                if ch == 'A': # up arrow
                    if not self.io.activate_up():
                        print('\x07', end='', flush=True)
                    sequence = ''
                    self.io.update()
                elif ch == 'B': # down arrow
                    if not self.io.activate_down():
                        print('\x07', end='', flush=True)
                    sequence = ''
                    self.io.update()
                elif ch == 'C': # right arrow
                    if self.position >= len(self.answer):
                        print('\x07', end='', flush=True)
                        sequence = ''
                    else:
                        self.position += 1
                        sequence = ''
                        self.io.update()
                elif ch == 'D': # left arrow
                    if self.position <= 0:
                        print('\x07', end='', flush=True)
                        sequence = ''
                    else:
                        self.position -= 1
                        sequence = ''
                        self.io.update()
                else:
                    self.answer = self.answer[:self.position] + sequence + ch + self.answer[self.position:]
                    self.position += 3
                    sequence = ''
                    self.io.update()
            else:
                sequence = ''
                if ch in ['\r', '\n', '\x03', '\x04']:
                    self.submitted = True
                    self.io.update()
                    return
                elif ch == '\x7f':
                    if self.position <= 0:
                        print('\x07', end='', flush=True)
                    else:
                        self.answer = self.answer[:self.position - 1] + self.answer[self.position:]
                        self.position -= 1
                        self.io.update()
                elif ch == '\x1b':
                    sequence += ch
                else:
                    self.answer = self.answer[:self.position] + ch + self.answer[self.position:]
                    self.position += 1
                    self.io.update()
            if self.io is None or self.submitted:
                return
    
    def draw(self):
        if self.io.terminal.width < 3:
            print(self.io.terminal.move_x(0) + self.io.terminal.clear_eol, end='', flush=True)
        elif self.io.terminal.width < 14:
            print(self.io.terminal.move_x(0) + self.answer[:self.io.terminal.width - 3], end=self.io.terminal.black_on_cyan('...'), flush=True)
        elif len(self.message) + len(self.answer) + 8 > self.io.terminal.width: # line does not fit on screen
            if self.position != 0 and len(self.answer) - self.position + 11 < self.io.terminal.width: # display the end of the answer
                if len(self.answer) + 11 < self.io.terminal.width:
                    end_of_answer = self.message[-self.io.terminal.width + len(self.answer) + 11:] + self.io.terminal.bold(self.answer)
                else:
                    end_of_answer = self.io.terminal.bold(self.answer[-self.io.terminal.width + 11:])
                print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.io.terminal.black_on_cyan('...') + end_of_answer + ' ' + self.io.terminal.move_x(self.io.terminal.width - 1 - len(self.answer) + self.position), end='', flush=True)
            else:
                section = (len(self.message) + self.position - 3) // (self.io.terminal.width - 13)
                if section <= 0:
                    print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message + self.io.terminal.bold(self.answer[:self.io.terminal.width - len(self.message) - 10]) + self.io.terminal.black_on_cyan('...') + self.io.terminal.move_x(7 + len(self.message) + self.position), end='', flush=True)
                else:
                    if len(self.message) > 3 + section * (self.io.terminal.width - 13):
                        partial_message = self.message[3 + section * (self.io.terminal.width - 13):]
                        partial_answer = partial_message + self.io.terminal.bold(self.answer[:self.io.terminal.width - len(partial_message) - 13])
                    else:
                        partial_answer = self.io.terminal.bold(self.answer[section * (self.io.terminal.width - 13) - len(self.message) + 3:][:self.io.terminal.width - 13])
                    print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.io.terminal.black_on_cyan('...') + partial_answer + self.io.terminal.black_on_cyan('...') + self.io.terminal.move_x(7 + len(self.message) + self.position - section * (self.io.terminal.width - 13)), end='', flush=True)
        elif len(self.message) + len(self.answer) + 8 == self.io.terminal.width: # line fits exactly on screen
            print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message + self.io.terminal.bold(self.answer) + self.io.terminal.move_x(7 + len(self.message) + self.position), end='', flush=True)
        else:
            print(self.io.terminal.move_x(0) + self.formatted_prefix() + self.message + self.io.terminal.bold(self.answer) + self.io.terminal.clear_eol + self.io.terminal.move_x(7 + len(self.message) + self.position), end='', flush=True)
        
    def is_interactive(self):
        return not self.submitted
    
    def join(self, update_interval=0.1):
        """Blocks until input has been submitted, then returns that input.
        """
        while not self.submitted:
            if self.io.active_line is None:
                self.io.activate(self)
            else:
                self.io.update()
                time.sleep(update_interval)
        return self.answer

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
        interactive = self.is_interactive()
        ret = self.io.terminal.bold('[') if interactive else '['
        ret += self.prefix_formatter(self.prefix)
        ret += self.io.terminal.bold(']') if interactive else ']'
        return ret + ' '
    
    def join(self, update_interval=0.1):
        try:
            self.thread.start()
        except RuntimeError:
            pass # thread is already running
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

class SleepLine(TaskLine):
    def __init__(self, io, end, message=None):
        class SleepThread(threading.Thread):
            def __init__(self, delta):
                self.delta = delta.total_seconds()
                self.progress = 0.0
                self.state = None
                super().__init__()
            
            def run(self):
                if self.delta <= 0:
                    self.progress = 1.0
                    return
                for progress in range(5):
                    time.sleep(self.delta / 5)
                    self.progress = (progress + 1) / 5
        
        if isinstance(end, datetime):
            # sleep until datetime
            thread = SleepThread(delta=(end - datetime.utcnow()))
            if message is None:
                if end.date() == date.today():
                    date_string = end.strftime('%H:%M:%S')
                else:
                    date_string = end.strftime('%Y-%m-%d %H:%M:%S')
                message = 'sleeping until ' + date_string
        else:
            # sleep for time interval
            if not isinstance(end, timedelta):
                end = timedelta(seconds=end)
            thread = SleepThread(delta=end)
            if message is None:
                if end.total_seconds() >= 86400:
                    date_string = str(end.total_seconds() // 86400) + ' days'
                elif end.total_seconds() >= 3600:
                    date_string = str(end.total_seconds() // 3600) + ' hours'
                elif end.total_seconds() >= 60:
                    date_string = str(end.total_seconds() // 60) + ' minutes'
                elif end.total_seconds() >= 1:
                    date_string = str(int(end.total_seconds())) + ' seconds'
                else:
                    date_string = str(int(end.total_seconds() * 1000)) + ' milliseconds'
                message = 'sleeping for ' + date_string
        super().__init__(io, thread=thread, message=message)

class IO:
    def __init__(self, terminal=None):
        if terminal is None:
            import blessings
            terminal = blessings.Terminal()
        self.terminal = terminal
        self.lines = []
        self.max_lines = 1
        self.position = 0
        self.active_line = None
        self.update_lock = threading.Lock()
        self._getch = None
    
    def __contains__(self, item):
        return item in self.lines
    
    def __delitem__(self, key):
        if key < self.max_lines - self.terminal.height:
            raise IndexError('Line has scrolled out of screen')
        del self.lines[key]
        self.update()
    
    def __enter__(self):
        self._getch = _getch()
        return self
    
    def __exit__(self, exception_type, exception_val, trace):
        """Update everything and print a newline after the last line
        """
        self.active_line = None
        self.update()
        print(self.terminal.move_x(0), end='', flush=True)
        if len(self):
            print(flush=True)
        del self._getch
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
    
    def activate(self, line):
        if (line is None) or (line in self):
            self.active_line = line
            self.update()
            if line is not None:
                if line.is_interactive():
                    line.activate()
                self.activate(None)
        else:
            raise ValueError()
    
    def activate_down(self):
        prev_active_line = self.active_line
        for line in (self.lines if self.active_line is None else self.lines[self.index(self.active_line) + 1:]):
            if line.is_interactive():
                self.activate(line)
                self.active_line = prev_active_line
                return True
        return False
    
    def activate_up(self):
        prev_active_line = self.active_line
        for line in reversed(self.lines if self.active_line is None else self.lines[:self.index(self.active_line)]):
            if line.is_interactive():
                self.activate(line)
                self.active_line = prev_active_line
                return True
        return False
    
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
            self.activate(line)
            line.join(update_interval=update_interval)
        else:
            threading.Thread(target=line.join, kwargs={'update_interval': update_interval}).start()
    
    def getch(self):
        return next(self._getch)
    
    def index(self, line):
        return self.lines.index(line)
    
    def input(self, prompt='', prefix='????'):
        """Display the prompt and listen for newline-terminated input on stdin.
        """
        line = InputLine(self, message=prompt, prefix=prefix)
        self.activate(line)
        return line.join()
    
    def insert(self, position, line):
        self.lines.insert(position, line)
        self.update()
    
    def move_down(self):
        print(flush=True)
        self.position += 1
        if self.position == self.max_lines:
            self.max_lines += 1
    
    def move_up(self):
        if self.position <= 0 or self.max_lines - self.position >= self.terminal.height:
            raise IndexError()
        else:
            self.position -= 1
            print(self.terminal.move_up, end='', flush=True)
    
    def print(self, *args, sep=' ', end='\n', file=None, flush=False, prefix='**'):
        """Print the values to a new StringLine after the existing lines.
        
        Designed to be compatible with the built-in function "print". However, all keyword arguments other than "sep" and "prefix" are ignored.
        """
        PrefixLine(self, message=sep.join(str(arg) for arg in args), prefix=prefix)
    
    def update(self):
        with self.update_lock:
            self.max_lines = max(self.max_lines, len(self))
            starting_line = 0
            if self.max_lines > self.terminal.height:
                starting_line = self.max_lines - self.terminal.height
            while self.position > starting_line:
                self.move_up()
            if len(self) > starting_line:
                for line in self.lines[starting_line:-1]:
                    line.io = self
                    line.draw()
                    self.move_down()
                self.lines[-1].draw()
            else:
                print(self.terminal.move_x(0) + self.terminal.clear_eol, end='', flush=True)
            if self.position < self.max_lines - 1:
                print(self.terminal.move_down + self.terminal.move_x(0) + self.terminal.clear_eos + self.terminal.move_up, end='', flush=True)
            if self.active_line is not None and self.active_line in self:
                while self.position > self.index(self.active_line):
                    self.move_up()
                self.active_line.draw()
