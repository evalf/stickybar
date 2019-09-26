import stickybar, unittest, pyte, sys, platform, os, time

class StickyBar(unittest.TestCase):

  def setUp(self):
    self.stdout = sys.stdout
    self.screen = pyte.Screen(60, 6)
    self.stream = pyte.ByteStream(self.screen)
    if platform.system() != 'Windows':
      self.screen.set_mode(pyte.modes.LNM)
    self.fdread, fdwrite = os.pipe()
    self.fdwrite = os.dup(fdwrite)
    sys.stdout = os.fdopen(fdwrite, 'w', buffering=1)

  def tearDown(self):
    sys.stdout.close()
    os.close(self.fdread)
    os.close(self.fdwrite)
    sys.stdout = self.stdout

  def updateScreen(self):
    sys.stdout.flush()
    time.sleep(.1) # give StickyBar thread some time to finish writing
    os.write(self.fdwrite, b'\0') # append token byte to prevent blocking read
    data = os.read(self.fdread, 1024)
    assert data[-1:] != 0 # assert data ends with token byte
    self.stream.feed(data[:-1]) # update pyte screen

  def assertScreen(self, x, y, *lines, error=False, nbar=1):
    self.updateScreen()
    self.assertEqual(self.screen.cursor.x, x)
    self.assertEqual(self.screen.cursor.y, y)
    for i in range(self.screen.lines):
      for j in range(self.screen.columns):
        char = self.screen.buffer[i][j]
        self.assertEqual(char.data, lines[i][j] if i < len(lines) and j < len(lines[i]) else ' ')
        self.assertEqual(char.fg, 'default' if not 0 < len(lines)-i <= nbar or j >= len(lines[i]) else 'red' if error else 'brown')
        self.assertEqual(char.bg, 'default')
        self.assertFalse(char.bold)
        self.assertFalse(char.italics)
        self.assertFalse(char.underscore)
        self.assertFalse(char.strikethrough)
        self.assertFalse(char.reverse)

  def printscreen(self): # for debugging
    self.updateScreen()
    for i in range(self.screen.lines):
      print(i, '|', *(self.screen.buffer[i][j].data for j in range(self.screen.columns)), '|', i, sep='', file=self.stdout)

  def test_output(self):
    with stickybar.activate(lambda running: 'my bar', update=0):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', 'my bar')
      print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'my bar')
    self.assertScreen(0, 3, 'first line', 'second line', 'my bar')

  def test_long_output(self):
    with stickybar.activate(lambda running: 'my bar', update=0):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', 'my bar')
      print('second line: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxyz')
      self.assertScreen(0, 2, 'first line', 'second line: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrsz', '', 'my bar')
    self.assertScreen(0, 3, 'first line', 'second line: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrsz', 'my bar')

  def test_long_status(self):
    with stickybar.activate(lambda running: 'my bar: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxyz', update=0):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', 'my bar: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxz')
      print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'my bar: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxz')
    self.assertScreen(0, 4, 'first line', 'second line', 'my bar: abcdefghijklmnopqrstuvwxyz abcdefghijklmnopqrstuvwxy', 'z', nbar=2)

  def test_scroll(self):
    with stickybar.activate(lambda running: 'my bar', update=0):
      for i in range(10):
        print('line', i)
      self.assertScreen(0, 4, 'line 6', 'line 7', 'line 8', 'line 9', '', 'my bar')
    self.assertScreen(0, 5, 'line 6', 'line 7', 'line 8', 'line 9', 'my bar')

  def test_restore(self):
    with stickybar.activate(lambda running: 'my bar', update=0):
      print('first line')
      print('second line', end='', flush=True)
      self.assertScreen(11, 1, 'first line', 'second line', 'my bar')
    self.assertScreen(0, 2, 'first line', 'my bar')

  def test_noupdate(self):
    val = 0
    with stickybar.activate(lambda running: 'val={} run={}'.format(val, running), update=0):
      self.assertScreen(0, 0, '', 'val=0 run=True')
      val = 1; print('first line')
      self.assertScreen(0, 1, 'first line', '', 'val=0 run=True')
      val = 2; print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val=0 run=True')
      val = 3
    self.assertScreen(0, 3, 'first line', 'second line', 'val=3 run=False')

  def test_positive_update(self):
    val = 0
    with stickybar.activate(lambda running: 'val={} run={}'.format(val, running), update=.9):
      self.assertScreen(0, 0, '', 'val=0 run=True')
      val = 1; print('first line')
      self.assertScreen(0, 1, 'first line', '', 'val=0 run=True')
      val = 2; print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val=0 run=True')
      val = 3; time.sleep(1)
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val={} run=True'.format(0 if platform.system() == 'Windows' else 3))
    self.assertScreen(0, 3, 'first line', 'second line', 'val=3 run=False')

  def test_negative_update(self):
    val = 0
    with stickybar.activate(lambda running: 'val={} run={}'.format(val, running), update=-1):
      self.assertScreen(0, 0, '', 'val=0 run=True')
      val = 1; print('first line')
      self.assertScreen(0, 1, 'first line', '', 'val=1 run=True')
      val = 2; print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val=2 run=True')
      val = 3
    self.assertScreen(0, 3, 'first line', 'second line', 'val=3 run=False')

  def test_error(self):
    with stickybar.activate(lambda running: 'val={:.1f}'.format('foo'), update=0):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', "ValueError: Unknown format code 'f' for object of type 'str'", error=True)
    self.assertScreen(0, 2, 'first line', "ValueError: Unknown format code 'f' for object of type 'str'", error=True)
