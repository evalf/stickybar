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

version = '1.0b1'

import sys, os, contextlib, platform, threading, select, warnings


class StickyBar(threading.Thread):

  def __init__(self, fdread, fdwrite, index, callback, encoding, interval):
    self.fdread = fdread
    self.fdwrite = fdwrite
    self.index = index
    self.callback = callback
    self.encoding = encoding
    self.interval = interval
    super().__init__()

  def run(self):
    clear_bar = self.index + b'\033[2K\033[A' # clear line below cursor (scroll if necessary) and return to position
    new_empty_line = self.index + b'\r\033[K' # move to beginning of next line and clear
    save_and_open_bar = self.index + b'\033[A\0337\033[B' # save cursor and move to beginning of next line
    restore = b'\0338' # restore cursor
    for text in self.read():
      self.write(clear_bar + text + save_and_open_bar + self.bar(True) + restore)
    self.write(self.bar(False) + new_empty_line)

  def read(self):
    yield b'' # initialize bar
    while True:
      while self.interval and not select.select([self.fdread], [], [], self.interval)[0]:
        yield b''
      try:
        text = os.read(self.fdread, 1024)
      except OSError:
        return
      if not text:
        return
      yield text

  def write(self, data):
    while data:
      n = os.write(self.fdwrite, data)
      data = data[n:]

  def bar(self, running):
    try:
      bar = b'\033[0;33m' + self.callback(running).encode(self.encoding)
    except Exception as e:
      try:
        msg = str(e).encode(self.encoding)
      except:
        msg = b'unknown error'
      bar = b'\033[0;31mcallback failed: ' + msg
    return b'\r\033[K' + bar + b'\033[0m'


@contextlib.contextmanager
def activate(callback, interval=0):
  with contextlib.ExitStack() as stack:

    # create virtual terminal
    fdread, fdwrite = getattr(os, 'openpty', os.pipe)()
    stack.callback(os.close, fdread) # fdwrite is closed separately to signal to the thread

    # save original output file descriptor
    fileno = os.dup(sys.stdout.fileno())
    stack.callback(os.close, fileno)

    # set console mode
    if platform.system() == 'Windows': # pragma: no cover
      if interval:
        warnings.warn('stickybar: "interval" is ignored on Windows', RuntimeWarning)
        interval = 0
      import ctypes
      handle = ctypes.windll.kernel32.GetStdHandle(-11) # https://docs.microsoft.com/en-us/windows/console/getstdhandle
      orig_mode = ctypes.c_uint32() # https://docs.microsoft.com/en-us/windows/desktop/WinProg/windows-data-types#lpdword
      ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(orig_mode)) # https://docs.microsoft.com/en-us/windows/console/getconsolemode
      ctypes.windll.kernel32.SetConsoleMode(handle, orig_mode.value | 4 | 8) # add ENABLE_VIRTUAL_TERMINAL_PROCESSING and DISABLE_NEWLINE_AUTO_RETURN, https://docs.microsoft.com/en-us/windows/console/setconsolemode
      stack.callback(ctypes.windll.kernel32.SetConsoleMode, handle, orig_mode)
      index = b'\n'
    else:
      index = b'\033D'

    # create thread
    t = StickyBar(fdread, fileno, index, callback, sys.stdout.encoding, interval)
    stack.callback(t.join)

    # replace stdout by virtual terminal
    os.dup2(fdwrite, sys.stdout.fileno())
    os.close(fdwrite)
    stack.callback(os.dup2, fileno, sys.stdout.fileno()) # restore stdout and signal to thread

    if platform.system() == 'Windows': # pragma: no cover
      # In Windows, `sys.stdout` becomes unusable after
      # `os.dup2(..,sys.stdout.fileno())`, hence we recreate `sys.stdout` here.
      # Because a pipe is not a tty, `fdopen` defaults to buffering with fixed
      # size chunks.  `buffering=1` enforces lines buffering.  The new
      # `sys.stdout` answers `False` to `.isatty()` for the same reason.
      stack.enter_context(contextlib.redirect_stdout(os.fdopen(sys.stdout.fileno(), 'w', encoding=sys.stdout.encoding, buffering=1)))

    # start bar-drawing thread
    t.start()
    yield
