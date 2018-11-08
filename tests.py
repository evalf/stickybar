import stickybar, unittest, pyte, io, sys, contextlib, platform

class PyteBuffer:
  def __init__(self, screen):
    self._stream = pyte.ByteStream(screen)
  def readable(self):
    return False
  def writable(self):
    return True
  def seekable(self):
    return False
  def isatty(self):
    return True
  def write(self, data):
    self._stream.feed(data)
  def flush(self):
    pass

class StickyBar(unittest.TestCase):

  def setUp(self):
    self._stdout = sys.stdout
    self.screen = pyte.Screen(20, 6)
    if platform.system() != 'Windows':
      self.screen.set_mode(pyte.modes.LNM)
    sys.stdout = io.TextIOWrapper(PyteBuffer(self.screen), line_buffering=True)

  def tearDown(self):
    sys.stdout = self._stdout

  def assertCursor(self, x, y):
    self.assertEqual(self.screen.cursor.x, x)
    self.assertEqual(self.screen.cursor.y, y)

  def assertScreen(self, *lines):
    for i in range(self.screen.lines):
      for j in range(self.screen.columns):
        char = self.screen.buffer[i][j]
        self.assertEqual(char.data, lines[i][j] if i < len(lines) and j < len(lines[i]) else ' ')
        self.assertEqual(char.fg, 'brown' if i == len(lines)-1 and j < len(lines[i]) else 'default')
        self.assertEqual(char.bg, 'default')
        self.assertFalse(char.bold)
        self.assertFalse(char.italics)
        self.assertFalse(char.underscore)
        self.assertFalse(char.strikethrough)
        self.assertFalse(char.reverse)

  def printscreen(self): # for debugging
    sys.stderr.writelines('{0}|{1}|{0}\n'.format(i, ''.join(self.screen.buffer[i][j].data for j in range(self.screen.columns))) for i in range(self.screen.lines))

  def test_output(self):
    with stickybar.activate(lambda running: 'my bar'):
      print('first line')
      self.assertScreen('first line', '', 'my bar')
      self.assertCursor(0, 1)
      print('second line')
      self.assertScreen('first line', 'second line', '', 'my bar')
      self.assertCursor(0, 2)
    self.assertScreen('first line', 'second line', 'my bar')
    self.assertCursor(0, 3)

  def test_scroll(self):
    with stickybar.activate(lambda running: 'my bar'):
      for i in range(10):
        print('line', i)
      self.assertScreen('line 6', 'line 7', 'line 8', 'line 9', '', 'my bar')
      self.assertCursor(0, 4)
    self.assertScreen('line 6', 'line 7', 'line 8', 'line 9', 'my bar')
    self.assertCursor(0, 5)

  def test_restore(self):
    with stickybar.activate(lambda running: 'my bar'):
      print('first line')
      print('second line', end='', flush=True)
      self.assertScreen('first line', 'second line', 'my bar')
      self.assertCursor(11, 1)
    self.assertScreen('first line', 'my bar')
    self.assertCursor(0, 2)

  def test_callback(self):
    with stickybar.activate(lambda running: 'val={} run={}'.format(val, running)):
      val = 10
      print('first line')
      self.assertScreen('first line', '', 'val=10 run=True')
      self.assertCursor(0, 1)
      val = 20
      print('second line')
      self.assertScreen('first line', 'second line', '', 'val=20 run=True')
      self.assertCursor(0, 2)
      val = 30
    self.assertScreen('first line', 'second line', 'val=30 run=False')
    self.assertCursor(0, 3)

  def test_isatty(self):
    with stickybar.activate(lambda running: 'my bar'):
      self.assertTrue(sys.stdout.isatty())
