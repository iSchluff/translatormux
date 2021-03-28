#!/usr/bin/env python3
import time
import threading
import logging
import re
import array

log = logging.getLogger("muxer")

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)


def Demux(name, address):
    pipeline = ""
    if address.startswith("srt://"):
        pipeline += f" srtsrc uri={address} streamid=play/test latency=150"
        pipeline += f" ! tsdemux name={name}" # latency=0
    elif address.startswith("rtmp://"):
        pipeline += f" rtmpsrc location={address} do-timestamp=true"
        pipeline += f" ! identity single-segment=true ! flvdemux name={name}"
    else:
        raise ValueError("Unknown input protocol: " + address)
    return pipeline


def Mux(name, address):
    pipeline = ""
    if address.startswith("srt://"):
        match = re.match("^srt:\/\/(.+?):?(\d+)\??(streamid=(.*)|)$", address)
        if match is None:
            raise ValueError("invalid srt url: " + address)
        (host, port, _, streamid) = match.groups()
        # pipeline += f" mpegtsmux name={name} alignment=7"
        pipeline += f" avmux_mpegts name={name}"
        # pipeline += f" fakesink name={name}"
        pipeline += (
            f" ! srtsink uri=srt://{host}:{port} streamid={streamid} latency=150"
        )
    # only works with webm :(
    elif address.startswith("icecast://"):
        match = re.match("^icecast:\/\/([^:]+):?([^@]+)@?(.+?):?(\d+)$", address)
        if match is None:
            raise ValueError("invalid icecast url: " + address)
        (user, password, host, port) = match.groups()
        if not port:
            port = 8000
        pipeline += f" shout2send name={name} sync=true username={user} password={password} ip={host} port={port}"
    return pipeline


class Muxer(object):
    def __init__(self, numChannels, src, dst):
        self.running = True
        delaySec = 3

        pipeline = Demux("demux", src)
        # pipeline = ""

        # pipeline += " demux.video ! queue ! h264parse ! mux."
        # pipeline += " demux.audio ! queue ! aacparse ! mux."
        # pipeline += f" ! queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 min-threshold-time={delaySec*1e9:d}"
        # pipeline += " ! mux."
        for i in range(numChannels): # max-bytes=96000
            pipeline += f" appsrc name=trans-in{i} emit-signals=false do-timestamp=true is-live=true min-latency=1000 block=true caps=audio/x-raw,rate=48000,channels=1,format=S16LE,layout=interleaved"
            pipeline += " ! queue"
            pipeline += " ! audioconvert"
            pipeline += " ! audioresample"
            pipeline += " ! avenc_aac"
            pipeline += " ! audio/mpeg,rate=48000,channels=2,mpegversion=4"
            pipeline += " ! queue"
            pipeline += " ! mux."

        pipeline += Mux("mux", dst)

        print("pipeline", pipeline)
        self.pipe = Gst.parse_launch(pipeline)

        self.bus = self.pipe.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.handle_message)
        self.bus.enable_sync_message_emission()

        self.audio_inputs = []
        for i in range(numChannels):
            input = self.pipe.get_by_name("trans-in" + str(i))
            input.set_property("format", Gst.Format.TIME)
            self.audio_inputs.append(input)

        self.demux = self.pipe.get_by_name("demux")
        self.demux.connect("pad-added", self.handle_demuxpad)
        self.mux = self.pipe.get_by_name("mux")

        print(self.pipe.set_state(Gst.State.PLAYING))

        self.push_audio(0, array.array("h", [0]))

        # self.lasttime = time.time()
        # self.frames = 0

        # self.push_camera_frames()
        # self.push_presentation_frames()
        # self.push_background_frames()

    def handle_message(self, bus, message):
        print("msg", message.get_structure().to_string())


    # create queues for separating audio/video
    def make_queue(self):
        queue = Gst.ElementFactory.make("queue")
        self.pipe.add(queue)
        queue.sync_state_with_parent()
        return queue

    h264caps = Gst.Caps.from_string("video/x-h264, stream-format=avc")
    aaccaps = Gst.Caps.from_string("audio/mpeg, mpegversion=4, stream-format=raw")

    def handle_demuxpad(self, demuxer, pad):
        pad_caps = pad.query_caps()

        # h264 passthrough
        if pad_caps.is_subset(self.h264caps):
            queue = self.make_queue()
            pad.link(queue.get_static_pad("sink"))

            h264parse = Gst.ElementFactory.make("h264parse")
            self.pipe.add(h264parse)
            h264parse.set_property("config-interval", -1)
            h264parse.sync_state_with_parent()
            res = queue.link(h264parse)
            if not res:
                print("failed to link h264-parse", res)
                return
            res = h264parse.link(self.mux)
            if not res:
                print("failed to link h264-mux")
                return
            print("linked", pad_caps.to_string())
        # elif pad_caps.is_subset(self.aaccaps):
        #     queue = self.make_queue()
        #     pad.link(queue.get_static_pad("sink"))

        #     aacparse = Gst.ElementFactory.make("aacparse")
        #     self.pipe.add(aacparse)
        #     aacparse.sync_state_with_parent()
        #     queue.link(aacparse)

        #     aacdec = Gst.ElementFactory.make("avdec_aac")
        #     self.pipe.add(aacdec)
        #     aacdec.sync_state_with_parent()
        #     aacparse.link(aacdec)

        #     aacenc = Gst.ElementFactory.make("avenc_aac")
        #     self.pipe.add(aacenc)
        #     aacenc.sync_state_with_parent()
        #     aacdec.link(aacenc)

        #     res = aacenc.link(self.mux)
        #     if not res:
        #         print("failed to link aac-mux")
        #         return
        #     print("linked", pad_caps.to_string())
        else:
            print("unknown pad", pad_caps.to_string())
        return True

        # print("pad", dir(self.mux))
        # mux_pad = self.mux.get_compatible_pad(pad)
        # print("mux_pad", mux_pad)
        # if mux_pad is not None:
        #     pad.link(mux_pad)
        #     print("linked!")

    def stop(self):
        self.running = False

    def state(self):
        print(self.pipe.get_state(0))

    # if self.running:
    #     threading.Timer(1, self.push_background_frames).start()
    # self.background_input.emit("push-buffer", self.bgbuffer)

    def push_audio(self, channel, arr):
        buf = Gst.Buffer.new_wrapped(arr.tobytes())
        # buf.pts = 18446744073709551615
        # buf.dts = 18446744073709551615
        if arr[0] > 0:
            print(".", end="", flush=True)
        self.audio_inputs[channel].emit("push-buffer", buf)
