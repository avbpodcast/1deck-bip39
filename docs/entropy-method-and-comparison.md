# 1-deck card → BIP-39: entropy method, comparison, and recovery without the tool

Version 2.13 · derivation id `1deck-bip39-v2`

Every number in this document was produced by running the code, not by reasoning about it. The
worked examples are reproducible on any machine with `sha256sum`.

---

# Part 1 — The method

## 1.1 What the physical procedure produces

You shuffle a 52-card deck and record ordered draws of four cards. Each draw is written as four
two-character codes, rank then suit, in the order the cards came off the deck:

```
ranks  A 2 3 4 5 6 7 8 9 T J Q K
suits  C = clubs   D = diamonds   H = hearts   S = spades
draw   TD KD 8H 5C
```

**Order carries information.** The same four cards in a different order are a different draw and
produce a different seed. This is deliberate: an *ordered* draw of four distinct cards has

```
P(52,4) = 52 × 51 × 50 × 49 = 6,497,400 possibilities
log₂(6,497,400) = 22.6314 bits
```

An unordered draw — a *combination* — would be worth only log₂(C(52,4)) = log₂(270,725) = 18.05
bits. Insisting on order buys 4.58 bits per draw for free, at the cost of writing the cards down
left to right instead of sorted.

## 1.2 Two protocols, and why the entropy differs between them

**Reshuffle (default).** Return the four cards, reshuffle the whole deck, draw again. Every draw
is independent and worth the full 22.6314 bits, so *n* draws are worth 22.6314 × *n*.

**Deal-through.** Shuffle once, then deal cards straight off the top without returning them.
Dealing *m* ordered cards from one shuffled deck is worth

```
log₂(52 × 51 × … × (52 − m + 1))
```

which is strictly less than *m*/4 × 22.6314, and the shortfall grows as the deck is depleted:

| Cards dealt | Bits | | Cards dealt | Bits |
|---|---|---|---|---|
| 4 | 22.63 | | 32 | 164.50 |
| 8 | 44.79 | | 40 | 196.75 |
| 16 | 87.49 | | 48 | 221.00 |
| 24 | 127.64 | | 52 | **225.58** |

**225.58 bits is a hard ceiling.** One deck ordering cannot be worth more than log₂(52!) no
matter how well you shuffle. Two consequences the tool enforces:

- A 256-bit seed can never come from a single shuffle. Deal-through is disabled for 24 words.
- Passes are split *evenly* rather than filled to 52 cards. The 52nd card off a deck adds
  log₂(1) = 0 bits; the last four cards of a full pass add 4.58 bits between them, against 22.63
  for four fresh ones. Splitting 14 draws as 7 + 7 yields 293.1 bits where 13 + 1 yields 248.2 —
  below the 256-bit target.

## 1.3 The derivation

```
preimage = DERIVATION_ID ‖ "|" ‖ word_count ‖ "|" ‖ card codes separated by single spaces
entropy  = leading N bits of SHA-256(preimage)          N = 128 for 12 words, 256 for 24
checksum = leading N/32 bits of SHA-256(entropy)        exactly as BIP-39 defines
mnemonic = (entropy ‖ checksum) split into 11-bit groups, each indexing the BIP-39 English list
```

`DERIVATION_ID` is the ASCII string `1deck-bip39-v2`. It is **frozen** and is deliberately not
tied to the program version — changing it would silently change every seed the tool has ever
produced. Version 2.13 and version 2.01 derive identically.

Worked example, reproducible on any machine:

```
$ printf '%s' '1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H' | sha256sum
56cd7feb1647fd133477bc54589f7c2d5eefb33dec0fac06f085518495a628a2

first 128 bits (32 hex characters) = the entropy

entropy  56cd7feb1647fd133477bc54589f7c2d
phrase   fine hip width clutch lemon maze spike wasp february shaft tenant force
XFP      B8428EFE
```

## 1.4 Why hash at all, rather than use the card bits directly

This is the central design decision, and the honest answer is **head-room**.

