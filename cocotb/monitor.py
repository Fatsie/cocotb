#!/bin/env python

# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Class defining the standard interface for a monitor within a testbench.

The monitor is responsible for watching the pins of the DUT and recreating
the transactions.
"""

from collections import deque

import cocotb
from cocotb.bus import Bus
from cocotb.decorators import coroutine
from cocotb.log import SimLog
from cocotb.result import ReturnValue
from cocotb.triggers import Event, Timer


class MonitorStatistics(object):
    """Wrapper class for storing Monitor statistics"""

    def __init__(self):
        self.received_transactions = 0


class Monitor(object):
    """Base class for Monitor objects.

    Monitors are passive 'listening' objects that monitor pins going in or out of a DUT.
    This class should not be used
    directly, but should be sub-classed and the internal :any:`_monitor_recv` method
    should be overridden and decorated as a :any:`coroutine`.  This :any:`_monitor_recv`
    method should capture some behavior of the pins, form a transaction, and
    pass this transaction to the internal :any:`_recv` method.  The :any:`_monitor_recv`
    method is added to the cocotb scheduler during the ``__init__`` phase, so it
    should not be yielded anywhere.

    The primary use of a Monitor is as an interface for a
    :class:`~cocotb.scoreboard.Scoreboard`.

    Args:
        callback (callable): Callback to be called with each recovered transaction
            as the argument. If the callback isn't used, received transactions will
            be placed on a queue and the event used to notify any consumers.
        event (cocotb.triggers.Event): Event that will be called when a transaction
            is received through the internal :any:`_recv` method.
            `Event.data` is set to the received transaction.
    """

    def __init__(self, **kwargs):
        self._event = kwargs.pop('event', None)
        callback = kwargs.pop('callback', None)
        self._wait_event = Event()
        self._recvQ = deque()
        self._callbacks = []
        self.stats = MonitorStatistics()

        # Sub-classes may already set up logging
        if not hasattr(self, "log"):
            self.log = SimLog("cocotb.monitor.%s" % (self.__class__.__name__))

        if callback is not None:
            self.add_callback(callback)

        # Create an independent coroutine which can receive stuff
        self._thread = cocotb.scheduler.add(self._monitor_recv())

    def kill(self):
        """Kill the monitor coroutine."""
        if self._thread:
            self._thread.kill()
            self._thread = None

    def __len__(self):
        return len(self._recvQ)

    def __getitem__(self, idx):
        return self._recvQ[idx]

    def add_callback(self, callback):
        """Add function as a callback.

        Args:
            callback (callable): The function to call back.
        """
        self.log.debug("Adding callback of function %s to monitor",
                       callback.__name__)
        self._callbacks.append(callback)

    @coroutine
    def wait_for_recv(self, timeout=None):
        """With *timeout*, :meth:`.wait` for transaction to arrive on monitor
        and return its data.

        Args:
            timeout: The timeout value for :class:`~.triggers.Timer`.
                Defaults to ``None``.

        Returns:
            Data of received transaction.
        """
        if timeout:
            t = Timer(timeout)
            fired = yield [self._wait_event.wait(), t]
            if fired is t:
                raise ReturnValue(None)
        else:
            yield self._wait_event.wait()

        pkt = self._wait_event.data
        raise ReturnValue(pkt)

    @coroutine
    def _monitor_recv(self):
        """Actual implementation of the receiver.

        Sub-classes should override this method to implement the actual receive
        routine and call :any:`_recv` with the recovered transaction.
        """
        raise NotImplementedError("Attempt to use base monitor class without "
                                  "providing a ``_monitor_recv`` method")

    def _recv(self, transaction):
        """Common handling of a received transaction."""

        self.stats.received_transactions += 1

        # either callback based consumer
        for callback in self._callbacks:
            callback(transaction)

        # Or queued with a notification
        if not self._callbacks:
            self._recvQ.append(transaction)

        if self._event is not None:
            self._event.set(data=transaction)

        # If anyone was waiting then let them know
        if self._wait_event is not None:
            self._wait_event.set(data=transaction)
            self._wait_event.clear()


class BusMonitor(Monitor):
    """Wrapper providing common functionality for monitoring buses."""
    _signals = []
    _optional_signals = []

    def __init__(self, **kwargs):
        callback = kwargs.pop('callback', None)
        event = kwargs.pop('event', None)

        self._reset = kwargs.pop('reset', None)
        self._reset_n = kwargs.pop('reset_n', None)
        self.clock = kwargs.pop('clock')
        self.bus = Bus(
            signals=self._signals, optional_signals=self._optional_signals,
            **kwargs
        )
        self.log = SimLog("cocotb.{}.{}".format(self.__class__.__name__, str(self.bus)))

        Monitor.__init__(self, callback=callback, event=event)

    @property
    def in_reset(self):
        """Boolean flag showing whether the bus is in reset state or not."""
        if self._reset_n is not None:
            return not bool(self._reset_n.value.integer)
        if self._reset is not None:
            return bool(self._reset.value.integer)
        return False

    def __str__(self):
        return str(self.bus) + "_monitor"

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.bus)