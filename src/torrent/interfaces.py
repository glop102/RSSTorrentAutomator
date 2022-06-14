from abc import abstractmethod,ABC
from typing import List,Union

class TorrentFile(ABC):
    @property
    @abstractmethod
    def absolutePath(self) -> str:
        """The full path on the remote server to the file."""
        pass
    @property
    @abstractmethod
    def relativePath(self) -> str:
        """The relative path of the file to the save location of the torrent."""
        pass
    @property
    @abstractmethod
    def downloadProgress(self) -> float:
        """Percentage of how much of this file has been downloaded."""
        pass
    @property
    @abstractmethod
    def completed(self) -> bool:
        """Boolean of if the file is finished downloading."""
        pass
    @property
    @abstractmethod
    def bytesTotal(self) -> int:
        """Total number of bytes for the size of the file."""
        pass
    @property
    def totalSize(self) -> int:
        """Total number of bytes for the size of the file."""
        return self.bytesTotal

class Torrent(ABC):
    @abstractmethod
    def start(self) -> None:
        """Start the torrent processing/downloading. Safe to call repeatedly."""
        pass
    @abstractmethod
    def stop(self) -> None:
        """Stop the torrent processing/downloading. Safe to call repeatedly."""
        pass

    # Read Only Properties
    @property
    @abstractmethod
    def id(self) -> str:
        """Implementation specific ID to refer to this torrent. Consistent across the lifetime of the torrent, including reboots. Handy to use for repeatedly tracking a specific torrent."""
        pass
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the torrent in the client."""
        pass
    @property
    @abstractmethod
    def downloadProgress(self) -> float:
        """Percentage of the torrent download complete."""
        pass
    @property
    @abstractmethod
    def seedRatio(self) -> float:
        """Ratio of how much has been uploaded compared to how much was downloaded/"""
        pass
    @property
    @abstractmethod
    def files(self) -> List[TorrentFile]:
        """A list of TorrentFile objects that this torrent will/has downloaded."""
        pass
    @property
    @abstractmethod
    def completed(self) -> bool:
        """Boolean of if the torrent has finished downloading."""
        pass
    @property
    @abstractmethod
    def active(self) -> bool:
        """Boolean of if the torrent is still downloading or uploading/seeding."""
        pass
    @property
    @abstractmethod
    def bytesDone(self) -> int:
        """Number of bytes that have finished downloading."""
        pass
    @property
    @abstractmethod
    def bytesLeft(self) -> int:
        """Number of bytes left to finish downloading."""
        pass
    @property
    @abstractmethod
    def bytesTotal(self) -> int:
        """Total number of bytes for this torrent when downloaded."""
        pass
    @property
    def totalSize(self)->int:
        """Total number of bytes for this torrent when downloaded."""
        return self.bytesTotal
    @property
    @abstractmethod
    def downloadRate(self) -> int:
        """Speed that the torrent is downloading at in bytes per second."""
        pass
    @property
    @abstractmethod
    def uploadRate(self) -> int:
        """Speed that the torrent is uploading/seeding at in bytes per second."""
        pass
    @property
    @abstractmethod
    def isFullTorrent(self) -> bool:
        """Boolean of if this is a proper full torrent or a temporary placeholder torrent. Magnet links are started as temporary torrents that get replaced with a normal one after it recieves some peers."""
        pass

    # Read/Write properties
    @abstractmethod
    def getLabel(self) -> str: pass
    @abstractmethod
    def setLabel(self,new_label:str) -> None: pass
    label = property(getLabel,setLabel,doc="A singular label for the client to keep track of. Useful for categorizing things.")
    @abstractmethod
    def getSavePath(self) -> str: pass
    @abstractmethod
    def setSavePath(self, path:str) -> None: pass
    savePath = property(getSavePath,setSavePath,doc="What path the client will save the contents of a torrent to. Changing this will make the client move the currently downloaded items to the new locaiton.")

class TorrentServer(ABC):
    @abstractmethod
    def getTorrentList(self) -> List[Torrent]:
        """Returns a list of torrents in the client."""
        pass
    @abstractmethod
    def addNewTorrent_URL(self, url:str) -> Torrent:
        """Add a new torrent to the client. The url may be a magnet link."""
        pass
    @abstractmethod
    def addNewTorrent_data(self, data:Union[bytes,str]) -> Torrent:
        """Add a new torrent to the client. It may be either the raw data of a torrent file or a torrent file that is byte64 encoded."""
        pass
    @abstractmethod
    def removeTorrent(self, torrent:Union[str,Torrent]) -> None:
        """Removes a torrent from a client. This will leave the files in place, meaning you have to do the cleanup elsewhere."""
        pass
