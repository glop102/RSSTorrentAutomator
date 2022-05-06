from src.datagroup import DataGroup

class ProcessingSteps:
    #holds no state, only information that comes from the processing template
    periodicProcessing:int = 0 #number of seconds between calls from cron to process
    steps = [] #no idea what format this will end up actually being, just marking it for later
    def start(self): #register self with cron
        pass
    def stop(self):
        pass