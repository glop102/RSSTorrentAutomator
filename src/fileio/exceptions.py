#For when the stop flag of the processing is called. This is often when shutting down the service and is not really an error.
class StopFlagException(Exception): pass
#For when a user asks for a process to stop. We should consider this a failure as it is an abnormal condition.
class UserCancelException(Exception): pass

class UnknownHostException(Exception): pass