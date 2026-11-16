# PC collision fixes

The reported SA-MP 0.3.DL-R1 crash address `0x0041B1D4` is inside the collision
stream reader's entry. The original GTA instruction at `0x41B1D0` is six bytes:
`64 A1 00 00 00 00` (`mov eax, fs:[0]`). ExtendedVeh previously installed an
inline MinHook jump there.

The local official 0.3.DL-R1 `samp.dll` writes `C3` to `0x41B1D0` while loading
custom models and restores only the first byte to `64`. The relevant writes
are at DLL RVAs `B1B6C`, `B1B84`, `B1BEC`, and `B1C2A`. Restoring that byte over
an inline jump leaves the jump's displacement bytes in the native instruction.
The DLL's ASLR load address does not change this GTA address.

ExtendedVeh now registers its five-argument reader with RenderWare after RW
initialization and restores the native reader before RW shutdown. It never
patches `0x41B1D0`. Normal streams delegate to the original reader; custom DFFs
still skip this native reader and load embedded/separate collision through the
existing collision loader. The standard writer and size callbacks are retained.

Two separate collision-selection errors are also corrected:

- GTA's special per-vehicle collision takes priority, as in the original
  `CEntity::GetColModel` (hydraulics/moving components).
- Once a vehicle's custom collision is registered, temporarily masking its
  wheel-line count to zero does not switch its body back to the base model.
  GTA masks this count inside collision/detachment tests.

Run `python3 tests/test_pc_collision.py` on Linux with a C++20 compiler. It
compiles the actual callback/selection function bodies against simulated engine
calls and checks forwarding, suppression, registration, special collision,
temporary line masking, missing data and unbound vehicles. It does not run GTA.

The user reports the wheel/stuck-exit problem only on PC and confirms it is
separate from the crash. These fixes address confirmed source defects; the
reported stuck-exit reproduction is still needed to establish whether it is
resolved. Claude's unfinished suspension-restoration changes in the original
worktree were preserved and are not included in this branch. The branch starts
from `fix/txd-sanitize` (`6bf6108`), retaining its TXD and custom-bike fixes.
