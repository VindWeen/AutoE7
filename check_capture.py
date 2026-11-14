import time
import app
from window_capture import WindowCapture
matches = [(t,h) for t,h in app.windows() if t == 'Epic Seven']
assert matches, 'Game window not found'
hwnd = matches[0][1]
capture = WindowCapture()
try:
    capture.start(hwnd)
    deadline = time.monotonic() + 8
    count = 0
    last = None
    while time.monotonic() < deadline:
        l,t,r,b = app.bounds(hwnd)
        frame = capture.poll(hwnd,r-l,b-t)
        if frame is not None:
            count += 1
            last = frame
        time.sleep(.2)
    assert last is not None, 'No frames'
    print('Capture OK:', last.shape, 'polls:', count, 'std:', round(float(last.std()),2))
    gray = app.cv2.cvtColor(app.cv2.resize(last,(1280,720)),app.cv2.COLOR_RGB2GRAY)
    detector = app.App.__new__(app.App)
    detector.templates = {}
    rules = app.json.loads((app.ROOT/'scenarios.json').read_text(encoding='utf-8-sig'))['Đi Map']
    print('Ready score:', round(detector.detect(gray,next(r for r in rules if r['id']=='ready')),3))
finally:
    capture.close()
    time.sleep(.5)
