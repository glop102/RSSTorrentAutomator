from src.processingsteps import ProcessingSteps

class DataGroup:
    """This is the base class that holds all data that is used and processed."""
    #Holds all state
    parent:DataGroup = None
    children:list(DataGroup) = []
    UUID:str = None
    dataTemplate:str = None #name of the data template in use
    processingTemplate:str = None #name of the processing template that will run on this data group
    __data:dict(str,str) = {}
    def start(self):
        """looks up processingSteps and calls start() on it and also all children"""
        #TODO register self with cron if needed - first look up the processing steps and get the interval
        for c in self.children:
            c.start()
    def stop(self):
        """stops the processing steps and calls stop() on all children"""
        if self.__processingSteps:
            self.__processingSteps.stop()
        for c in self.children:
            c.stop()
    def process(self): #called by cron to continue processing
        pass
    def __getitem__(self,key): # gets a matching variable by traversing up the parent tree
        return self.__data[key]
    def __setitem__(self, key, value,local=True):
        """sets the value in this data group if `local` seet to true, else attempt to first update the parent DataGroups before setting it locally"""
        #TODO do the parent lookup for settings
        self.__data[key] = value
    def __delitem__(self,key,local=True):
        #TODO do the parent lookup for deleting
        del self.__data[key]
    def removeChild(self,child): #removes a child object - may be using a UUID or may be the exact DataGroup object - clear the static class cache of the removed entry at the same time
        pass

    __UUIDLookup:dict = {}
    @classmethod
    def getUUID(cls): #return the DataGroup that has the UUID - results may be cached in the dict above or can fall back to traversing the tree of children
        return None