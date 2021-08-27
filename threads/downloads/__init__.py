from threading import Thread,Event
__downloads_thread = None
__downloads_stop_flag = Event()
__hosts = {}

from .taskqueue import TaskQueue
from . import delete
from . import download
from . import copy


def __downloads_thread_main_loop():
    while not __downloads_stop_flag.is_set():
        if not TaskQueue.waitForWork():
            #slow periodic check for work in the queue
            #unfortunantly python has no way to wait on multiple locks so we have to poll like this
            continue
        
        item = TaskQueue.getNextItem()
        try:
            if item["taskType"] == download.taskType:
                failureReason = download.validate(__hosts,item)
                if failureReason is not None:
                    TaskQueue.currentTaskFailed(failureReason , True)
                    print("Failure to download an item. "+failureReason)
                    continue
                download.process(__hosts,item)
            elif item["taskType"] == delete.taskType:
                failureReason = delete.validate(__hosts,item) #reason = "Remote Delete Host \"{}\" is not known.".format(item["host"])
                if failureReason is not None:
                    TaskQueue.currentTaskFailed(failureReason , True)
                    print("Failure to delete a remote item. "+failureReason)
                    continue
                delete.process(__hosts,item)
            elif item["taskType"] == copy.taskType:
                #TODO
                pass
            else:
                reason = "Unknown task type in the download thread : {}".format(item["taskType"])
                TaskQueue.currentTaskFailed(reason , True)
                print("Skipping a download item. "+reason)
                continue
            
            #We can assume the processing was successful to get here and so this item is complete
            TaskQueue.removeFrontOfQueue()
        except Exception as e:
            TaskQueue.currentTaskFailed(str(e))
            print("There was an error attempting to run an item in the download thread.")
            print(e)

def start(settings):
    global __downloads_thread, __downloads_stop_flag
    __downloads_thread = Thread(target=__downloads_thread_main_loop)
    __downloads_thread.daemon = True  #exit the program even if this thread has not stopped yet
    __downloads_thread.start()

    queue = None
    failures = None
    if "queue" in settings and type(settings["queue"]) == list:
        queue = settings["queue"]
    if "failures" in settings and type(settings["failures"]) == list:
        failures = settings["failures"]
    TaskQueue.restoreTasks(queue,failures)

    if "hosts" in settings and type(settings["hosts"]) == dict:
        global __hosts
        __hosts = settings["hosts"]
def stop():
    global __downloads_thread, __downloads_stop_flag
    __downloads_stop_flag.set()
    __downloads_thread.join(timeout=3.0)
    if __downloads_thread.is_alive():
        print("Warning: the download thread has refused to stop. killing thread...")
        #since we mark the thread as a daemon, it is killed automatically when the main thread exits so nothing more is needed to be called
        
def serializeSettings():
    settings = {}
    settings["queue"] = TaskQueue.getQueue()
    settings["failures"] = TaskQueue.getQueueFailures()
    settings["hosts"] = __hosts
    return settings