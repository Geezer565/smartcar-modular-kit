# Project origin and attribution

_Independent educational implementation · 2026-11-06_

## Context

The maintainer studied the high-level separation of responsibilities in a team
smart-car system: perception, navigation, motion, mission flow, communication and
hardware. The maintainer does not claim authorship of that team's code.

This repository was newly written for a general educational toolkit, with AI
assistance. No source files, names of internal task states, device-specific wire
formats, training data, weights, images, calibration, private addresses or team
documentation were imported from those repositories. Previous repositories were
not modified to create this project.

This is a statement about this project's development process, not a claim of a
formal independent legal audit or a clean-room certification. General algorithm
ideas are credited below; they are not presented as new inventions.

## Public algorithm references

- Pure pursuit: R. Craig Coulter, CMU-RI-TR-92-01 (1992),
  [original publication page](https://publications.ri.cmu.edu/implementation-of-the-pure-pursuit-path-tracking-algorithm)
- A*: a standard graph search method; this repository implements a compact grid variant
- CRC-16: calculated with Python's standard-library `binascii.crc_hqx`, initial
  value `0xffff`; [official API](https://docs.python.org/3.13/library/binascii.html#binascii.crc_hqx)

No external library source, driver or report is vendored. The core uses Python's
standard library. The GitHub workflow uses separately licensed GitHub Actions
without including their source in this repository.

## Authorship wording

Accurate description: “A newly written, AI-assisted mobile robot learning toolkit
maintained by Geezer565, with modular planning, control and software simulation.”

Do not describe this as the team's final competition software, a competition
award-winning implementation, a physical vehicle already validated in the field,
or an independently invented planning/control algorithm.

## License scope

The root MIT license covers new source, documentation and artwork supplied here.
It does not change rights to any prior team work or third-party component. New
contributions must be yours to submit and compatible with that license.
