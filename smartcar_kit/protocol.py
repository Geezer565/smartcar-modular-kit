"""New example wire protocol. It is unrelated to any original vehicle protocol."""

import binascii
from dataclasses import dataclass
import struct

from .messages import Velocity

MAGIC = b'\xa5\x5a'
HEADER = struct.Struct('<2sBBHH')
CRC = struct.Struct('<H')
COMMAND = struct.Struct('<ff')
MAX_PAYLOAD = 512
VELOCITY_TYPE = 1


@dataclass(frozen=True)
class Frame:
    message_type: int
    sequence: int
    payload: bytes


def encode(frame: Frame) -> bytes:
    if type(frame.message_type) is not int or not 0 <= frame.message_type <= 255:
        raise ValueError('message type must fit uint8')
    if type(frame.sequence) is not int or not 0 <= frame.sequence <= 65535:
        raise ValueError('sequence must fit uint16')
    if not isinstance(frame.payload, bytes) or len(frame.payload) > MAX_PAYLOAD:
        raise ValueError('payload must be bytes of length <= 512')
    body = HEADER.pack(MAGIC, 1, frame.message_type, frame.sequence, len(frame.payload)) + frame.payload
    return body + CRC.pack(binascii.crc_hqx(body[2:], 0xffff))


class StreamDecoder:
    def __init__(self):
        self.buffer = bytearray()
        self.rejected = 0

    def feed(self, chunk: bytes) -> list[Frame]:
        if len(chunk) > 65536:
            raise ValueError('feed at most 64 KiB at a time')
        self.buffer.extend(chunk)
        frames = []
        while True:
            start = self.buffer.find(MAGIC)
            if start < 0:
                self.buffer[:] = self.buffer[-1:] if self.buffer[-1:] == MAGIC[:1] else b''
                break
            del self.buffer[:start]
            if len(self.buffer) < HEADER.size:
                break
            _, version, message_type, sequence, size = HEADER.unpack_from(self.buffer)
            if version != 1 or size > MAX_PAYLOAD:
                del self.buffer[0]
                self.rejected += 1
                continue
            length = HEADER.size + size + CRC.size
            if len(self.buffer) < length:
                break
            expected, = CRC.unpack_from(self.buffer, length - CRC.size)
            actual = binascii.crc_hqx(self.buffer[2:length - CRC.size], 0xffff)
            if actual != expected:
                del self.buffer[0]
                self.rejected += 1
                continue
            frames.append(Frame(message_type, sequence, bytes(self.buffer[HEADER.size:length - CRC.size])))
            del self.buffer[:length]
        return frames


def velocity_frame(command: Velocity, sequence: int) -> Frame:
    try:
        payload = COMMAND.pack(command.speed, command.yaw_rate)
    except (OverflowError, struct.error) as error:
        raise ValueError('velocity cannot be represented as float32') from error
    return Frame(VELOCITY_TYPE, sequence, payload)


def read_velocity(frame: Frame) -> Velocity:
    if frame.message_type != VELOCITY_TYPE or len(frame.payload) != COMMAND.size:
        raise ValueError('expected a velocity frame with an 8-byte payload')
    return Velocity(*COMMAND.unpack(frame.payload))
