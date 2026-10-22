#!/usr/bin/env python3
"""Build a SWEETXNU payload with a stub "kernel" (bring-up test, not for iOS).

The shim only needs flat segments, so this packs any raw blob + an ADT without
touching Mach-O fixups. Usage:

  mkstub_payload.py --stub STUB.bin --adt ADT --out PAYLOAD [--phys 0xB0000000]
                    [--virt 0xB0000000] [--mem 0x9800000] [--cmdline "..."]

Payload layout (little endian, offsets from payload start):
  0x000 magic "SWEETXNU"   0x008 u32 version, nsegs
  0x010 u64 virt_base      0x018 u64 entry_va
  0x020 u64 adt_off        0x028 u64 adt_size
  0x030 u64 kernel_end_va  0x038 u64 phys_base   0x040 u64 mem_size
  0x048 char cmdline[608]
  0x2a8 seg[nsegs] { u64 vmaddr, vmsize, file_off, file_size }   # 32 bytes each
  (then the segment data, then the ADT)

Keep phys_base below 0x200000000: the shim's MMU maps the first 8 GiB as Device
and leaves the rest unmapped.
"""
import argparse, struct

ap = argparse.ArgumentParser()
ap.add_argument('--stub', required=True)
ap.add_argument('--adt', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--phys', type=lambda s: int(s, 0), default=0xB0000000)
ap.add_argument('--virt', type=lambda s: int(s, 0), default=None)
ap.add_argument('--mem', type=lambda s: int(s, 0), default=0x9800000)
ap.add_argument('--cmdline', default='debug=0xc serial=3 cpus=1 keepsyms=1 -noprogress')
a = ap.parse_args()

stub = open(a.stub, 'rb').read()
adt = open(a.adt, 'rb').read()
phys = a.phys
virt = a.phys if a.virt is None else a.virt
mem = a.mem
entry = virt
kernel_end = virt + 0x1000

SEG = 32
stub_off = (0x2a8 + SEG + 7) & ~7
adt_off = (stub_off + len(stub) + 7) & ~7
body = bytearray(adt_off + len(adt))

body[0:8] = b'SWEETXNU'
struct.pack_into('<II', body, 0x08, 1, 1)              # version, nsegs
struct.pack_into('<Q', body, 0x10, virt)
struct.pack_into('<Q', body, 0x18, entry)
struct.pack_into('<Q', body, 0x20, adt_off)
struct.pack_into('<Q', body, 0x28, len(adt))
struct.pack_into('<Q', body, 0x30, kernel_end)
struct.pack_into('<Q', body, 0x38, phys)
struct.pack_into('<Q', body, 0x40, mem)
cmds = a.cmdline.encode()[:607]
body[0x48:0x48 + len(cmds)] = cmds
struct.pack_into('<QQQQ', body, 0x2a8, virt, 0x1000, stub_off, len(stub))
body[stub_off:stub_off + len(stub)] = stub
body[adt_off:adt_off + len(adt)] = adt

open(a.out, 'wb').write(bytes(body))
print(f'{a.out}: {len(body)} bytes (stub {len(stub)} @0x{stub_off:x}, adt {len(adt)} @0x{adt_off:x}, '
      f'dst=0x{phys:x})')
