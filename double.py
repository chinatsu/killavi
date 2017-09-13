import killavi

a = killavi.Base("sample.avi")
meta = []
count = 1
for frame in a.frames:
    if frame.is_deltaframe() or frame.is_audioframe():
        if count <= 50:
            count += 0.1111
        for x in range(0, int(count)):
            meta.append(frame.as_meta())
    else:
        meta.append(frame.as_meta())
a.frames.meta = meta
a.frames.remove_keyframes()
a.frames.overwrite(a.frames.as_temp())
a.output('double.avi')
