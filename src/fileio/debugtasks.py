import time
from .ioqueue import FileIO,FileIOHandlerInterface

class Debug10SDelay(FileIOHandlerInterface):
    yaml_tag = u"!Debug10SDelay"
    def __init__(self):
        super().__init__()
        self.timeLeft=10
    def start(self,fileioParent:FileIO):
        while(self.timeLeft>0):
            print(self.timeLeft)
            self.checkStopFlags()
            time.sleep(1)
            self.timeLeft = self.timeLeft - 1
        print("Debug10SDelay Finished")
    def getProcessingPercentage(self)->float:
        """Returns a number between 0 and 1 as a float. It is calculated off of currentCount and maxCount"""
        return (10.0-self.timeLeft)/100.0
    def getProcessingStatus(self)-> str:
        return "{} seconds left".format(self.timeLeft)
class Debug10SDelayFail(FileIOHandlerInterface):
    yaml_tag = u"!Debug10SDelayFailure"
    def __init__(self):
        super().__init__()
        self.timeLeft=10
    def start(self,fileioParent:FileIO):
        while(self.timeLeft>0):
            print(self.timeLeft)
            self.checkStopFlags()
            time.sleep(1)
            self.timeLeft = self.timeLeft - 1
        print("Debug10SDelayFail Finished")
        raise Exception("Intended Failure Debug")
    def getProcessingPercentage(self)->float:
        """Returns a number between 0 and 1 as a float. It is calculated off of currentCount and maxCount"""
        return (10.0-self.timeLeft)/100.0
    def getProcessingStatus(self)-> str:
        return "{} seconds left".format(self.timeLeft)
