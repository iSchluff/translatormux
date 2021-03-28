#!/usr/bin/env python3
from . import mumble, muxer
import time
from gi.repository import GLib


def start(mumbleChannels, config):
    streammuxer = muxer.Muxer(len(mumbleChannels), config["src"], config["dst"])
    for (num, channel) in enumerate(mumbleChannels):
        mumble.MumbleReceiver(num, channel, config["mumble"], streammuxer)

    loop = GLib.MainLoop()

    try:
        loop.run()
    except KeyboardInterrupt:
        pass

    streammuxer.stop()