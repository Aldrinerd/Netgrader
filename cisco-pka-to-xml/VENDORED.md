# Vendored copy

This directory is a vendored copy of
[jeamxn/cisco-pka-to-xml](https://github.com/jeamxn/cisco-pka-to-xml)
at upstream commit `efe407c`, used by `src/pkt_parser.py` to decrypt
Packet Tracer `.pkt`/`.pka` files.

It is committed rather than installed so that a lab computer with no
internet access still reads `.pkt` files.

## Local change

`pka2xml/libtwofish.dll` is committed here (upstream ignores it). It is
the 64-bit Windows build of `vendor/twofish`, made with
`python build_libtwofish.py`, so lab PCs need no C compiler. It needs
64-bit Python. On Linux or macOS, run `python build_libtwofish.py` once
to produce `libtwofish.so` / `libtwofish.dylib`.

## Licenses

- pka2xml: MIT, see `LICENSE`
- Twofish implementation: BSD 3-Clause (Keybase), see `vendor/twofish/LICENSE`

## Updating

Copy the new upstream tree over this directory (without its `.git`),
rebuild the DLL, update the commit above, and run `python -m pytest`.
