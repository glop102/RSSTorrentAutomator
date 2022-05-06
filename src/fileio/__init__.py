import yaml
from .ioqueue import IOQueue

class FileIO():
    """Mostly servers as a data container that is serializable."""
    yaml_tag = u"!FileIO"
    yaml_loader = yaml.SafeLoader #whitelist it for being allowed to be parsed with the safe loader
    def __init__(self,hosts=[],ioqueue=None):
        self.hosts = hosts
        self.ioqueue = ioqueue