Hashing does not create entropy. SHA-256 of a weak input is a weak seed dressed up to look
uniform — that is exactly why the tool refuses to let a statistical test stand in for a real one.
What hashing *with surplus input* does buy is extraction: when the input carries substantially
more entropy than the output, the output is close to uniform even when the input is not. When
input and output are the same size, no function can help you, because there is nothing to
compress away.

| Setting | Draws | Card entropy in | Extracted | Head-room |
|---|---|---|---|---|
| 12-word, margin | 8 | 181.05 bits | 128 | **+53.05** |
| 12-word, minimum | 6 | 135.79 bits | 128 | +7.79 |
| 24-word, margin | 14 | 316.84 bits | 256 | **+60.84** |
| 24-word, minimum | 12 | 271.58 bits | 256 | +15.58 |

That surplus is what absorbs an imperfect shuffle. Measured against the Gilbert–Shannon–Reeds
riffle model, starting from factory order, using the tool's own adjacency statistic (a uniform
deck averages 3.26 same-suit adjacent pairs):

| Riffles | Mean pairs | Riffles | Mean pairs |
|---|---|---|---|
| 1 | 24.67 | 5 | 3.84 |
| 2 | 16.25 | 6 | 3.43 |
| 3 | 9.24 | 7 | 3.31 |
| 4 | 5.33 | 8 | 3.21 |

A three-riffle shuffle is measurably not uniform. With 53 bits of head-room that deficit is
absorbed; with 7 bits it is not. This is why margin mode is the default and minimum mode carries
a warning in the interface.

## 1.5 Why the checksum is computed rather than drawn

BIP-39 checksum bits are redundancy, not entropy — they are a function of the entropy. An earlier
design spent a whole physical draw selecting among the checksum-valid final words. Measured, that
draw bought 7 bits for a 12-word seed and **3 bits** for a 24-word seed, in exchange for a full
shuffle. Computing the checksum instead is both cheaper and yields *more* card-derived entropy:
all 128 bits come from the pooled deck rather than 121 from the deck plus 7 from one draw.

## 1.6 What is deliberately absent

- **No random number generator.** No `Math.random`, no `crypto.getRandomValues`, no clock access
  anywhere, including in the countdown timers, which count whole ticks precisely so that this
  claim stays literally true.
- **No network surface.** Zero absolute URLs, no `src` attributes, no `fetch`, `XHR`, `WebSocket`
  or `sendBeacon`, no `<form>`, no cookies, no `console` output. From v2.13 the footer carries two
  **relative** links, to `howitworks.pdf` and `techspecs.md` sitting beside the file. They resolve
  against the local folder, fetch nothing, and open in a new tab so the page holding your draws is
  never navigated away from.
- **No hidden state.** The card draws alone reproduce the seed. Nothing else needs recording.

---

# Part 2 — How this differs from iancoleman.io/bip39

Both tools were run on the same 32 cards and both results were reproduced exactly from source, so
what follows is measured rather than asserted. Neither method is presented here as the correct
one; they make different trade-offs, and the trade-offs are stated in both directions.

## 2.1 Both encodings are unbiased

Given a fairly shuffled deck, both tools produce uniform entropy. It is worth stating this plainly
because the two designs look so different that it is easy to assume one must be cutting a corner.

iancoleman maps each card to a fixed-length bit pattern, chosen so that every emitted bit is
uniform:

```
32 cards (A♣ … 6♥)      → 5 bits each     32/52 of the time, 5 uniform bits
16 cards (7♥ … 9♠)      → 4 bits each     16/52 of the time, 4 uniform bits
 4 cards (T♠ J♠ Q♠ K♠)  → 2 bits each      4/52 of the time, 2 uniform bits
```

log₂(52) = 5.7004 bits per card does not divide evenly, so instead of reducing a value modulo
something — which would introduce bias — they emit a variable number of unbiased bits, averaging
4.46 per card. Conditioned on the length pattern the bits are uniform, and the length pattern is
independent of the values. The construction is sound.

