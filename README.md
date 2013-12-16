**fancyio** creates fancy terminal input/output in Python 3, in the style of programs like Debian lsb (think `init`) or ZNC.

This is `fancyio` version 0.5.0 ([semver][]).

Requirements
============

*   Python 3.3
*   [blessings][] 1.6 — must be run through `2to3` first

Examples
========

Basic input and output:

```Python
with fancyio.IO() as io: # Create a new IO object. The with statement prints a newline after the last line on exit.
    print = io.print # Make print point to the IO object's convenience method instead of the built-in function.
    input = io.input # Same but for “input”
    print('Hello, world!')
    print(input('CRUISE CONTROL ').upper()) # get some input, then print the uppercased string to a new line
```

Editing the lines:

```Python
with fancyio.IO() as io:
    io.print('foo') # Add a line saying “foo”
    fancyio.StringLine(io, 'bar') # Same but with “bar”
    del io[0] # Delete the “foo” line
    io.insert(0, fancyio.StringLine(None, 'baz')) # Create a new StringLine which is not associated with the io object, and insert it.
    io.lines = [fancyio.StringLine(None, 'foobar')] + io.lines # Same, but by manually editing the list of lines.
    io.update() # Since we manually edited io.lines, we need to call update.
    io.clear() # Delete all lines
```

Tasks:

```Python
import time

with fancyio.IO() as io:
    io.do(time.sleep, args=[2], message='waiting for 2 secs') # Displays an ellipsis, which changes to “ok” after the function is done.
```

[blessings]: https://github.com/erikrose/blessings (github: erikrose: blessings)
[semver]: http://semver.org/ (Semantic Versioning 2.0.0)
