import stickybar, unittest, pyte, sys, platform, os, time

class StickyBar(unittest.TestCase):

  def setUp(self):
    self.screen = pyte.Screen(20, 6)
    self.stream = pyte.ByteStream(self.screen)
    if platform.system() != 'Windows':
      self.screen.set_mode(pyte.modes.LNM)
    self.fdread, fdwrite = os.pipe()
    self.stdout = os.fdopen(fdwrite, 'w', buffering=1)

  def tearDown(self):
    self.stdout.close()

  def assertScreen(self, x, y, *lines):
    time.sleep(.1)
    self.stream.feed(os.read(self.fdread, 1024))
    self.assertEqual(self.screen.cursor.x, x)
    self.assertEqual(self.screen.cursor.y, y)
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
    for i in range(self.screen.lines):
      print(i, '|', *(self.screen.buffer[i][j].data for j in range(self.screen.columns)), '|', i, sep='')

  def test_output(self):
    with stickybar.open(lambda running: 'my bar', stdout=self.stdout) as bar:
      print('first line', file=bar)
      self.assertScreen(0, 1, 'first line', '', 'my bar')
      print('second line', file=bar)
      self.assertScreen(0, 2, 'first line', 'second line', '', 'my bar')
    self.assertScreen(0, 3, 'first line', 'second line', 'my bar')

  def test_scroll(self):
    with stickybar.open(lambda running: 'my bar', stdout=self.stdout) as bar:
      for i in range(10):
        print('line', i, file=bar)
      self.assertScreen(0, 4, 'line 6', 'line 7', 'line 8', 'line 9', '', 'my bar')
    self.assertScreen(0, 5, 'line 6', 'line 7', 'line 8', 'line 9', 'my bar')

  def test_restore(self):
    with stickybar.open(lambda running: 'my bar', stdout=self.stdout) as bar:
      print('first line', file=bar)
      print('second line', end='', flush=True, file=bar)
      self.assertScreen(11, 1, 'first line', 'second line', 'my bar')
    self.assertScreen(0, 2, 'first line', 'my bar')

  def test_callback(self):
    val = 10
    with stickybar.open(lambda running: 'val={} run={}'.format(val, running), stdout=self.stdout) as bar:
      print('first line', file=bar)
      self.assertScreen(0, 1, 'first line', '', 'val=10 run=True')
      val = 20
      print('second line', file=bar)
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val=20 run=True')
      val = 30
    self.assertScreen(0, 3, 'first line', 'second line', 'val=30 run=False')

  def test_activate(self):
    stdout = sys.stdout
    try:
      sys.stdout = self.stdout
      with stickybar.activate(lambda running: 'my bar'):
        print('output')
        self.assertScreen(0, 1, 'output', '', 'my bar')
      self.assertScreen(0, 2, 'output', 'my bar')
    finally:
      sys.stdout = stdout
