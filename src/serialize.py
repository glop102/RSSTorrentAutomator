import inspect
import yaml


# Forces the YAML representation to only use the variables that are used in the __init__ method to save, and
# then uses those same variables to construct a new object with __init__ instead of directly writing the state
# to the internal __dict__ of the object. This is a more intuitive way of handling state, so that people don't have
# to be mindful of what they store in their object.
# If someone wants their object to store some variable, they just need to add it to their __init__()
# Additionally, all a programmer needs to add in is a yaml_tag = u"!something" to make it distinct for loading.
class Serializable(yaml.YAMLObject):
    __metaclass__ = yaml.YAMLObjectMetaclass
    yaml_loader = yaml.SafeLoader #whitelist it for being allowed to be parsed with the safe loader

    @classmethod
    def to_yaml(cls, dumper, data):
        named_args = inspect.signature(data.__init__).parameters.keys()
        arg_values = []
        for var_name in named_args:
            node_key = dumper.represent_data(var_name)
            node_value = dumper.represent_data(data.__dict__[var_name])
            arg_values.append((node_key, node_value))
        return yaml.nodes.MappingNode('!{0}'.format(data.__class__.__name__), arg_values)


    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=True)
        return cls(**fields)
