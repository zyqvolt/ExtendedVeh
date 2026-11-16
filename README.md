# ExtendedVeh

A fork of [BrownTurbo/BrownTurbo-ExtendedVeh](https://github.com/BrownTurbo/BrownTurbo-ExtendedVeh) that fixes bugs found while porting the client to SA-MP Mobile X, so the PC and Android clients behave the same.

All original work, design and code belong to [BrownTurbo](https://github.com/BrownTurbo) (John Magdy Lotfy Kamel). This fork only adds fixes on top and keeps the original [BSD 2-Clause License](LICENSE) and copyright notice.

## Changes in this fork
- Custom vehicles use their own SA-MP colors. Before, the first vehicle of a custom model gave its colors to every vehicle of that model.
- Custom vehicles sit on their own wheel dummies, use the collision embedded in their DFF and seat occupants at their own seat dummies.
- The Linux server plugin is built against glibc 2.36 (Debian 12) with a static libstdc++.
- PC collision reading no longer patches the entry that SA-MP 0.3.DL rewrites;
  custom collision selection also preserves GTA's special collision and temporary
  wheel-line masking. See [verification and PC test scope](docs/PC_COLLISION_FIX.md).

## Credits & Acknowledgements
This project is built upon and inspired by [dotSILENT/chandling](https://github.com/dotSILENT/chandling) & [dotSILENT/chandling-svr](https://github.com/dotSILENT/chandling-svr) by [@dotSILENT](https://github.com/dotSILENT), licensed under the BSD 2-Clause License. We are grateful for their foundational work.
