# -*- coding: utf-8 -*-
'''
    salt.utils.yamldumper
    ~~~~~~~~~~~~~~~~~~~~~

'''
# pylint: disable=W0232
#         class has no __init__ method

from __future__ import absolute_import
try:
    from yaml import CDumper as Dumper
    from yaml import CSafeDumper as SafeDumper
except ImportError:
    from yaml import Dumper
    from yaml import SafeDumper

from salt.utils.odict import OrderedDict


class OrderedDumper(Dumper):  # pylint: disable=W0232
    '''
    A YAML dumper that represents python OrderedDict as simple YAML map.
    '''


class SafeOrderedDumper(SafeDumper):  # pylint: disable=W0232
    '''
    A YAML safe dumper that represents python OrderedDict as simple YAML map.
    '''


def represent_ordereddict(dumper, data):
    return dumper.represent_dict(data.items())


OrderedDumper.add_representer(OrderedDict, represent_ordereddict)  # pylint: disable=E1101
SafeOrderedDumper.add_representer(OrderedDict, represent_ordereddict)  # pylint: disable=E1101
