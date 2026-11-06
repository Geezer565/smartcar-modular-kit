"""Optional browser check using an installed Chromium-family browser."""

import argparse
from pathlib import Path
import subprocess


CHECK = '''<script>
try {
  slider.value = rows.length - 1;
  slider.dispatchEvent(new Event('input'));
  if (!stats.textContent.includes('completed')) throw new Error('seek did not reach final state');
  play.click();
  if (play.textContent !== '暂停') throw new Error('play toggle failed');
  document.getElementById('restart').click();
  if (+slider.value !== 0) throw new Error('restart failed');
  play.click();
  if (play.textContent !== '播放') throw new Error('pause toggle failed');
  document.body.setAttribute('data-replay-check', 'passed');
} catch (error) {
  document.body.setAttribute('data-replay-check', String(error));
}
</script>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / 'outputs/demo/replay.html'
    destination = root / 'outputs/replay-check'
    destination.mkdir(exist_ok=True)
    fixture = destination / 'check.html'
    fixture.write_text(source.read_text(encoding='utf-8').replace('</html>', CHECK + '</html>'), encoding='utf-8')
    run = subprocess.run([
        str(args.browser), '--headless=new', '--disable-gpu', '--no-first-run',
        '--disable-extensions', '--disable-background-networking', '--disable-sync',
        '--no-default-browser-check', f'--user-data-dir={destination / "profile"}',
        '--dump-dom', '--virtual-time-budget=500', fixture.as_uri(),
    ], capture_output=True, timeout=40)
    if b'data-replay-check="passed"' not in run.stdout:
        print('Replay control check failed; inspect outputs/replay-check/check.html')
        return 1
    print('Replay controls OK: seek, play, restart and pause.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
