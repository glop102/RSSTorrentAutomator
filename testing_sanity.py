import yaml
import time
from src import torrent


server = torrent.RTorrentServer("rtorrentURLHere")
torrents = server.getTorrentList()
for t in [torrents[1]]:
    print(t.name)
    print(t.id)
    print(t.savePath)
    print(t.active)
    print(t.completed)
    print(t.bytesDone)
    print(t.bytesLeft)
    print(t.bytesTotal)
    print(t.totalSize)
    original_label = t.label
    print(original_label)
    t.label = "Example Label"
    print(t.label)
    t.label = original_label
    print(t.isFullTorrent)
    print(t.downloadProgress)

    print()
    files = t.files
    for f in files:
        print(f.absolutePath)
        print("\t"+f.relativePath)
        print("\t"+str(f.downloadProgress))
        print("\t"+str(f.completed))
        print("\t"+str(f.bytesTotal))