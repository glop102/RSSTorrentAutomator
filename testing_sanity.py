import yaml
import time
# from src import torrent
from src import fileio


# server = torrent.RTorrentServer("")
# # torrent = server.addNewTorrent_URL("https://example.com/file.torrent",True)
# torrent = server.addNewTorrent_URL('''magnet:?xt=urn:btih:etcetc''')
# time.sleep(2)
# torrent.stop()
# server.removeTorrent(torrent)

queue = fileio.FileIO()
queue.hosts["sftpserver"] = fileio.SFTPServerConfig("","",password="")
downloader = fileio.SFTPDownload("sftpserver","files/","/tmp/")
id = queue.addNewJob(downloader)

# \033[F - go to beginning of the previous line
# \033[2K - clear line
# \033[A - move up a line
verbose = True
prevNumLines = 0
while id in queue.currentJobs:
    status = downloader.getProcessingStatus(verbose)
    unwindLines = "\r"+ ( "\033[2K\033[A"*prevNumLines )
    print(unwindLines + status,end="",flush=True)
    prevNumLines = status.count("\n")
    time.sleep(1)

print()
print(downloader.getProcessingStatus(verbose))