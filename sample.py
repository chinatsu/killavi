import killavi

if __name__ == '__main__':
    a = killavi.Base('sample.avi') # load a file named sample.avi
    meta = [] # a list to store metadata (frame order, basically)
    for idx, _ in enumerate(a.frames): # iterate over every frame
        if idx+35 > len(a.frames):
            break # break the loop if the index is 35 frames away from the end
        for x in range(idx, idx+35):
            meta.append(a.frames[x].as_meta()) # append frames with a lookahead of 35 frames
    a.frames.meta = meta # insert our new metadata!
    a.frames.remove_keyframes() # remove the keyframes
    io = a.frames.as_temp() # build the bytestream
    a.frames.overwrite(io) # overwrite the Frames instance with the new shit
    a.output('sample2.avi') # output the things
