import killavi
from pprint import pprint

# a = killavi.Base('sample.avi')
# a.set_dimensions(4, 8)
# a.refresh_frames()
# a.output('test.avi')

a = killavi.Base('sample2.avi')
#pprint(a.avi.streams[0])
pprint(a.avi.streams[0]['handler'])
