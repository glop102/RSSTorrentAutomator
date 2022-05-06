from fastapi import FastAPI,status
from fastapi.responses import JSONResponse,HTMLResponse
from pydantic import BaseModel

from .taskqueue import TaskQueue
from .taskprogress import TaskProgress

"""
This is just a collection of functions that act as the web api for this thread.
I had previously thought about not having any GUI functionality available from here and keep it in the main thread,
    but this thread is kind of being used as a prototype layout for plugins that can be dynamically loaded.
"""

class DebugCreationType(BaseModel):
    behaviorType:str
class ProgressStatus(BaseModel):
    currentCount:int = 0
    maxCount:int = 100
    speed:str = "N/A"
    status:str = ""
    percentage:float = 0.0

def registerEndpoints(app:FastAPI):
    @app.get("/downloads/json/queue",tags=["downloads"])
    def get_queue():
        return TaskQueue.getQueue()
    # TODO Make this use a UUIDv4 instead of index
    # @app.get("/downloads/json/queueItem/{itemNumber}",tags=["downloads"])
    # def get_queue_item(itemNumber:int):
    #     """Get a single item from the Download Queue. Indexes start at 0."""
    #     q = TaskQueue.getQueue()
    #     if len(q) <= itemNumber:
    #         return JSONResponse(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, content={"Issue":"The requested item number is larger than the number of items in the queue."})
    #     return q[itemNumber]
    
    @app.get("/downloads/json/failures",tags=["downloads"])
    def get_failure_queue():
        """When an item fails in processing with the normal queue, it will be sent here to wait for a human to come intervene."""
        return TaskQueue.getQueueFailures()
    # TODO Make this use a UUIDv4 instead of index
    # @app.get("/downloads/json/failureItem/{itemNumber}",tags=["downloads"])
    # def get_failure_item(itemNumber:int):
    #     """Get a single item from the Download Queue. Indexes start at 0."""
    #     q = TaskQueue.getQueueFailures()
    #     if len(q) <= itemNumber:
    #         return JSONResponse(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, content={"Issue":"The requested item number is larger than the number of items in the failure queue."})
    #     return q[itemNumber]
    @app.post("/downloads/json/failureRetryAll",tags=["downloads"])
    def retry_all_failures():
        TaskQueue.requeueAllFailedTasks()
        return {}
    @app.post("/downloads/json/failureClearAll",tags=["downloads"])
    def delete_all_failures():
        TaskQueue.deleteAllFailedTasks()
        return {}
    # TODO Make this use a UUIDv4 instead of index
    # @app.post("/downloads/json/failureClear/{itemNum}",tags=["downloads"])
    # def delete_single_failure(itemNum:int):
    #     try:
    #         TaskQueue.deleteFailedTask(itemNum)
    #         return {}
    #     except:
    #         return JSONResponse(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, content={"Issue":"The requested item number is larger than the number of items in the queue."})
    # TODO Make this use a UUIDv4 instead of index
    # @app.post("/downloads/json/failureRetry/{itemNum}",tags=["downloads"])
    # def retry_single_failure(itemNum:int):
    #     try:
    #         TaskQueue.requeueFailedTask(itemNum)
    #         return {}
    #     except:
    #         return JSONResponse(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, content={"Issue":"The requested item number is larger than the number of items in the queue."})

    @app.get("/downloads/json/progress",tags=["downloads"])
    def current_progress() -> ProgressStatus:
        return {
            "currentCount" : TaskProgress.currentCount,
            "maxCount" : TaskProgress.maxCount,
            "speed" : TaskProgress.speed,
            "status" : TaskProgress.status,
            "percentage" : TaskProgress.getPercentage()
        }
    
    @app.post("/downloads/json/addDebugItem",tags=["downloads"])
    def debug_item(request:DebugCreationType):
        TaskQueue.queueDebugItem(request.behaviorType)
        return { "added" : True }

    @app.get("/downloads",tags=["downloads"],response_class=HTMLResponse)
    def status_page():
        #TODO Make this module use paths relative to the module location
        #TODO make this list the whole list of items - failed and queued
        #TODO make this auto-update the progress of items dynamically with some delays
        #TODO add buttons to requeue failed items (the whole list and specific ones)
        #TODO add buttons to delete failed items (the whole list and specific ones)
        return open("threads/downloads/html/status_page.html","r").read()