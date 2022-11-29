import os
import re

import yaml


class Config(object):
    """A class that wraps access to the given YAML schema file."""

    def __init__(self):
        self._schema = None
        self.schema_file = None

    @property
    def schema(self):
        """
        Return the schema loaded from the given YAML schema file.

        :return: The parsed YAML schema.
        :rtype: dict
        """
        if self._schema is None and self.schema_file is not None:
            self._schema = load_schema(self.schema_file)
        return self._schema


def load_schema(schema_file):
    # Original code from here https://gist.github.com/mkaranasou/ba83e25c835a8f7629e34dd7ede01931
    tag = '!ENV'
    pattern = re.compile(r'.*?\${(\w+)}.*?')
    custom_loader = yaml.FullLoader
    custom_loader.add_implicit_resolver(tag, pattern, None)

    def constructor_env_variables(loader, node):
        """
        Extract the environment variable from the node's value.

        :param yaml.Loader loader: The yaml loader
        :param node: The current node in the yaml
        :return: The parsed string that contains the value of the environment variable
        """
        value = loader.construct_scalar(node)
        match = pattern.findall(value)  # to find all env variables in line
        if match:
            full_value = value
            for g in match:
                full_value = full_value.replace(
                    '${{{g}}}'.format(g=g), os.environ.get(g, g)
                )
            return full_value
        return value

    custom_loader.add_constructor(tag, constructor_env_variables)
    return yaml.load(open(schema_file), Loader=custom_loader)


config = Config()
