# 1-Deck Casino Card → BIP-39 Seed Generator

**Version 2.15 · derivation id `1deck-bip39-v2`**

Turn physically drawn playing cards into a BIP-39 seed phrase, offline, in a single HTML file.

**There is no random number generator anywhere in this tool.** No `Math.random`, no
`crypto.getRandomValues`, no clock reading — not even in the countdown timers. The seed comes from
a deck you shuffled and cards you typed in, and from nothing else. If your shuffle is good, your
seed is good. If it is not, no software can rescue it, and this one does not pretend otherwise.

---

## Verify before you use it

The file is only trustworthy if it is the file that was published. Check the hash **against a copy
published somewhere this repository does not control** — the project site, a signed post, a mirror.

```bash
# Linux
sha256sum 1deck-bip39-v2.15.html

# macOS
shasum -a 256 1deck-bip39-v2.15.html
```
```powershell
# Windows
Get-FileHash -Algorithm SHA256 1deck-bip39-v2.15.html
```

Expected:

```
42e1457b6d986aa6c102a8865483692f6a838234a3bb5393fffe3339e47b37d3
```

Everything else in the repo is listed in [`SHA256SUMS`](SHA256SUMS):

```bash
sha256sum -c SHA256SUMS
```

The page **cannot hash itself**. A local page may not read its own bytes, and what JavaScript sees
is a re-serialisation of the parsed document rather than the file on disk. Any self-reported hash
would be unverifiable and trivially faked, so the tool does not offer one.

---

## Use it

1. **Download** the HTML file, `howitworks.pdf` and `techspecs.md`. Keep them in the same folder —
   the footer links are relative.
2. **Disconnect the machine.** Open the HTML from your own drive so the address bar starts with
   `file://`. A banner turns red if you are running it from a web server, because a server can
   send different code to different visitors and nothing you verified once still holds.
3. **Wash and shuffle a sealed deck.** Cards face down on the table, swirled for 30 seconds or
   more, then seven or more riffles with cuts between.
4. **Draw and type.** Four cards at a time, in the order dealt. 8 draws for a 12-word seed,
   14 for 24 words.
5. **Verify.** Use verify-by-re-entry, then compare the master fingerprint and the first two
   receive addresses against the wallet you restore into. Send a small amount and recover it
   before committing real funds.
6. **Wipe** the session before leaving the machine.

---

## How it works, briefly

```
preimage = "1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH …"
entropy  = first 128 bits of SHA-256(preimage)        (256 bits for 24 words)
checksum = first 4 bits of SHA-256(entropy)           (8 bits for 24 words)
mnemonic = entropy‖checksum split into 11-bit groups, indexing the BIP-39 English list
```

An ordered draw of four cards from 52 is worth log₂(52×51×50×49) = **22.63 bits**. The tool
deliberately collects far more than it uses:

| Seed | Draws | Card entropy in | Extracted | Head-room |
|---|---|---|---|---|
| 12 words | 8 | 181.05 bits | 128 | **+53.05** |
| 24 words | 14 | 316.84 bits | 256 | **+60.84** |

That surplus is the point. SHA-256 only behaves as a randomness extractor when its input carries
more entropy than its output; feed it exactly as many bits as you take out and an imperfect
shuffle passes straight through.

Full detail in **[`techspecs.md`](techspecs.md)**, including a worked example carrying every
intermediate value from cards to addresses.

Want to see it work before you shuffle anything? Load
[`examples/example-draw-record-12word.txt`](examples/example-draw-record-12word.txt) with
**Import draw record**, leave the settings at their defaults, and generate. You should get the
entropy, phrase, fingerprint and addresses printed in `techspecs.md` §9 — which is also how you
confirm your copy of the file derives the same seed as everyone else's.
**Those cards are published. Never fund that seed.**

---

## Recovery without this tool

Your card record is the backup, and the entropy hex in the PDF seed record is the universal
interchange format — every BIP-39 implementation accepts it.

```bash
printf '%s' '1deck-bip39-v2|12|<your cards>' | sha256sum | cut -c1-32
```

Feed that into any BIP-39 tool with entropy type **Hex**.
[`recover.py`](recover.py) does the whole job with Python's standard library and no network —
four lines of actual derivation, plus `bip39-english.txt`.

Step-by-step for iancoleman's tool, including the setting that silently double-hashes your entropy
if you get it wrong: [`docs/recovering-on-iancoleman.md`](docs/recovering-on-iancoleman.md).

---

## What's in this repo

| File | |
|---|---|
| `1deck-bip39-v2.15.html` | the tool — one self-contained file |
| `howitworks.pdf` | one-page summary, linked from the tool's footer |
| `techspecs.md` | full specification, enough to reimplement from scratch |
| `recover.py` | dependency-free recovery script |
| `bip39-english.txt` | official BIP-39 English wordlist |
| `SHA256SUMS` | checksums for everything above |
| `SECURITY.md` | threat model, scope, and how to report a vulnerability |
| `docs/entropy-method-and-comparison.md` | the method, and an even-handed comparison with iancoleman |
| `docs/recovering-on-iancoleman.md` | recovery walkthrough |
| `docs/test-report.md` | the audit trail: what was measured, what was found, what was fixed |
| `examples/` | a seed record, a blank draw sheet, and a draw record you can import |

---

## Verification built into the tool

- **Deterministic self-tests** — official BIP-39, BIP-32 and BIP-84 vectors, RIPEMD-160 known
  answers, the wordlist hash, and golden vectors that pin the whole card-to-seed pipeline. Same
  output on every machine.
- **A card-sensitivity sweep** — every card position substituted with all 48 legal alternatives,
  each result required to be new. This exists because a distribution test cannot do the job: a
  build that ignored a quarter of the cards, discarding 44.9 of 181.1 bits, still produced a flat
  chi-square. It fails the sweep instantly.
- **A shuffle check** on your own draws, calibrated analytically, that flags a deck which was not
  riffled enough — and says plainly that a low score means the deck does not look like a *new*
  deck, never that it is random.

---

## Honest limitations

- **It cannot certify your shuffle.** The check catches obvious under-shuffling. It is blind past
  about four riffles, it assumes the deck started in factory order, and a deterministic faro
  shuffle scores *better* than random while carrying no entropy at all.
- **It cannot scrub RAM.** JavaScript strings are immutable and garbage-collected. Wiping is
  best-effort; reload the page and close the browser.
- **The paper and the PDF are your seed.** The card draws alone reproduce it. Redacting the words
  does not make either safe.
- **This has not had months of adversarial review.** It has deterministic tests, published
  vectors, a documented threat model and an audit trail — not the same thing. Review is welcome;
  see [`SECURITY.md`](SECURITY.md).

---

## Licence

MIT — see [`LICENSE`](LICENSE). No warranty. You are responsible for your own funds.
