from threading import Thread,Event
import traceback
from time import sleep
__downloads_thread = None
__downloads_stop_flag = Event()
__hosts = {}

from .taskqueue import TaskQueue
from . import delete
from . import download
from . import copy
from . import debug
from .web_api import registerEndpoints
from .exceptions import *

"""
Welcome to the Download + others thread.
Currently this handles the following tasks:
 - downloading a file
 - deleting a file
 - copying a file from one location to another
In general, if a file operation that takes a long time needs to be done, adding it here makes sense.

=====
As a user of this thread, you will generally want to import downloads.TaskQueue and use the functions from there.
The main thread will start and stop the download thread here for you so all you need to worry about is adding something
    and then checking back later periodically to see if it is done.

=====
As a programmer/maintainer of this thread, lets talk about the architecture a little.
The Task Queue is mostly a safety shim that has some reentrant locking to let things from any thread make use of this thread.
TaskQueue is where persistent data is generally stored. Look at the bottom of this file for where we serialize settings from.
The main loop function here is where each item in the queue gets dispatched to do its specific work.
If you want to add new functionality
    make your own .py file in this module, import it
    then follow the same structure of the other dispatches in the main loop function
        first call validate() and then process()
    You will also need to add a static method in TaskQueue to allow people to add the work to the queue
To add any new web apis (eg list of items in the queue) add them to the web_api file.
    The registerEndpoints() function is run after the download thread is started.

checklist of adding a new 'download' type
 - make a new .py file for your thing
 - define a taskType string
 - add your setup as a new method in the TaskQueue object
 - make your validate() and process() functions - download.py is a good example of these
 - update TaskProgress as you go through things, most important being the *Count varaiables
    - it is a good idea to call TaskProgress.reset() first thing in your processing function
    - there are some report*() functions already there that might do what you want
"""


def __downloads_thread_main_loop():
    processOptions=[download,delete,copy,debug]
    while not __downloads_stop_flag.is_set():
        if not TaskQueue.waitForWork():
            #slow periodic check for work in the queue
            #unfortunantly python has no way to wait on multiple locks so we have to poll like this
            continue
        
        item = TaskQueue.getNextItem()
        try:
            process = None
            for p in processOptions:
                if item["taskType"] == p.taskType:
                    process = p
                    break
            if process == None:
                reason = "Unknown task type in the download thread : {}".format(item["taskType"])
                TaskQueue.currentTaskFailed(reason , True)
                print("Skipping a download item. "+reason)
                continue

            failureReason = process.validate(__hosts,item)
            if failureReason is not None:
                TaskQueue.currentTaskFailed(failureReason , True)
                print("Failure to process a download/{} item. {}".format(process.taskType,failureReason))
                continue
            process.process(__hosts,item,__downloads_stop_flag)

            #We can assume the processing was successful to get here and so this item is complete
            TaskQueue.removeFrontOfQueue()
            
        except ConnectionException as e:
            print("Issue connecting to remote host '{}'".format(e))
            #technically it failed, so lets mark it. We do not want it to block processing other items that will work.
            TaskQueue.currentTaskFailed(str(e),extended_debug=traceback.format_exc())
            sleep(1.0)
            #TODO Wait on a known good remote location like google to become available again
        except DownloadStopFlagException:
            print("Download Processing was signaled to stop in the middle of an item - exiting now")
        except Exception as e:
            TaskQueue.currentTaskFailed(str(e),extended_debug=traceback.format_exc())
            print("There was an error attempting to run an item in the download thread.")
            print(e)
            print(traceback.format_exc())
    print("Download thread has stopped")

def start(settings:dict):
    global __downloads_thread, __downloads_stop_flag
    __downloads_stop_flag.clear()
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
        
def serializeSettings() -> dict:
    settings = {}
    settings["queue"] = TaskQueue.getQueue()
    settings["failures"] = TaskQueue.getQueueFailures()
    settings["hosts"] = __hosts
    return settings