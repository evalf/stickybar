import stickybar, unittest, pyte, sys, platform, os, time

class StickyBar(unittest.TestCase):

  def setUp(self):
    self.stdout = sys.stdout
    self.screen = pyte.Screen(80, 6)
    self.stream = pyte.ByteStream(self.screen)
    if platform.system() != 'Windows':
      self.screen.set_mode(pyte.modes.LNM)
    self.fdread, fdwrite = os.pipe()
    sys.stdout = os.fdopen(fdwrite, 'w', buffering=1)

  def tearDown(self):
    sys.stdout.close()
    os.close(self.fdread)
    sys.stdout = self.stdout

  def assertScreen(self, x, y, *lines, error=False):
    time.sleep(.1)
    self.stream.feed(os.read(self.fdread, 1024))
    self.assertEqual(self.screen.cursor.x, x)
    self.assertEqual(self.screen.cursor.y, y)
    for i in range(self.screen.lines):
      for j in range(self.screen.columns):
        char = self.screen.buffer[i][j]
        self.assertEqual(char.data, lines[i][j] if i < len(lines) and j < len(lines[i]) else ' ')
        self.assertEqual(char.fg, 'default' if i != len(lines)-1 or j >= len(lines[i]) else 'red' if error else 'brown')
        self.assertEqual(char.bg, 'default')
        self.assertFalse(char.bold)
        self.assertFalse(char.italics)
        self.assertFalse(char.underscore)
        self.assertFalse(char.strikethrough)
        self.assertFalse(char.reverse)

  def printscreen(self): # for debugging
    time.sleep(.1)
    self.stream.feed(os.read(self.fdread, 1024))
    for i in range(self.screen.lines):
      print(i, '|', *(self.screen.buffer[i][j].data for j in range(self.screen.columns)), '|', i, sep='', file=self.stdout)

  def test_output(self):
    with stickybar.activate(lambda running: 'my bar'):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', 'my bar')
      print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'my bar')
    self.assertScreen(0, 3, 'first line', 'second line', 'my bar')

  def test_scroll(self):
    with stickybar.activate(lambda running: 'my bar'):
      for i in range(10):
        print('line', i)
      self.assertScreen(0, 4, 'line 6', 'line 7', 'line 8', 'line 9', '', 'my bar')
    self.assertScreen(0, 5, 'line 6', 'line 7', 'line 8', 'line 9', 'my bar')

  def test_restore(self):
    with stickybar.activate(lambda running: 'my bar'):
      print('first line')
      print('second line', end='', flush=True)
      self.assertScreen(11, 1, 'first line', 'second line', 'my bar')
    self.assertScreen(0, 2, 'first line', 'my bar')

  def test_callback(self):
    val = 10
    with stickybar.activate(lambda running: 'val={} run={}'.format(val, running)):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', 'val=10 run=True')
      val = 20
      print('second line')
      self.assertScreen(0, 2, 'first line', 'second line', '', 'val=20 run=True')
      val = 30
    self.assertScreen(0, 3, 'first line', 'second line', 'val=30 run=False')

  def test_error(self):
    with stickybar.activate(lambda running: 'val={:.1f}'.format('foo')):
      print('first line')
      self.assertScreen(0, 1, 'first line', '', "callback failed: Unknown format code 'f' for object of type 'str'", error=True)
    self.assertScreen(0, 2, 'first line', "callback failed: Unknown format code 'f' for object of type 'str'", error=True)

  def test_interval(self):
    i = 0
    def bar(running):
      nonlocal i
      i += 1
      return 'my bar'
    if platform.system() == 'Windows':
      with self.assertWarns(RuntimeWarning), stickybar.activate(bar, interval=.1):
        print('first line')
        time.sleep(1)
      self.assertEqual(i, 3)
    else:
      with stickybar.activate(bar, interval=.1):
        print('first line')
        time.sleep(1)
      self.assertGreater(i, 9)
    self.assertScreen(0, 2, 'first line', 'my bar')
