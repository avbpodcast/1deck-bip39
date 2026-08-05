# Security Policy

This tool derives Bitcoin seed phrases. 
A defect here can cost people money that cannot be
recovered. Reports are welcome and will be taken seriously when documented.

---

## Reporting a vulnerability

**Preferred — GitHub's private advisory flow: the "Security" tab → "Report a vulnerability".**
That keeps the report private until a fix is published, and it threads the discussion with the
code.

**By email — security@avbforge.com.** Use this if you would rather not report through GitHub, or
if the repository is unreachable. Say up front that it concerns the 1-deck card BIP-39 generator.

Please do **not** open a public issue for anything that could weaken a seed.

What helps most, in rough order:

- Which file and version — the SHA-256 of the HTML you tested, not just the version number.
- What you did, and what you expected instead.
- A card sequence that reproduces it, **using cards you have never used for a real seed**.
- Whether the derivation itself changes, or only the interface.

You will get an acknowledgement. If a report turns out to be a real weakness in the derivation,
it will be fixed, disclosed, and credited unless you ask otherwise.

---

## Supported versions

Only the latest released version is supported.

The **derivation** is frozen and versioning it is deliberate: `DERIVATION_ID` is the fixed string
`1deck-bip39-v2` and is never tied to the program version. Every 2.x release reproduces the same
seed from the same cards. If that ever has to change, the derivation id changes with it and it
will be stated loudly, because a silent change would strand every existing card record.

---

## What is in scope

Anything that could produce a weak, wrong, or leaked seed:

- **The derivation** — the preimage construction, entropy extraction, BIP-39 checksum, word
  mapping. A mismatch against `techspecs.md` §9 or the standard test vectors is a bug.
- **Entropy accounting** — a configuration where the tool claims more head-room than the cards
  actually carry.
- **Anything reintroducing non-determinism** — a random number generator, clock access, or any
  input to the seed other than the cards.
- **Leaks** — the seed reaching the clipboard, disk, browser storage, session restore, a network
  request, or a saved copy of the page, other than where the tool says so.
- **The verification path** — a self-test that passes on a broken build, or a golden vector that
  does not actually exercise the shipped code. This has happened before; see below.
- **The PDF writer** — malformed output, or a record that does not match what was on screen.

## What is out of scope

Not because it does not matter, but because it is outside what a single HTML file can control:

- **A compromised machine.** Keyloggers, screen capture, malicious extensions, a hostile OS. The
  tool assumes the machine is trusted; if it is not, nothing here helps.
- **A modified copy of the file.** Verify the SHA-256 against a published value first — see
  `README.md`. The in-page checks cannot protect you here, because a modified page controls them.
- **Physical security.** Cameras, shoulder-surfing, someone finding the paper.
- **Your shuffle.** The tool flags obvious under-shuffling but cannot certify randomness. An
  under-shuffled deck is a real weakness and the documentation says so, but it is not a code bug.
- **Browser or OS vulnerabilities.**
- **The absence of features** you would like to see. Open a normal issue for those.

---

## Design decisions that are intentional

Please check these before reporting; each is deliberate and documented.

| Observation | Why |
|---|---|
| The seed phrase sits in the DOM after generation | It has to be displayed. It is blurred by default, auto-hides on idle and on tab switch, and the wipe button clears it. A CSS blur does not hide text from an extension — this is stated in the tool. |
| The PDF record contains the seed | It is a seed backup. It says so on page one. The card draws alone reproduce the seed, so redacting the words would not make it safer. |
| The footer has two `href` links | They are **relative**, to documentation files beside the page. They resolve locally, retrieve nothing, and open in a new tab so the page holding your draws is not navigated away from. |
| Wiping cannot guarantee erasure from RAM | JavaScript strings are immutable and garbage-collected. The tool overwrites what it can, says plainly that this is best-effort, and recommends reloading and closing the browser. |
| The shuffle check passes a faro-shuffled deck | Measured: two perfect faros score 0.00 adjacent pairs, better than random, while being fully deterministic. A low score means the deck does not look like a *new* deck — never that it is random. Documented in `techspecs.md` §8. |
| Deal-through is disabled for 24 words | One deck ordering is worth at most log₂(52!) = 225.58 bits. A 256-bit seed cannot come from a single shuffle. |
| Minimum mode has thin head-room | 7.79 bits for a 12-word seed. It is offered, warned about in the interface, and is not the default. |

---

## How this project verifies itself

Stated so you know what the existing checks do and do not prove.

- **Deterministic self-tests**, built into the page. Official BIP-39, BIP-32 and BIP-84 vectors,
  RIPEMD-160 known answers, the wordlist hash, and golden vectors pinning the whole card-to-seed
  pipeline to fixed output. Same result on every machine.
- **A card-sensitivity sweep** : Every card position substituted with all 48 legal alternatives
  across several baselines, each output required to be new. This exists because a distribution
  test cannot do the job: a build that silently ignored a quarter of the cards, throwing away 44.9
  of 181.1 bits, still produced a flat chi-square with a healthy p-value. It fails the sweep
  immediately.
- **A negative control** inside that sweep, asserting the broken build *would* be caught, so the
  sweep cannot quietly stop working.

- **An input guard on the derivation itself**, with a self-test that proves it fires. The
  derivation refuses anything that is not a grid of canonical card indices rather than deriving
  from it. See the note below for why.

**A near miss, fixed in 2.14 and kept here because the shape of it is instructive.** `cardCode()`
converts a card index to its two-letter code and validated nothing, so `cardCode(null)` returned
`"AC"` — `null % 13` is `0`. A grid with one draw left blank would therefore have derived from
aces of clubs the user never drew, and produced twelve valid words with a correct checksum and
nothing on screen to suggest anything was wrong. It was never reachable: every caller validated
first. But "the caller checks" is precisely the arrangement that fails the first time somebody
adds a caller, and the damage would have been a wrong seed that looked right. `deriveFromCards()`
now refuses malformed input itself, and seven self-tests assert that it does.

**A defect found in this project's own history, kept here as a caution.** An earlier version's
golden vectors and sensitivity sweep each re-implemented the derivation inline instead of calling
the shipped function. Sabotaging the real derivation left every test passing with a perfect score.
Both now go through the single production path, and sabotaging it fails them. If you are auditing:
*check that the tests call the code that ships*, not a copy of its logic.

---

## Threat model in one line

The tool assumes a trusted, offline machine and a genuinely shuffled deck, and tries to be honest
about everything it cannot assume.