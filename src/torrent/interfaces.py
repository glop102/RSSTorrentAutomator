from abc import abstractmethod,ABC
from typing import List,Union

class TorrentFile(ABC):
    @property
    @abstractmethod
    def absolutePath(self) -> str: pass
    @property
    @abstractmethod
    def relativePath(self) -> str: pass
    @property
    @abstractmethod
    def downloadProgress(self) -> float: pass
    @property
    @abstractmethod
    def completed(self) -> bool: pass
    @property
    @abstractmethod
    def bytesTotal(self) -> int: pass
    @property
    def totalSize(self) -> int: return self.bytesTotal

class Torrent(ABC):
    @abstractmethod
    def start(self) -> None: pass
    @abstractmethod
    def stop(self) -> None: pass

    # Read Only Properties
    @property
    @abstractmethod
    def id(self) -> str: pass
    @property
    @abstractmethod
    def name(self) -> str: pass
    @property
    @abstractmethod
    def downloadProgress(self) -> float: pass
    @property
    @abstractmethod
    def seedRatio(self) -> float: pass
    @property
    @abstractmethod
    def files(self) -> List[TorrentFile]: pass
    @property
    @abstractmethod
    def completed(self) -> bool: pass
    @property
    @abstractmethod
    def active(self) -> bool: pass
    @property
    @abstractmethod
    def bytesDone(self) -> int: pass
    @property
    @abstractmethod
    def bytesLeft(self) -> int: pass
    @property
    @abstractmethod
    def bytesTotal(self) -> int: pass
    @property
    def totalSize(self)->int: return self.bytesTotal
    @property
    @abstractmethod
    def downloadRate(self) -> int: pass
    @property
    @abstractmethod
    def uploadRate(self) -> int: pass
    @property
    @abstractmethod
    def isFullTorrent(self) -> bool: pass #if this is a temp magnet link torrent waiting on peers or is a proper torrent that all the other fields are vaild for

    # Read/Write properties
    @abstractmethod
    def getLabel(self) -> str: pass
    @abstractmethod
    def setLabel(self,new_label:str) -> None: pass
    label = property(getLabel,setLabel)
    @abstractmethod
    def getSavePath(self) -> str: pass
    @abstractmethod
    def setSavePath(self, path:str) -> None: pass
    savePath = property(getSavePath,setSavePath)

class TorrentServer(ABC):
    @abstractmethod
    def getTorrentList(self) -> List[Torrent]: pass
    @abstractmethod
    def addNewTorrent_URL(self, url:str) -> Torrent: pass
    @abstractmethod
    def addNewTorrent_data(self, data:Union[bytes,str]) -> Torrent: pass
    @abstractmethod
    def removeTorrent(self, torrent:Union[str,Torrent]) -> None: pass
