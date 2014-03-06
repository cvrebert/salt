# -*- coding: utf-8 -*-
'''
Manage events

This module is used to manage events via RAET
'''

# Import python libs
import logging
import time
from collections import MutableMapping

# Import salt libs
import salt.payload
import salt.loader
import salt.state
import salt.utils.event
from salt.transport.road.raet import stacking
from salt.transport.road.raet import yarding
log = logging.getLogger(__name__)


class SaltEvent(object):
    '''
    The base class used to manage salt events
    '''
    def __init__(self, node, sock_dir=None, **kwargs):
        '''
        Set up the stack and remote yard
        '''
        self.node = node
        self.sock_dir = sock_dir
        self.__prep_stack()

    def __prep_stack(self):
        yid = salt.utils.gen_jid()
        self.stack = stacking.StackUxd(
                yid=yid,
                lanename=self.node,
                dirpath=self.sock_dir)
        self.router_yard = yarding.Yard(
                prefix='master',
                yid=0,
                dirpath=self.sock_dir)
        self.stack.addRemoteYard(self.router_yard)
        route = {'dst': (None, self.router_yard.name, 'event_req'),
                 'src': (None, self.stack.yard.name, None)}
        msg = {'route': route, 'load': {'yid': yid, 'dirpath': self.sock_dir}}
        self.stack.transmit(msg, self.router_yard.name)
        self.stack.serviceAll()

    def subscribe(self, tag=None):
        '''
        Included for compat with zeromq events, not required
        '''
        return

    def unsubscribe(self, tag=None):
        '''
        Included for compat with zeromq events, not required
        '''
        return

    def connect_pub(self):
        '''
        Establish the publish connection
        '''
        return

    def connect_pull(self, timeout=1000):
        '''
        Included for compat with zeromq events, not required
        '''

    @classmethod
    def unpack(cls, raw, serial=None):
        '''
        Included for compat with zeromq events, not required
        '''
        return raw

    def get_event(self, wait=5, tag='', full=False):
        '''
        Get a single publication.
        IF no publication available THEN block for up to wait seconds
        AND either return publication OR None IF no publication available.

        IF wait is 0 then block forever.
        '''
        start = time.time()
        while True:
            self.stack.serviceAll()
            if self.stack.rxMsgs:
                msg = self.stack.rxMsgs.popleft()
                event = msg.get('event', {})
                if 'tag' not in event and 'data' not in event:
                    # Invalid event, how did this get here?
                    continue
                if not event['tag'].startswith(tag):
                    # Not what we are looking for, throw it away
                    continue
                if full:
                    return event
                else:
                    return event['data']
            if start + wait < time.time():
                return None

    def get_event_noblock(self):
        '''
        Get the raw event without blocking or any other niceties
        '''
        self.stack.serviceAll()
        if self.stack.rxMsgs:
            event = self.stack.rxMsgs.popleft()
            if 'tag' not in event and 'data' not in event:
                # Invalid event, how did this get here?
                return None
            return event

    def iter_events(self, tag='', full=False):
        '''
        Creates a generator that continuously listens for events
        '''
        while True:
            data = self.get_event(tag=tag, full=full)
            if data is None:
                continue
            yield data

    def fire_event(self, data, tag, timeout=1000):
        '''
        Send a single event into the publisher with paylod dict "data" and event
        identifier "tag"
        '''
        # Timeout is retained for compat with zeromq events
        if not str(tag):  # no empty tags allowed
            raise ValueError('Empty tag.')

        if not isinstance(data, MutableMapping):  # data must be dict
            raise ValueError('Dict object expected, not "{0!r}".'.format(data))
        route = {'dst': (None, self.router_yard.name, 'event_fire'),
                 'src': (None, self.stack.yard.name, None)}
        msg = {'route': route, 'tag': tag, 'data': data}
        self.stack.transmit(msg)
        self.stack.serviceAll()

    def fire_ret_load(self, load):
        '''
        Fire events based on information in the return load
        '''
        if load.get('retcode') and load.get('fun'):
            # Minion fired a bad retcode, fire an event
            if load['fun'] in salt.utils.event.SUB_EVENT:
                try:
                    for tag, data in load.get('return', {}).items():
                        data['retcode'] = load['retcode']
                        tags = tag.split('_|-')
                        if data.get('result') is False:
                            self.fire_event(
                                    data,
                                    '{0}.{1}'.format(tags[0], tags[-1]))  # old dup event
                            data['jid'] = load['jid']
                            data['id'] = load['id']
                            data['success'] = False
                            data['return'] = 'Error: {0}.{1}'.format(tags[0], tags[-1])
                            data['fun'] = load['fun']
                            data['user'] = load['user']
                            self.fire_event(
                                data,
                                salt.utils.event.tagify([load['jid'],
                                        'sub',
                                        load['id'],
                                        'error',
                                        load['fun']],
                                       'job'))
                except Exception:
                    pass
