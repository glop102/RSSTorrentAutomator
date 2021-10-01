from time import sleep
from threading import RLock
from copy import deepcopy

from . import delete
from . import download
from . import copy
from . import debug

class TaskQueue:
    """
    Simple class to handle threading issues of adding/removing files from the queue.
    Essentially this will act as the API to the rest of the world.
    """
    __queue = []
    __queueFailures = []
    __editlock = RLock()
    @classmethod
    def __addItem(cls,item:dict,priority:bool=False):
        with cls.__editlock:
            if priority:
                #Put it near the front of the queue
                #We put in not in index 0 since we assume 0 is currently being processed
                cls.__queue.insert(1,item)
            else:
                cls.__queue.append(item)

    @classmethod
    def getNextItem(cls) -> dict:
        with cls.__editlock:
            return deepcopy(cls.__queue[0])
    @classmethod
    def getQueue(cls) -> list[dict]:
        with cls.__editlock:
            return deepcopy(cls.__queue)
    @classmethod
    def getQueueFailures(cls) -> list[dict]:
        with cls.__editlock:
            return deepcopy(cls.__queueFailures)
    @classmethod
    def queueLength(cls) -> int:
        with cls.__editlock:
            return len(cls.__queue)
    @classmethod
    def waitForWork(cls) -> bool:
        if cls.queueLength() == 0:
            sleep(2.0)
            return False
        else:
            with cls.__editlock: #do not try grabbing more work while the queue is being edited
                return True
    @classmethod
    def restoreTasks(cls,queue:list[dict]=None,failures:list[dict]=None) -> None:
        with cls.__editlock:
            if queue is not None: cls.__queue = queue
            if failures is not None: cls.__queueFailures = failures
    @classmethod
    def removeFrontOfQueue(cls) -> None:
        with cls.__editlock:
            del cls.__queue[0]
    @classmethod
    def currentTaskFailed(cls,reason="unknown",forceFailure=False,extended_debug="") -> None:
        """Will attempt to intelligently try the task again. After it fails 3 times, it will stop retrying and move it to the failure queue. Every failure report will move the task to the end of the queue to not block others."""
        with cls.__editlock:
            item = cls.__queue[0]
            del cls.__queue[0]
            if not "fail count" in item:
                item["fail count"] = 1
            else:
                item["fail count"] = item["fail count"] + 1
            
            if item["fail count"] == 3 or forceFailure:
                item["reason"] = reason
                item["extended_debug"] = extended_debug
                cls.__queueFailures.append(item)
            else:
                cls.__addItem(item)
    @classmethod
    def requeueFailedTask(cls,index:int) -> None:
        """Move a failed task from the failure queue to the work queue to try again."""
        with cls.__editlock:
            item = cls.__queueFailures[index]
            del cls.__queueFailures[index]
            if "fail count" in item:
                del item["fail count"]
            if "reason" in item:
                del item["reason"]
            if "extended_debug" in item:
                del item["extended_debug"]
            cls.__addItem(item)
    @classmethod
    def requeueAllFailedTasks(cls) -> None:
        """Move all failed tasks to the work queue to try them all again."""
        with cls.__editlock:
            for item in cls.__queueFailures:
                if "fail count" in item:
                    del item["fail count"]
                if "reason" in item:
                    del item["reason"]
                cls.__addItem(item)
            cls.__queueFailures.clear()
    @classmethod
    def deleteAllFailedTasks(cls) -> None:
        with cls.__editlock:
            cls.__queueFailures.clear()
    @classmethod
    def deleteFailedTask(cls,index:int) -> None:
        with cls.__editlock:
            del cls.__queueFailures[index]
    @classmethod
    def countQueuedItemsWithTrackingId(cls,groupTrackingID:str) -> int:
        """This will count how many items have a particular tracking ID. Note: Will not count items without a tracking ID."""
        count = 0
        with cls.__editlock:
            for item in cls.__queue + cls.__queueFailures:
                if "groupTrackingID" in item and item["groupTrackingID"] == groupTrackingID:
                    count = count + 1
        return count
    @classmethod
    def queueContainsTrackingId(cls,groupTrackingID:str) -> bool:
        """Returns True/False if there are any items in the queue that have a particular tracking ID"""
        with cls.__editlock:
            for item in cls.__queue + cls.__queueFailures:
                if "groupTrackingID" in item and item["groupTrackingID"] == groupTrackingID:
                    return True
        return False
    #======================================================================================================
    #  Adding Items to the Queue
    #======================================================================================================
    @classmethod
    def queueForDownload(cls,remoteHost:str,remoteLocation:str,localLocation:str,groupTrackingID:str=None,priority:bool=False) -> None:
        """
        This will add a file to the queue to be downloaded. Unknown results for trying to download a folder.
        remoteHost is the name of the configured host to download from.
        the location inputs are obvious.
        groupTrackingID is an optional to associate some external reference with this item to know if it is finished. Multiple items may use the same ID.
        priority is a True/False to mark if it should be added to the front of the queue or the back.
        """
        newItem = {
            "taskType":download.taskType,
            "host":remoteHost,
            "remoteLocation":remoteLocation,
            "localLocation":localLocation
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        cls.__addItem(newItem,priority)
    @classmethod
    def queueForLocalCopy(cls,source:str,destination:str,groupTrackingID:str=None,priority:bool=False) -> None:
        newItem = {
            "taskType":copy.taskType,
            "source":source,
            "destination":destination
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        cls.__addItem(newItem,priority)
    @classmethod
    def queueForRemoteDeletion(cls,remoteHost:str,remoteLocation:str,groupTrackingID:str=None,priority:bool=False) -> None:
        newItem = {
            "taskType":delete.taskType,
            "host":remoteHost,
            "remoteLocation":remoteLocation
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        cls.__addItem(newItem,priority)
    @classmethod
    def queueDebugItem(cls,behaviorType:str,groupTrackingID:str=None,priority:bool=False) -> None:
        newItem = {
            "taskType" : debug.taskType,
            "host" : "This is debug, so no host",
            "behaviorType" : behaviorType
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        cls.__addItem(newItem,priority)