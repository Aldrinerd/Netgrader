# Contributing to cisco-pka-to-xml

Thanks for taking the time to contribute! This document is a long-form version of the "Contributing" section in [README.md](./README.md). Read whichever you prefer — they say the same things.

## TL;DR

```bash
# 1. fork on GitHub, then:
git clone https://github.com/<your-user>/cisco-pka-to-xml.git
cd cisco-pka-to-xml
git remote add upstream https://github.com/jeamxn/cisco-pka-to-xml.git
git checkout -b feat/my-thing

# 2. build + test
python build_libtwofish.py
python tests/test_roundtrip.py

# 3. commit + push + PR
git commit -am "feat(cli): add --quiet flag"
git push -u origin feat/my-thing
```

## Issue reports

A good `.pka`-cannot-be-decoded issue includes:

- Packet Tracer version that produced the file (top-left of the PT title bar).
- The exact `PkaError` message and a stack trace.
- The first 32 bytes of the file as hex (`xxd -l 32 yourfile.pka`).
- The output of `python build_libtwofish.py` so we know your compiler + OS.

If you can attach a small sample `.pka` that fails, do — make sure it does not contain personal data (device names, real IPs).

## Style

- Plain Python 3.8+, four-space indent, PEP 8.
- Type hints on new public functions.
- snake_case names, `PascalCase` for classes.
- Keep imports sorted: stdlib, third-party (none, ideally), local.
- Comment intent, not mechanics. Reference the relevant stage of the decryption pipeline when changing crypto code.

## Commit messages

We loosely follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add encode subcommand
fix(eax): correct CTR counter wraparound on 32-byte plaintext
docs(readme): document Windows build
chore: bump test KAT vectors
```

PRs are squash-merged; the final squash message comes from the PR title and body, so write those carefully.

## Pull request checklist

- [ ] `python build_libtwofish.py` succeeds on Linux.
- [ ] `python tests/test_roundtrip.py` passes.
- [ ] New public APIs have docstrings.
- [ ] No new third-party Python dependencies.
- [ ] No personal `.pka` files committed.
- [ ] README updated for user-visible changes.

## What we will not merge

- Anything that adds a Python runtime dependency we could implement in ~30 lines of stdlib.
- Features whose only purpose is bypassing Packet Tracer's grading or licensing system.
- Non-trivial logic changes without tests.

## Security

Please use GitHub's private "Report a vulnerability" flow under the Security tab. Do not open a public issue for sensitive findings.

## Code of conduct

Be kind. Assume good faith. Disagreement is fine; personal attacks are not. We follow the spirit of the [Contributor Covenant](https://www.contributor-covenant.org/).
