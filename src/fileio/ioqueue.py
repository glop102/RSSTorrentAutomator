import yaml
from multiprocessing import Pool

class IOQueue(yaml.YAMLObject):
    """
    Please add new jobs via addNewJob() or addNewJobs() so that it gets started instead of simply queued.
    If you really do want to simply queue the job, then you can append it to currentJobs, but there is no mechanism to detect queded items to start them later.
    """
    yaml_tag = u"!IOQueue"
    yaml_loader = yaml.SafeLoader #whitelist it for being allowed to be parsed with the safe loader
    def __init__(self,currentJobs=[],failedJobs=[],numberSimultaneous=1):
        self.currentJobs = currentJobs
        self.failedJobs = failedJobs
        self.numberSimultaneous = numberSimultaneous  #how many current jobs to allow to run at the same time
        self.__pool = Pool(self.numberSimultaneous)
        self.__start_jobs()
    def __repr__(self):
        return "{name}(Current={}, Failed={}, Threads={})".format(self.__class__.__name__,len(self.currentJobs),len(self.failedJobs),self.numberSimultaneous)
    def __del__(self):
        self.__pool.terminate()
        self.__pool.join()

    def __start_jobs(self):
        self.__pool.map_async(
            lambda jobItem : jobItem.start(),
            self.currentJobs,
            callback=self.__processing_success,
            error_callback=self.__processing_failure
        )
    def __processing_success(self,async_result):
        print(async_result,type(async_result))
        # figure out who just finished
        # remove them from the curent job queue
    def __processing_failure(self,exception_thrown):
        print(exception_thrown,type(exception_thrown))
        # figure out who just finished
        # remove them from the curent job queue
        # add them to the failed job queue
        # attach the error to the job for debugging latter
        #Probably need to have an ErrorMessage object in the __init__ of jobs so debugging problesm is persistent
        # - make it a string because we have no idea what weird erros things like paramiko might throw

    def changeJobPoolSize(self, numberSimultaneous):
        self.__pool.terminate()
        self.__pool.join()
        self.numberSimultaneous = numberSimultaneous
        self.__pool = Pool(self.numberSimultaneous)
        self.__start_jobs()
    
    def addNewJob(self,job):
        self.currentJobs.append(job)
        self.__pool.apply_async(
            lambda jobItem : jobItem.start(),
            [job],
            callback=self.__processing_success,
            error_callback=self.__processing_failure
        )
    def addNewJobs(self,jobs):
        self.currentJobs.extend(jobs)
        self.__pool.map_async(
            lambda jobItem : jobItem.start(),
            jobs,
            callback=self.__processing_success,
            error_callback=self.__processing_failure
        )