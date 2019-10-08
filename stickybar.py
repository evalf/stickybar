# Copyright (c) 2014 Evalf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

version = '1.0'

import sys, os, contextlib, platform, threading, select, warnings, time


class StickyBar(threading.Thread):

  def __init__(self, fdread, fdwrite, callback, encoding, update):
    self.fdread = fdread
    self.fdwrite = fdwrite
    self.callback = callback
    self.encoding = encoding
    self.update = update
    super().__init__()

  def run(self):
    self.write(b'\n' + self.callback().encode(self.encoding, errors='ignore') + b'\r\033[A\033[K')
    for text in self.read():
      self.write(text.replace(b'\n', b'\n\n\033[A\033[L') if text else b'\0337\033[B\r' + self.callback().encode(self.encoding, errors='ignore') + b'\033[K\0338')
    self.write(b'\033[B\033[2K\033[A')

  def poll(self, timeout):
    return timeout > 0 and (platform.system() == 'Windows' or select.select([self.fdread], [], [], timeout)[0])

  def read(self):
    try:
      nextupdate = time.perf_counter() + self.update
      while True:
        while self.update > 0 and not self.poll(nextupdate - time.perf_counter()):
          yield b''
          nextupdate += self.update
        text = os.read(self.fdread, 1024)
        if not text:
          break
        yield text
        if self.update < 0: # redraw bar after every write
          yield b''
    except OSError:
      pass

  def write(self, data):
    while data:
      n = os.write(self.fdwrite, data)
      data = data[n:]


@contextlib.contextmanager
def activate(callback, update):
  def bar(arg=True):
    try:
      text = callback(arg)
      color = 3 # yellow
    except Exception as e:
      text = '{}: {}'.format(getattr(type(e), '__name__', 'callback failed'), e)
      color = 1 # red
    return '\033[0;3{}m{}\033[0m'.format(color, text)
  with draw(bar, update):
    yield
  print('\r{}\033[K'.format(bar(False)))


@contextlib.contextmanager
def draw(callback, update):

  with contextlib.ExitStack() as stack:

    # create virtual terminal
    fdread, fdwrite = getattr(os, 'openpty', os.pipe)()
    stack.callback(os.close, fdread) # fdwrite is closed separately to signal to the thread

    # save original output file descriptor
    fileno = os.dup(sys.stdout.fileno())
    stack.callback(os.close, fileno)

    # create thread
    t = StickyBar(fdread, fileno, callback, sys.stdout.encoding, update)
    stack.callback(t.join)

    # replace stdout by virtual terminal
    os.dup2(fdwrite, sys.stdout.fileno())
    stack.callback(os.dup2, fileno, sys.stdout.fileno()) # restore stdout and signal to thread
    os.close(fdwrite)

    if platform.system() != 'Windows':
      os.write(fileno, b'\033[?7l') # disable line wrap
      stack.callback(os.write, fileno, b'\033[?7h') # enable line wrap
    else:
      # set console mode
      import ctypes
      kernel32 = ctypes.WinDLL('kernel32')
      handle = kernel32.GetStdHandle(-11) # https://docs.microsoft.com/en-us/windows/console/getstdhandle
      orig_mode = ctypes.c_uint32() # https://docs.microsoft.com/en-us/windows/desktop/WinProg/windows-data-types#lpdword
      kernel32.GetConsoleMode(handle, ctypes.byref(orig_mode)) # https://docs.microsoft.com/en-us/windows/console/getconsolemode
      new_mode = orig_mode.value
      new_mode |= 4 # check ENABLE_VIRTUAL_TERMINAL_PROCESSING
      new_mode &= ~2 # uncheck ENABLE_WRAP_AT_EOL_OUTPUT
      if new_mode != orig_mode.value:
        kernel32.SetConsoleMode(handle, ctypes.c_uint32(new_mode)) # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        stack.callback(kernel32.SetConsoleMode, handle, orig_mode)

      # In Windows, `sys.stdout` becomes unusable after
      # `os.dup2(..,sys.stdout.fileno())`, hence we recreate `sys.stdout` here.
      # Because a pipe is not a tty, `fdopen` defaults to buffering with fixed
      # size chunks.  `buffering=1` enforces lines buffering.  The new
      # `sys.stdout` answers `False` to `.isatty()` for the same reason.
      stack.enter_context(contextlib.redirect_stdout(os.fdopen(sys.stdout.fileno(), 'w', encoding=sys.stdout.encoding, buffering=1)))

    # start bar-drawing thread
    t.start()
    yield
