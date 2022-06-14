from .interfaces import TorrentServer,Torrent,TorrentFile
from typing import List,Union
from time import sleep
import xmlrpc.client
import urllib.request
import inspect
#https://docs.python.org/3/library/xmlrpc.client.html#module-xmlrpc.client
#https://rtorrent-docs.readthedocs.io/en/latest/cmd-ref.html#download-items-and-attributes

class RTorrentFile(TorrentFile):
    def __init__(self,__server,__id:str):
        self.__server = __server
        self.__id = __id #format of <TORRENT ID>:f<FILE INDEX>
    @property
    def absolutePath(self) -> str:
        return self.__server.proxy.f.frozen_path(self.__id)
    @property
    def relativePath(self) -> str:
        return self.__server.proxy.f.path(self.__id)
    @property
    def downloadProgress(self) -> float:
        total = self.__server.proxy.f.size_chunks(self.__id)
        completed = self.__server.proxy.f.completed_chunks(self.__id)
        return float(completed)/total
    @property
    def completed(self) -> bool:
        total = self.__server.proxy.f.size_chunks(self.__id)
        completed = self.__server.proxy.f.completed_chunks(self.__id)
        return total == completed
    @property
    def bytesTotal(self) -> int:
        return self.__server.proxy.f.size_bytes(self.__id)

class RTorrent(Torrent): 
    def __init__(self,__server,__id:str):
        self.__server = __server
        self.__id = __id
    
    def start(self) -> None:
        self.__server.proxy.d.start(self.__id)
    def stop(self) -> None:
        self.__server.proxy.d.stop(self.__id)

    # Read Only Properties
    @property
    def id(self) -> str:
        return self.__id
    @property
    def name(self) -> str:
        return self.__server.proxy.d.name(self.__id)
    @property
    def downloadProgress(self) -> float:
        return float(self.bytesDone)/self.bytesTotal
    @property
    def seedRatio(self) -> float:
        return int(self.__server.proxy.d.ratio(self.__id))/1000.0
    @property
    def files(self) -> List[RTorrentFile]:
        num_files = self.__server.proxy.d.size_files(self.__id)
        return [RTorrentFile(self.__server,self.__id+":f"+str(idx)) for idx in range(num_files)]
    @property
    def completed(self) -> bool:
        return bool(self.__server.proxy.d.complete(self.__id))
    @property
    def active(self) -> bool:
        return bool(self.__server.proxy.d.is_active(self.__id))
    @property
    def bytesDone(self) -> int:
        return int(self.__server.proxy.d.completed_bytes(self.__id))
    @property
    def bytesLeft(self) -> int:
        return int(self.__server.proxy.d.left_bytes(self.__id))
    @property
    def bytesTotal(self) -> int:
        return int(self.__server.proxy.d.size_bytes(self.__id))
    @property
    def downloadRate(self) -> int:
        return int(self.__server.proxy.d.down.rate(self.__id))
    @property
    def uploadRate(self) -> int:
        return int(self.__server.proxy.d.up.rate(self.__id))
    @property
    def isFullTorrent(self) -> bool:
        return not bool(self.__server.proxy.d.is_meta(self.__id))

    # Read/Write properties
    def getLabel(self) -> str:
        return self.__server.proxy.d.custom1(self.__id)
    def setLabel(self,new_label:str) -> None:
        return self.__server.proxy.d.custom1.set(self.__id,new_label)
    label = property(getLabel,setLabel)
    def getSavePath(self) -> str: 
        return self.__server.proxy.d.directory(self.__id)
    def setSavePath(self, path:str) -> None:
        return self.__server.proxy.d.directory.set(self.__id,path)
    savePath = property(getSavePath,setSavePath)

class RTorrentServer(TorrentServer):
    def __init__(self,url:str):
        """Pass in the URL to control rTorrent. If you are connecting through ruTorrent, it often will be https://example.com/xmlrpc. Give account credentials as username:password@example.com if required."""
        self.proxy = xmlrpc.client.ServerProxy(url)
    def getTorrentList(self) -> List[Torrent]:
        hashes = self.proxy.download_list()
        ts = []
        for h in hashes:
            ts.append(RTorrent(self,h))
        return ts
    def addNewTorrent_URL(self, url:str, downloadLocal:bool = False) -> Torrent:
        """This has an extra parameter of downloadLocal. IF set to true, instead of passing a URL to the torrent client, we will instead download the URL and pass the data to the client."""
        if(url.startswith("magnet") or downloadLocal == False):
            #just the most basic situation of letting the client handle the URL
            preIDs = self.proxy.download_list()
            self.proxy.load.start("",url) # the empty first param is required
            newIDs = []
            while len(newIDs) == 0:
                sleep(0.5)
                newIDs = [ id for id in self.proxy.download_list() if id not in preIDs ]
            if len(newIDs) > 1:
                raise Exception("There were more than 1 new IDs after adding the torrent URL {}".format(url))
            return RTorrent(self,newIDs[0])
        # else we have been asked to download the URL and send the raw file to the client
        return self.addNewTorrent_data(urllib.request.urlopen(url).read())
    def addNewTorrent_data(self, data:Union[bytes,str]) -> Torrent:
        preIDs = self.proxy.download_list()
        self.proxy.load.raw_start("",data) # the empty first param is required
        newIDs = []
        while len(newIDs) == 0:
            sleep(0.5)
            newIDs = [ id for id in self.proxy.download_list() if id not in preIDs ]
        if len(newIDs) > 1:
            raise Exception("There were more than 1 new IDs after adding torrent data ({})".format(type(data)))
        return RTorrent(self,newIDs[0])
    def removeTorrent(self, torrent:Union[str,Torrent]) -> None:
        if Torrent in inspect.getmro(type(torrent)):
            torrent = torrent.id
        self.proxy.d.erase(torrent)