This tool reduces the whole card sequence through SHA-256 and takes the leading bits. Given
uniform input that is also uniform output.

**So the difference is not bias. It is what happens when the shuffle is imperfect**, and how much
work each design does on your behalf.

## 2.2 What each tool did with the same 32 cards

```
TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H
```

**iancoleman, default setting `Use Raw Entropy (3 words per 32 bits)`:**

```
each card → its 5/4/2-bit code, concatenated        = 135 bits
round down to a multiple of 32                      = 128 bits
discard the first 7 bits, keep the last 128
entropy  2241c743a1939095106a6f658ae880dc
phrase   car athlete special drip decorate enhance double evil grain firm cage reveal
```

**This tool:**

```
preimage "1deck-bip39-v2|12|TD KD 8H 5C …"
entropy  first 128 bits of SHA-256(preimage) = 56cd7feb1647fd133477bc54589f7c2d
phrase   fine hip width clutch lemon maze spike wasp february shaft tenant force
```

Three independent reasons these can never coincide: one truncates a bit string where the other
hashes; one has a domain-separating prefix and the other has none; and they take bits from
opposite ends of entirely different bit strings.

## 2.3 The two designs, side by side

| | iancoleman, raw mode | This tool |
|---|---|---|
| Card → bits | fixed 5/4/2-bit code per card | whole sequence hashed with SHA-256 |
| Bits available from 32 cards | 135 | 181.05 |
| Bits used | 128 | 128 |
| Head-room | 7 bits | 53 bits |
| Bias, given a fair shuffle | none | none |
| Behaviour, given an unfair shuffle | carried through largely intact | absorbed, in proportion to the head-room |
| Verifiable by hand, no tools | **yes** | no — needs SHA-256 |
| Draw model | each card uniform over 52, independent | four *distinct* cards per draw, no replacement |
| Domain separation | none | `1deck-bip39-v2\|12\|` prefix |
| Scope | general tool, many entropy sources, widely reviewed | one method, one deck |

**The case for the raw-mode design.** It is transparent. You can look up each card's bits in a
printed table, concatenate them, drop the leading seven, split into 11-bit groups and read the
words off the list — no hashing, no trust in an implementation you cannot check with a pen. For a
tool whose users may not have a SHA-256 utility to hand, that is a real and defensible advantage.
It is also part of a long-standing, widely audited project, which counts for something that a
newer single-purpose page cannot claim.

**The case for the hashing design.** Truncating a bit string is not a randomness extractor. If the
deck was under-shuffled, the structure in those bits passes into the seed nearly undiminished. By
construction raw mode can never have more than 31 bits of slack, because any surplus bits become
*more words* rather than more margin. Feeding SHA-256 substantially more entropy than it emits
does absorb an imperfect shuffle — which matters, because §1.4 shows a three-riffle shuffle is
measurably not uniform, and most people do not riffle seven times.

Which trade you prefer depends on whether you are more worried about your shuffle or about your
ability to verify the arithmetic. Both are legitimate concerns.

## 2.4 The designs are closer than they look

iancoleman's *Mnemonic Length* dropdown, set to anything other than `Use Raw Entropy`, switches to
hashing: it takes SHA-256 of the display string `T♦ K♦ 8♥ 5♣ …` and uses the leading bits. That is
architecturally the same approach this tool uses. The differences that remain are the exact
preimage — Unicode suit symbols and no prefix, against ASCII letters and a domain separator — and
the fact that this tool fixes the number of draws so the head-room is known in advance.

So this is less a disagreement about method than about which behaviour is the default.

**One practical consequence.** The same cards give two different seeds on iancoleman depending on
that dropdown:

| Setting | Result for the cards above |
|---|---|
| `Use Raw Entropy` (default) | `car athlete special drip decorate enhance…` |
| `12 Words` | `embrace lend crush sign travel allow…` |

Both are valid BIP-39. If you ever re-derive there, the dropdown position matters as much as the
cards — which is an argument for recording the entropy hex rather than relying on remembering a
UI setting, whichever tool you used.

