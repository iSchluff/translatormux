#!/usr/bin/env python3
import os
import random
import string
import sys
import time
import threading
import logging

from array import array

from pymumble_py3 import Mumble

log = logging.getLogger("mumble")


class MumbleReceiver:
    def __init__(self, num, channel, config, mux):
        self.num = num
        self.muxer = mux
        server = config["address"]
        nick = config.get("nick", "mux-{r}")
        debug = config.get("debug", False)

        # def __init__(self, server, channel, nick='recv-{r}@{channel}', debug=False):
        r = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.channelname = channel
        self.nick = nick.format(r=r, channel=channel)
        print("connect mumble", server, self.nick)
        self.mumble = Mumble(server, self.nick, password="somepassword", debug=debug)
        self.mumble.set_application_string("Receiver for Channel {}".format(channel))

        self.rate = 48000
        self.interval = 0.02  # 20ms of samples

        self.mumble.set_receive_sound(1)
        self.mumble.start()
        self.mumble.is_ready()

        self.channel = self.mumble.channels.find_by_name(self.channelname)
        self.channel.move_in()

        self.thread = None
        self.start()

    def start(self):
        self.thread = threading.Thread(target=self.send, daemon=True)
        self.thread.start()

    def stop(self):
        self.thread.join()

    def clip(self, val):
        return -32768 if val < -32768 else 32767 if val > 32767 else val

    def send(self):
        ts = time.time() - self.interval
        while True:
            start = time.time()
            buffer = array("h", [0] * int(self.interval * self.rate))
            for user in self.channel.get_users():
                samples = array("h")
                while len(samples) < len(buffer):
                    sound = user.sound.get_sound(self.interval)
                    if not sound:
                        # print(f"not enough samples: {len(samples)} < {len(buffer)}", file=sys.stderr)
                        break
                    samples.frombytes(sound.pcm)
                if sys.byteorder == "big":
                    samples.byteswap()
                for i in range(0, len(samples)):
                    buffer[i] = self.clip(buffer[i] + samples[i])
            if sys.byteorder == "big":
                buffer.byteswap()

            self.muxer.push_audio(self.num, buffer)

            wait = self.interval * 1 - (time.time() - start)
            if wait > 0:
                time.sleep(wait)
            # while time.time() < ts:  # spin until time is reached
            #     pass