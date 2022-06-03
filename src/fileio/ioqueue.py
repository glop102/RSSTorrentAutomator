from ..serialize import Serializable
from multiprocessing.pool import ThreadPool
from abc import abstractmethod
from typing import List
from uuid import uuid4
from threading import Event
from .exceptions import StopFlagException,UserCancelException
import yaml

class FileIOHandlerInterface(Serializable):
    """
    Common Interface that all IO Jobs inherit
    """
    yaml_tag = u"!FileIOHandlerInterface"
    @abstractmethod
    def __init__(self):
        self.stopFlag = Event()
        self.userCancelFlag = Event()
    @abstractmethod
    def start(self,fileioParent): pass
    @abstractmethod
    def getProcessingPercentage(self) -> float: pass
    @abstractmethod
    def getProcessingStatus(self) -> str:
        "Intended to be a human readable thing - eg '12 items remaining' or '2.6Gb/12.4Gb - 1.2Mbps'"
        pass
    def checkStopFlags(self):
        if self.stopFlag.is_set():
            raise StopFlagException()
        if self.userCancelFlag.is_set():
            raise UserCancelException()
    def cancelProcessing(self):
        self.userCancelFlag.set()

class FileIO(Serializable):
    """
    Please add new jobs via addNewJob() or addNewJobs() so that it gets started instead of simply queued.
    If you really do want to simply queue the job, then you can append it to currentJobs, but there is no mechanism to detect queded items to start them later.
    """
    yaml_tag = u"!FileIO"
    def __init__(self,currentJobs:dict=None,failedJobs:dict=None,failedJobReasons:dict=None,numberSimultaneous:int=1,hosts:dict=None,autosaveFilename:str=None):
        self.currentJobs = currentJobs or {}
        self.failedJobs = failedJobs or {}
        self.failedJobReasons = failedJobReasons or {}
        self.numberSimultaneous = numberSimultaneous  #how many current jobs to allow to run at the same time
        self.hosts = hosts or {}
        self.autosaveFilename = autosaveFilename

        self.__pool = ThreadPool(self.numberSimultaneous)
        self.__start_jobs()
    def __repr__(self):
        return "{name}(Current={}, Failed={}, Threads={}, Hosts={}, autosave={})".format(self.__class__.__name__,len(self.currentJobs),len(self.failedJobs),self.numberSimultaneous,len(self.hosts),self.autosaveFilename)
    def __del__(self):
        self.stopQueue()
        

    def __jobStartWrapperFactory(self,uuid):
        def __jobStartWrapper(job):
            try: # return the UUID to let us know who just finished processing
                job.start(self)
                return uuid
            except Exception as e: #attach the UUID to any exception that happens
                e.uuid = uuid
                raise e
        return __jobStartWrapper
    def __start_jobs(self) -> None:
        for uuid in self.currentJobs:
            self.__pool.apply_async(
                self.__jobStartWrapperFactory(uuid),
                [self.currentJobs[uuid]],
                callback=self.__processing_success,
                error_callback=self.__processing_failure
            )
    def __processing_success(self,async_result) -> None:
        # The result is simply the UUID of the job
        if not async_result in self.currentJobs:
            print("Error: FileIO had a job complete but we do not know who it was.")
            print("The returned result that is supposed to be a UUID was {}".format(async_result))
            return
        del self.currentJobs[async_result]

        if self.autosaveFilename:
            self.saveQueue()
    def __processing_failure(self,exception_thrown) -> None:
        # figure out who just finished
        # remove them from the curent job queue
        # add them to the failed job queue
        # attach the error to the job for debugging later
        uuid = exception_thrown.uuid
        del exception_thrown.uuid
        if not uuid in self.currentJobs:
            print("Error: FileIO had a job throw an exception but we do not know who it was.")
            print(exception_thrown)
            return
        if type(exception_thrown) is StopFlagException:
            return #the queue is just shutting down, no need to worry about this
        job = self.currentJobs[uuid]
        del self.currentJobs[uuid]
        self.failedJobs[uuid] = job
        self.failedJobReasons[uuid] = exception_thrown

        if self.autosaveFilename:
            self.saveQueue()

    def changeJobPoolSize(self, numberSimultaneous) -> None:
        self.stopQueue()
        self.numberSimultaneous = numberSimultaneous
        self.__pool = ThreadPool(self.numberSimultaneous)
        self.__start_jobs()
    
    def addNewJob(self,job) -> str:
        uuid = str(uuid4())
        self.__pool.apply_async(
            self.__jobStartWrapperFactory(uuid),
            [job],
            callback=self.__processing_success,
            error_callback=self.__processing_failure
        )
        self.currentJobs[uuid] = job

        if self.autosaveFilename:
            self.saveQueue()
        return uuid
    def addNewJobs(self,jobs) -> List[str]:
        uuids = []
        for job in jobs:
            uuid = str(uuid4())
            self.__pool.apply_async(
                self.__jobStartWrapperFactory(uuid),
                [job],
                callback=self.__processing_success,
                error_callback=self.__processing_failure
            )
            self.currentJobs[uuid] = job
            uuids.append(uuid)

        if self.autosaveFilename:
            self.saveQueue()
        return uuids

    def stopQueue(self) -> None:
        """This stops the processing queue permantly. You can serialize the data after it has been stopped, but a new object must be made to have a valid queue again."""
        for key in self.currentJobs:
            job=self.currentJobs[key]
            job.stopFlag.set()
        self.__pool.close()
        self.__pool.join()
    def saveQueue(self,filename:str=None) -> None:
        if filename == None:
            filename = self.autosaveFilename
        if filename == None:
            print("Warning: {} asked to save but there is no available filename to save to".format(self.__class__.__name__))
            return
        f = open(filename,"w")
        yaml.dump(self,f)