from time import sleep
from threading import RLock

from . import delete
from . import download
from . import copy

class TaskQueue:
    """
    Simple class to handle threading issues of adding/removing files from the queue.
    Essentially this will act as the API to the rest of the world.
    """
    __queue = []
    __queueFailures = []
    __editlock = RLock()
    @staticmethod
    def __addItem(item,priority=False):
        with TaskQueue.__editlock:
            if priority:
                #Put it near the front of the queue
                #We put in not in index 0 since we assume 0 is currently being processed
                TaskQueue.__queue.insert(1,item)
            else:
                TaskQueue.__queue.append(item)

    @staticmethod
    def getNextItem(): return TaskQueue.__queue[0]
    @staticmethod
    def getQueue(): return TaskQueue.__queue
    @staticmethod
    def getQueueFailures(): return TaskQueue.__queueFailures
    @staticmethod
    def queueLength(): return len(TaskQueue.__queue)
    @staticmethod
    def waitForWork():
        if TaskQueue.queueLength() == 0:
            sleep(2.0)
            return False
        else:
            with TaskQueue.__editlock: #do not try grabbing more work while the queue is being edited
                return True
    @staticmethod
    def restoreTasks(queue=None,failures=None):
        with TaskQueue.__editlock:
            if queue is not None: TaskQueue.__queue = queue
            if failures is not None: TaskQueue.__queueFailures = failures
    @staticmethod
    def removeFrontOfQueue():
        with TaskQueue.__editlock:
            del TaskQueue.__queue[0]
    @staticmethod
    def currentTaskFailed(reason="unknown",forceFailure=False):
        """Will attempt to intelligently try the task again. After it fails 3 times, it will stop retrying and move it to the failure queue."""
        with TaskQueue.__editlock:
            item = TaskQueue.__queue[0]
            del TaskQueue.__queue[0]
            if not "fail count" in item:
                item["fail count"] = 1
            else:
                item["fail count"] = item["fail count"] + 1
            
            if item["fail count"] == 3 or forceFailure:
                item["reason"] = reason
                TaskQueue.__queueFailures.append(item)
            else:
                TaskQueue.__addItem(item)
    @staticmethod
    def requeueFailedTask(index):
        """Move a failed task from the failure queue to the work queue to try again."""
        with TaskQueue.__editlock:
            item = TaskQueue.__queueFailures[index]
            del TaskQueue.__queueFailures[index]
            if "fail count" in item:
                del item["fail count"]
            if "reason" in item:
                del item["reason"]
            TaskQueue.__addItem(item)
    @staticmethod
    def requeueAllFailedTasks():
        """Move all failed tasks to the work queue to try them all again."""
        with TaskQueue.__editlock:
            for item in TaskQueue.__queueFailures:
                if "fail count" in item:
                    del item["fail count"]
                if "reason" in item:
                    del item["reason"]
                TaskQueue.__addItem(item)
            TaskQueue.__queueFailures.clear()
    @staticmethod
    def deleteAllFailedTasks():
        with TaskQueue.__editlock:
            TaskQueue.__queueFailures.clear()
    @staticmethod
    def queueForDownload(remoteHost,remoteLocation,localLocation,groupTrackingID=None,priority=False):
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
        TaskQueue.__addItem(newItem,priority)
    @staticmethod
    def queueForLocalCopy(source,destination,groupTrackingID=None,priority=False):
        newItem = {
            "taskType":copy.taskType,
            "source":source,
            "destination":destination
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        TaskQueue.__addItem(newItem,priority)
    @staticmethod
    def queueForRemoteDeletion(remoteHost,remoteLocation,groupTrackingID=None,priority=False):
        newItem = {
            "taskType":delete.taskType,
            "host":remoteHost,
            "remoteLocation":remoteLocation
        }
        if groupTrackingID is not None:
            newItem["groupTrackingID"] = groupTrackingID
        TaskQueue.__addItem(newItem,priority)
    @staticmethod
    def countQueuedItemsWithTrackingId(groupTrackingID):
        """This will count how many items have a particular tracking ID. Note: Will not count items without a tracking ID."""
        count = 0
        with TaskQueue.__editlock:
            for item in TaskQueue.__queue + TaskQueue.__queueFailures:
                if "groupTrackingID" in item and item["groupTrackingID"] == groupTrackingID:
                    count = count + 1
        return count
    @staticmethod
    def queueContainsPendingTrackingId(groupTrackingID):
        """Returns True/False if there are any items in the queue that have a particular tracking ID"""
        with TaskQueue.__editlock:
            for item in TaskQueue.__queue + TaskQueue.__queueFailures:
                if "groupTrackingID" in item and item["groupTrackingID"] == groupTrackingID:
                    return True
        return False