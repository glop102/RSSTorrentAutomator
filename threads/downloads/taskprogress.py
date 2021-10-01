import time
from threading import RLock

class TaskProgress:
    """
    A simple container struct that is directly modified by whatever item is processing.
    Please only read these variables if you are not the processing item to prevent confusion.

    If you use one of the report*() functions, please call reset() before the first use so that it will set things such as timeStart correctly.
    """
    #A time stamp object created when the processing item starts.
    timeStart:time.time=None
    #Counter Variables that track the progress of the item. eg for file downloads, it could be number of bytes or chunks.
    currentCount:int=0
    maxCount:int=0
    #The calculated speed by the processing item. This may not be implemented by all processing items.
    speed:str="N/A"
    #Sometimes it is helpful to give a little bit more information of some sort
    status:str=""

    __editlock = RLock()

    @classmethod
    def reset(cls) -> None:
        """Set all the varaibles to their default values"""
        with cls.__editlock:
            cls.timeStart=None
            cls.currentCount=0
            cls.maxCount=0
            cls.speed="N/A"
            cls.status=""

            #hidden vars used for reporting progress
            cls.__prev_bytes=0
            cls.__prev_time=None
    @classmethod
    def getPercentage(cls) -> float:
        """Returns a number between 0 and 1 as a float. It is calculated off of currentCount and maxCount"""
        if cls.maxCount != 0:
            return float(cls.currentCount)/cls.maxCount
        return 1.0
    
    #=============================================================================
    #  Allow Reporting some common cases
    #=============================================================================
    __prev_bytes:int=0
    __prev_time:time.time=None
    @staticmethod
    def __human_readable_bytes(nbytes:int) -> str:
        suffix=["B","KB","MB","GB","TB"]
        magnitude = 0
        while nbytes>1000:
            nbytes=nbytes/1000
            magnitude=magnitude+1
        nbytes = int(nbytes*10.0)/10.0 # limit to 1 decimal point
        return str(nbytes)+" "+suffix[magnitude]
    @classmethod
    def reportFileProgress(cls,currentBytes:int,totalBytes:int) -> None:
        with cls.__editlock:
            #if this is the first report, then set up some basic variables
            if cls.status == "" or cls.__prev_time == None:
                cls.status = "Filesize : " + cls.__human_readable_bytes(totalBytes)
                cls.maxCount = totalBytes
                cls.timeStart = time.time()
                cls.__prev_time = cls.timeStart
                return
            now = time.time()
            elapsed_time = now - cls.__prev_time
            if elapsed_time < 1:
                return #only bother updating the progress every second
            cls.speed = cls.__human_readable_bytes(
                float(currentBytes-cls.__prev_bytes) / elapsed_time
                )+"/s"
            cls.currentCount = currentBytes
            #progress report over, so save current progress
            cls.__prev_time = now
            cls.__prev_bytes = currentBytes
    @classmethod
    def reportPercentage(cls,percentage:float):
        """Percentage should be a float between 0 and 1"""
        with cls.__editlock:
            now = time.time()
            if cls.timeStart == None:
                cls.timeStart = now
                cls.currentCount = int(100*percentage)
                cls.maxCount = 100
                cls.status = "ETA: Unknown"
                return

            cls.currentCount = int(100*percentage)
            if cls.currentCount > 0:
                timePerPercent = (now-cls.timeStart)/cls.currentCount
                timeLeft = (cls.maxCount-cls.currentCount) * timePerPercent
                cls.status = "ETA: {} seconds".format(int(timeLeft))