## 2.5 Domain separation, and why the prefix is there

The preimage begins `1deck-bip39-v2|12|`. It costs nothing and buys two things. It ties the seed
to a stated derivation, so a future scheme cannot accidentally produce the same seed from the same
cards. And it puts the word count inside the input, so the same 32 cards interpreted as a 12-word
and a 24-word seed cannot collide.

The cost is honest and worth naming: a seed produced here can only be reproduced by something that
knows this exact prefix. Part 3 exists so that "something" never has to be this web page.

---

# Part 3 — Recreating your seed without this tool

The tool being unavailable must never mean your seed is unrecoverable. The card record is the
backup; this section is how to use it with nothing but standard software.

## 3.1 What to store, in order of preference

1. **The card draws** — the primary record, on the printed draw sheet. Everything else follows.
2. **The entropy hex** — `56cd7feb1647fd133477bc54589f7c2d`. This is the universal interchange
   format: every BIP-39 implementation in existence can turn 128 or 256 bits of entropy into a
   phrase. Storing it removes the need for SHA-256 at recovery time.
3. **The master fingerprint** — eight hex characters. Not needed to recover, but it tells you
   instantly whether a recovery attempt produced the right seed.

The draw sheet has boxes for all three.

## 3.2 Step one: cards → entropy, with only `sha256sum`

Available on every Linux and macOS machine, and in Windows PowerShell.

```bash
# Linux / macOS. 12 words → keep the first 32 hex characters; 24 words → keep all 64.
printf '%s' '1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H' | sha256sum | cut -c1-32
→ 56cd7feb1647fd133477bc54589f7c2d
```

```powershell
# Windows PowerShell
$s = '1deck-bip39-v2|12|TD KD 8H 5C …'
$b = [Text.Encoding]::UTF8.GetBytes($s)
$h = [Security.Cryptography.SHA256]::Create().ComputeHash($b)
(($h | ForEach-Object { $_.ToString('x2') }) -join '').Substring(0,32)
```

Rules that matter: uppercase card codes, single spaces, `T` for ten, no trailing space, no
newline (that is what `printf '%s'` guarantees and `echo` does not).

## 3.3 Step two: entropy → seed phrase

Any of these work, and none of them are this tool:

- **Any BIP-39 library.** Python `mnemonic`: `Mnemonic("english").to_mnemonic(bytes.fromhex(...))`.
  Equivalents exist in every language.
- **iancoleman offline**, paste the hex into the entropy field with type `Hex`.
- **The 40-line script below**, which needs only Python's standard library.

## 3.4 The standalone recovery script

Shipped alongside this document as `recover.py`. Standard library only — no pip, no network. It
needs the official BIP-39 English wordlist as a text file, whose SHA-256 is published in the BIP
and is `2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda`.

```
$ python3 recover.py english.txt 12 "TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H"
preimage : 1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH …
entropy  : 56cd7feb1647fd133477bc54589f7c2d
phrase   : fine hip width clutch lemon maze spike wasp february shaft tenant force
```

Verified against both the 12-word and 24-word golden vectors and against the worked example above.
The whole derivation is four lines of code; if the script is ever lost, §1.3 is enough to rewrite
it from scratch.

## 3.5 Recommendation

Print this section — or at minimum §1.3 and §3.2 — and keep it with the card record. A backup
that depends on a website still existing is not a backup. The derivation is short enough to fit
on the draw sheet, and short enough that a competent stranger could reimplement it from the
specification alone in half an hour.

## 3.6 Proposed additions to the tool

1. **Print the recovery recipe into the PDF seed record**, so the paper carries its own
   instructions: the exact preimage, the entropy hex, the `printf | sha256sum` line, and a
   one-paragraph statement of the derivation.
2. **Ship `recover.py` next to the HTML**, with its SHA-256 published alongside.
3. **Add the entropy hex to the blank draw sheet** as a labelled row, so it is captured on paper
   at generation time rather than reconstructed later.
