from time import sleep
import threading

from .taskprogress import TaskProgress
from .exceptions import *

taskType = "debug"

"""
read the behavior from "behaviorType"
Implemented Behaviors:
- failValidation
- throwExceptionValidating
- throwExceptionProcessing
- processInstantly
- process1Second
- process5Seconds
- process30Seconds
- process15Seconds4Times
- raiseStopFlagException
- raiseConnectionException
- raiseNoInternetException
To Be Implemented
"""

def validate(hosts:dict,item:dict):
    if not "behaviorType" in item:
        return "No behavior specified for this debug object"
    if item["behaviorType"] == "failValidation":
        return "Debug object failing validation as expected"
    if item["behaviorType"] == "throwExceptionValidating":
        raise Exception("Debug Exception raised in validate()")
    return None

def process(hosts:dict,item:dict,stopFlag:threading.Event):
    TaskProgress.reset()
    print("Debug Item Processing : "+item["behaviorType"])
    if item["behaviorType"] == "throwExceptionProcessing":
        raise Exception("Debug Exception raised in process()")
    if item["behaviorType"] == "processInstantly":
        print("\t Debug Done")
        return
    if item["behaviorType"] == "process1Second":
        sleep(1)
        TaskProgress.reportPercentage(1)
        print("\t Debug Done")
        return
    if item["behaviorType"] == "process5Seconds":
        for x in range(5):
            TaskProgress.reportPercentage(x/5.0)
            sleep(1.0)
        TaskProgress.reportPercentage(1.0)
        print("\t Debug Done")
        return
    if item["behaviorType"] == "process30Seconds":
        for x in range(30):
            TaskProgress.reportPercentage(x/30.0)
            sleep(1.0)
        TaskProgress.reportPercentage(1.0)
        print("\t Debug Done")
        return
    if item["behaviorType"] == "process15Seconds4Times":
        for y in range(4):
            for x in range(15):
                TaskProgress.reportPercentage(x/15.0)
                sleep(1.0)
            print("\t Did Iteration")
        TaskProgress.reportPercentage(1.0)
        print("\t Debug Done")
        return
    if item["behaviorType"] == "raiseStopFlagException":
        stopFlag.set()
        raise DownloadStopFlagException()
    if item["behaviorType"] == "raiseConnectionException":
        raise ConnectionException()
    print("=== DEBUG ERROR ===")
    print("Unknown Behavior specified and so we reached the end of processing")