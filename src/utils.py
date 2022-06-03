def humanReadableSpeed(speed:float) -> str:
    speedSuffix = ["Bps","KBps","MBps","GBps","TBps"]
    speedIndex = 0
    while(speed > 1000):
        speedIndex += 1
        speed /= 1000
    return "{:3.1f} {}".format(speed,speedSuffix[speedIndex])

def humanReadableFilesize(filesize:int) -> str:
    filesizeSuffix = ["Bytes","KB","MB","GB","TB"]
    filesizeIndex = 0
    while(filesize > 1000):
        filesizeIndex += 1
        filesize /= 1000.0
    return "{:3.1f} {}".format(filesize,filesizeSuffix[filesizeIndex])