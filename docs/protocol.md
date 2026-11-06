# Example command protocol

_Newly designed for this toolkit · version 1 · little-endian_

## 📦 Frame layout

This is an example binary format, unrelated to any prior team's vehicle firmware.
It can be carried by a byte-stream transport you implement. No serial or network
connection is created by this library.

| Offset | Size | Field | Meaning |
| --- | --- | --- | --- |
| 0 | 2 | Magic | `A5 5A` |
| 2 | 1 | Version | `01` |
| 3 | 1 | Message type | `01` = velocity command |
| 4 | 2 | Sequence | uint16, little-endian |
| 6 | 2 | Payload length | uint16, maximum 512 bytes |
| 8 | N | Payload | Depends on type |
| 8 + N | 2 | CRC | CRC-16/CCITT-FALSE, little-endian |

CRC parameters: polynomial `0x1021`, initial value `0xffff`, no reflection, final
XOR `0x0000`. CRC covers bytes from **version through the end of payload**,
excluding the magic and CRC itself. Python's `binascii.crc_hqx(data, 0xffff)`
implements the required calculation.[^1] The reference check value for
`123456789` is `0x29b1`.

## 🚗 Velocity payload

Type `1` has exactly 8 payload bytes:

| Payload offset | Type | Meaning |
| --- | --- | --- |
| 0 | float32 | Linear speed, m/s; forward positive |
| 4 | float32 | Yaw rate, rad/s; CCW positive |

`read_velocity()` checks message type, payload size and finite values. It does
not apply vehicle speed limits; those belong in the safety gate and receiver.

```python
from smartcar_kit.messages import Velocity
from smartcar_kit.protocol import encode, velocity_frame, StreamDecoder, read_velocity

raw = encode(velocity_frame(Velocity(0.3, -0.2), sequence=1))
decoder = StreamDecoder()
assert decoder.feed(raw[:5]) == []
frames = decoder.feed(raw[5:])
command = read_velocity(frames[0])
```

## 🔄 Stream handling

`StreamDecoder.feed()` supports split headers, split payloads, consecutive
frames, leading noise, invalid versions, invalid lengths and checksum failures.
It searches for the magic again after a malformed frame. Each feed is limited
to 64 KiB; payloads are capped at 512 bytes. A partial valid-length frame remains
buffered until enough bytes arrive. The transport must impose its own read
timeout; the parser does not own a clock or connection.

Unknown message types may decode as generic `Frame` objects. Call the matching
payload parser; do not treat unknown frames as velocity commands. The decoder's
`rejected` counter counts rejected headers/checksums, not every discarded byte.

## 🛑 Receiver responsibilities

Sequence numbers are provided but are not automatically enforced or deduplicated.
The receiver should reject old/replayed commands, apply local speed limits, and
maintain a command timeout using its own receive clock. No remote timestamp is
trusted as an actuator freshness guarantee. Handle uint16 wrap explicitly.

CRC detects accidental corruption; it does not authenticate the sender. The
protocol has no encryption, access control, retransmission, connection handshake
or motor watchdog. Do not expose it directly as a public remote-control service.

[^1]: Python Software Foundation. “binascii.crc_hqx.” https://docs.python.org/3.13/library/binascii.html#binascii.crc_hqx
