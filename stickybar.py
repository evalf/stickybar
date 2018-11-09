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

import sys, os, contextlib, platform, _thread, select

def read(fd):
  text = os.read(fd, 1024)
  while text:
    yield text
    text = os.read(fd, 1024)
    
def add_bar(callback, fdread, fdwrite, lock):
  with lock, set_console_mode() as index:
    clear_bar = index + b'\033[2K\033[A'
    save_and_open_bar = index + b'\033[A\0337' + index + b'\r\033[0;33m'
    restore = b'\033[0m\0338'
    clear_and_start_bar = b'\r\033[K\033[0;33m'
    newline_and_clear = b'\033[0m' + index + b'\r\033[K'
    os.write(fdwrite, clear_bar + save_and_open_bar + callback(True) + restore)
    for text in read(fdread):
      os.write(fdwrite, clear_bar + text + save_and_open_bar + callback(True) + restore)
    os.write(fdwrite, clear_and_start_bar + callback(False) + newline_and_clear)

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
def open(callback, stdout=None):
  if stdout is None:
    stdout = sys.stdout
  lock = _thread.allocate_lock()
  try:
    fdread, fdwrite = os.pipe()
    _thread.start_new_thread(add_bar, (lambda r: callback(r).encode(stdout.encoding), fdread, stdout.fileno(), lock))
    with os.fdopen(fdwrite, 'w', buffering=1) as barout:
      yield barout
  finally:
    lock.acquire()

@contextlib.contextmanager
def activate(callback):
  stdout = sys.stdout
  try:
    with open(callback, stdout) as sys.stdout:
      yield
  finally:
    sys.stdout = stdout
