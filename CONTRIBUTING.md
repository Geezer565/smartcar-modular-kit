# Contributing

_Keep modules small, examples runnable, and claims measurable._

## 🧩 Development

Use Python 3.11+ and work from the repository root:

```bash
python -m unittest discover -s tests -v
python tools/check_repository.py
python -m smartcar_kit demo --output outputs/demo
```

The core has no third-party runtime dependency. Avoid adding heavy dependencies
for a small helper. Optional hardware integrations should be separate adapters
and should not prevent the base demo from running.

## 🧪 A useful change

- State the problem and new behavior
- Add a focused check for a new control or protection behavior
- Include a runnable example for a new adapter
- Explain units, frames, acquisition time and error behavior
- Distinguish simulated, loopback and physical-hardware results

## 📚 Rights and attribution

Only submit material you have the right to contribute under the project's MIT
license. Do not submit team-private code, data, device credentials, copied drivers
or model weights without the necessary rights. Credit published algorithms and
retain any applicable third-party notices. Disclose substantial AI assistance in
the change description so reviewers understand the development process.

## 🚗 Hardware evidence

Hardware contributions should document device model, firmware version, units,
calibration assumptions and actual test conditions. Do not mark physical behavior
as verified based only on a software test, compilation or a successful connection.
