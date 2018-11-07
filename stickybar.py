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

version = '1.0b0'

import sys, io, contextlib, platform

class StickyBarOutput(io.IOBase):

  def __init__(self, callback, *, buffer, index):
    self._callback = callback
    self._buffer = buffer
    self._clear_bar = index + b'\033[2K\033[A'
    self._save_and_open_bar = index + b'\033[A\0337' + index + b'\r\033[0;33m'
    self._restore = b'\033[0m\0338'
    self._clear_and_start_bar = b'\r\033[K\033[0;33m'
    self._newline_and_clear = b'\033[0m' + index + b'\r\033[K'
    super().__init__()

  def writable(self):
    return True

  def isatty(self):
    return self._buffer.isatty()

  def write(self, text):
    self._buffer.write(self._clear_bar + text + self._save_and_open_bar + self._callback(True) + self._restore)
    self._buffer.flush()
    return len(text)

  def close(self):
    if not self.closed:
      self._buffer.write(self._clear_and_start_bar + self._callback(False) + self._newline_and_clear)
      self._buffer.flush()
      super().close()

@contextlib.contextmanager
def set_console_mode():
  if platform.system() == 'Windows': # pragma: no cover
    import ctypes
    handle = ctypes.windll.kernel32.GetStdHandle(-11) # https://docs.microsoft.com/en-us/windows/console/getstdhandle
    orig_mode = ctypes.c_uint32() # https://docs.microsoft.com/en-us/windows/desktop/WinProg/windows-data-types#lpdword
    ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(orig_mode)) # https://docs.microsoft.com/en-us/windows/console/getconsolemode
    ctypes.windll.kernel32.SetConsoleMode(handle, orig_mode.value | 4 | 8) # add ENABLE_VIRTUAL_TERMINAL_PROCESSING and DISABLE_NEWLINE_AUTO_RETURN, https://docs.microsoft.com/en-us/windows/console/setconsolemode
    try:
      yield b'\n'
    finally:
      ctypes.windll.kernel32.SetConsoleMode(handle, orig_mode)
  else:
    yield b'\033D'

@contextlib.contextmanager
def activate(callback):
  enc = sys.stdout.encoding
  with set_console_mode() as index, \
       StickyBarOutput(lambda r: callback(r).encode(enc), buffer=sys.stdout.buffer, index=index) as sbo, \
       contextlib.redirect_stdout(io.TextIOWrapper(sbo, encoding=enc, line_buffering=True)):
    yield
