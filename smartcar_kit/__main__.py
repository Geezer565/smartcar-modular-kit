"""python -m smartcar_kit demo | protocol-demo"""

import argparse
import json
from pathlib import Path

from .messages import Velocity
from .protocol import StreamDecoder, encode, velocity_frame, read_velocity
from .report import write_report
from .simulation import DemoConfig, simulate


def main():
    parser = argparse.ArgumentParser(description='SmartCar Kit: modular mobile robot software demo')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='run a deterministic software simulation')
    demo.add_argument('--scenario', choices=['normal', 'estop', 'stale', 'obstacle'], default='normal')
    demo.add_argument('--config', type=Path)
    demo.add_argument('--output', type=Path, default=Path('outputs/demo'))
    commands.add_parser('protocol-demo', help='encode, fragment and decode a command in memory')
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            result = simulate(args.scenario, DemoConfig.load(args.config))
            write_report(result, args.output)
            print(json.dumps(result['summary'], indent=2))
            print(f'Replay: {args.output.resolve() / "replay.html"}')
            return 0 if result['summary']['success'] else 1
        command = Velocity(.3, -.2)
        raw = encode(velocity_frame(command, 1))
        decoder = StreamDecoder()
        assert decoder.feed(raw[:5]) == []
        decoded = read_velocity(decoder.feed(raw[5:])[0])
        print(f'frame: {raw.hex(" ")}')
        print(f'decoded: speed={decoded.speed:.3f} m/s, yaw_rate={decoded.yaw_rate:.3f} rad/s')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'Error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
