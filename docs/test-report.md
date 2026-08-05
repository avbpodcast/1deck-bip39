# 4-card → BIP-39 mapping: test report and improvements

Tests were run against the v1 file as shipped, and then against the v2 file as built.
Everything below is reproducible: the card-side tests are exhaustive rather than sampled,
so they have no error bars.

---

## Part 1 — What v1 gets right

I extracted v1's actual code and ran it, rather than reading it.

**The ranking function is a proven bijection.** I enumerated all 6,497,400 ordered 4-card
draws and computed `rank4Distinct` for each. Zero collisions, zero gaps, full coverage of
`[0, 6497400)`. The permutation ranking is exactly correct.

**The modulo-bias rejection is exactly right.**

```
TOTAL      = 52·51·50·49 = 6,497,400
MAX        = ⌊6497400 / 2048⌋ · 2048 = 6,496,256
rejected   = 1,144 draws = 0.0176%
```

Counting exhaustively: after rejection, every one of the 2,048 words is backed by exactly
3,172 permutations. Not approximately — exactly. Min count equals max count.

Without the rejection the bias would have been tiny anyway (the most likely word would be
0.0315% more likely than the least likely, a min-entropy loss of 0.0002 bits), but the
rejection is correct and costs almost nothing.

**Using the low bits was the right choice.** This surprised me, so I tested it. I simulated
the Gilbert–Shannon–Reeds riffle model — the standard mathematical model of a human shuffle —
starting from new-deck order, and measured how uniform each candidate mapping's output is:

| Riffle shuffles | `rank % 2048` (v1) | `⌊rank / 3172⌋` (top bits) | `SHA-256(cards)` |
|---|---|---|---|
| 2 | 7.83 / 11 bits | 3.99 / 11 bits | 7.94 / 11 bits |
| 3 | **10.41** / 11 bits | 6.02 / 11 bits | 10.49 / 11 bits |
| 4 | 10.59 / 11 bits | 7.81 / 11 bits | 10.55 / 11 bits |
| 7 | 10.70 / 11 bits | 10.33 / 11 bits | 10.69 / 11 bits |

(min-entropy of the resulting word, 400,000 trials each)

Taking the top bits instead of the low bits would have been catastrophically worse under an
imperfect shuffle. v1's `% 2048` performs as well as a SHA-256 hash. **Do not change this.**

**The checksum logic is standard-compliant.** `csLen`, the entropy-byte extraction and the
candidate search all produce correct BIP-39. I confirmed against the four official test
vectors and confirmed that all 128 of v1's 12-word checksum candidates independently validate.

**The wordlist is the genuine official list**, despite the comment in the source saying
`TRUNCATED – REPLACE WITH FULL LIST`. 2,048 entries, sorted, unique 4-letter prefixes,
`sha256 = 2f5eed53…3b24dbda`. That comment is wrong and should be deleted — it invites
someone to "fix" a file that is already correct.

---

## Part 2 — What can be improved

### 2.1 The mapping throws away 51% of the entropy you physically generate

This is the big one.

```
An ordered 4-card draw carries log₂(6,497,400) = 22.6314 bits.
v1 extracts 11 bits from it.
Efficiency: 48.60%.
```

You shuffle a deck, draw four cards, write them down — and v1 discards more than half of the
work. For a 12-word seed that means 12 full shuffle-and-draw cycles where 8 would do.

**v2 fix.** Pool the draws and extract once, instead of extracting per-draw:

```
preimage = "1deck-bip39-v2|12|AS 7H TD 3C KD 2S 9C JH …"
entropy  = leading 128 bits of SHA-256(preimage)   (256 for a 24-word seed)
```

| | 12-word seed | 24-word seed |
|---|---|---|
| v1 draws | 12 | 24 |
| v2 draws (margin mode) | **8** | **14** |
| v2 draws (minimum mode) | 6 | 12 |
| Extraction efficiency | 48.6% → **70.7%** | 48.6% → **80.8%** |
| Entropy bits from cards | 121 + 7 | 253 + 3 |
| → in v2 | **128** | **256** |

### 2.2 Pooling also buys a real safety margin — that is why margin mode is the default

Hashing does not create entropy. But hashing *with head-room* is a genuine randomness
extractor: if the input carries more entropy than the output, the output is close to uniform
even when the input is not.

v1 has no head-room at all. Each draw independently yields 11 bits from 22.63, with no
cross-draw pooling, so a mediocre shuffle leaks directly. From the table above, at 3 riffles
v1 delivers 10.41 bits per word — so a 12-word v1 seed built on a 3-riffle shuffle is worth
roughly **125 bits, not 128**.

v2 margin mode feeds 8 draws (181.1 raw bits) into 128 extracted bits, leaving **53.1 bits of
head-room**. The 24-word setting feeds 14 draws (316.8 bits) into 256, leaving 60.8 bits. That
margin absorbs a shuffle that is merely decent rather than perfect — while still needing fewer
draws than v1.

Minimum mode (6 draws → 128 bits, 7.8 bits of head-room) is offered but flagged in the UI.
It is fine given a genuinely good shuffle and thin otherwise.

### 2.3 The checksum draw was the least efficient step, and it turned out to be unnecessary

v1 spent a full shuffle-and-draw cycle selecting the final word from the checksum-valid
candidates. Measured cost:

| Seed | Valid final words | Bits obtained | Bits drawn | Efficiency |
|---|---|---|---|---|
| 12-word | 128 (always exactly 128) | 7 | 22.63 | 31% |
| 24-word | 8 (always exactly 8) | 3 | 22.63 | 13% |

A whole shuffle for 3 bits. But the deeper point is that the step was an artifact of v1's
one-draw-one-word architecture: 11 draws gave 121 bits, and the 12th word was left dangling.
Once v2 pools the draws, SHA-256 emits 256 bits and only 121 were being used — bits 122–128
were sitting there unused, already card-derived.

**v2 now computes the checksum**, as BIP-39 defines it. This is not a compromise on
traceability; it is strictly more card-derived entropy:

| | Entropy from cards | From a dedicated draw | Draws (12w) |
|---|---|---|---|
| v1 / early v2 | 121 bits | 7 bits | 12 / 9 |
| **v2 final** | **128 bits** | — | **8** |

Checksum bits are redundancy, not entropy, so computing them costs nothing. The rejection
path, the candidate list and the selection step are all gone — along with the failure mode
where a valid set of draws had to be partially re-done because the checksum draw landed in the
overflow band.

A secondary benefit: **your paper draw sheet alone now fully reproduces the seed.** Nothing
else needs recording.

Three alternatives were considered and rejected. Right-sizing the draw (2 cards for a 12-word
seed, 1 card for a 24-word seed, instead of 4) would have kept the ritual at a quarter of the
cost — measured rejection rates 3.5% and 7.7%. A blind human number pick, 1-of-128, committing
to the number before revealing the words, is sound and bounded at 7 bits worst case (leaving
121). Seven coin flips is mathematically perfect, 2^7 = 128 exactly with zero rejection. All
three are secure; all three require recording something that is not a card.

### 2.6 Deal-through: honest numbers on the one-shuffle protocol

Deal-through — shuffle once, then deal cards straight off the top without replacement — is not
the default, and testing showed the original implementation was worse than it needed to be.

**Dealing without replacement yields less entropy, and the loss accelerates.** Dealing *n*
ordered cards off one shuffled deck is worth log₂(52·51·…·(52−n+1)) bits, not n/4 × 22.63:

| Cards dealt | Bits | Cards dealt | Bits |
|---|---|---|---|
| 4 | 22.63 | 32 | 164.50 |
| 8 | 44.79 | 40 | 196.75 |
| 16 | 87.49 | 48 | 221.00 |
| 24 | 127.64 | 52 | **225.58** |

**225.58 bits is a hard ceiling.** One deck ordering cannot be worth more, no matter how well
you shuffle. So a 256-bit seed can *never* come from a single shuffle — at least two passes are
always required for 24 words. This is now stated in the tool.

**The original 13-draws-per-pass rule was actively wrong.** Filling each pass to a full 52 cards
looks natural but wastes the tail: the 52nd card off a deck adds log₂(1) = 0 bits, and the last
four cards together add only 4.58 bits versus 22.63 for four fresh ones. Splitting draws evenly
across passes is strictly better for the same number of shuffles:

| 24-word, 14 draws | Pass split | Raw bits | Head-room over 256 |
|---|---|---|---|
| Original rule | 13 + 1 | 248.2 | **−7.8** |
| Balanced | 7 + 7 | **293.1** | **+37.1** |

The original rule produced a genuine entropy shortfall. v2 now splits evenly and picks the
smallest number of passes that clears the target by 24 bits.

**Measured head-room per combination, as the tool now computes it live:**

| Seed | Mode | Draws | Reshuffle | Deal-through | Passes chosen |
|---|---|---|---|---|---|
| 12-word | margin | 8 | +53.1 | **+36.5** | 1 |
| 12-word | minimum | 6 | +7.8 | +6.8 | 2+2+1+1 |
| 24-word | margin | 14 | +60.8 | **+37.1** | 7+7 |
| 24-word | minimum | 12 | +15.6 | +9.7 | 3+3+3+3 |

Two combinations would have been short of entropy under a naive single pass — 12-word minimum
(127.6 bits for a 128-bit target, −0.4) and 24-word minimum (221.0 for 256, −35.0). The
balanced-pass search now avoids both automatically, and the tool warns whenever head-room drops
below 24 bits.

**The counting is not the real objection.** In margin mode deal-through delivers the full 128 or
256 bits with 36–37 bits to spare — it is safe. The reason it stays off by default is that one
shuffle becomes a single point of failure. Under the reshuffle protocol a poor shuffle spoils
one draw in eight and the other seven dilute it; under deal-through every card in a pass comes
from the same shuffle, so a poor shuffle correlates all of them at once.

There is a clean bound here worth stating: a riffle shuffle has at most 2⁵² outcomes, so *k*
riffles cannot produce more than 52k bits of deck entropy. Extracting 164.5 bits from one pass
therefore needs at least 4 riffles by counting alone — and counting is the generous bound. The
GSR results in Part 1 show that at 4 riffles the distribution is still visibly non-uniform;
seven or more, with cuts and strips, is what you actually want.

### 2.4 Silent failure modes in v1

- **`BIP39_WORDS[i % BIP39_WORDS.length]`** — the modulo means a truncated wordlist would
  silently produce wrong-but-plausible words instead of throwing. The list is currently
  correct, so this is latent, not active. v2 indexes directly and self-tests the list hash.
- **Manual mode was not actually manual.** In v1, once you had entered enough words by hand,
  `finalizeManualChecksum()` called `pickByCards()`, which called `shuffleDeckCanonical()` —
  the browser RNG. The final word of a "manual" v1 seed came from software, not from your
  deck. v2 removes this entirely.
- **`riffleShuffle()` used `Math.random()`**, not `crypto.getRandomValues()`, for both the
  packet sizes and the alternation. Non-cryptographic. Moot in v2, which has no shuffle.

### 2.5 No protection against transcription error

40+ hand-copied cards, and a single wrong card changes the seed completely with no warning.
Measured: change one card out of 32 and 11 of the 12 words change.

v2 adds duplicate detection within each draw, an optional deal-through protocol where the
tool enforces that all cards within a pass are distinct (a strong typo trap the reshuffle
protocol cannot offer), a printable draw sheet, import/export of the draw record, and a
verify-by-re-entry mode that blanks every input, holds a fingerprint, and names the exact draw
and card position that differs.

### 2.7 Entering 32 to 56 cards through paired dropdowns is the wrong interface

The original layout put eight `<select>` elements per draw in a single wrapping row, so cards
did not line up in columns and a 56-card entry meant 112 dropdown interactions.

v2 now lays each draw out as its own block with four aligned card slots, each showing a live
card face so you can check the screen against the table at a glance. The block turns green when
complete and red on a duplicate. Above the slots is a quick-entry field that accepts the whole
draw as text — `AS 7H TD 3C`, `as7htd3c`, `A♠ 7♥ 10♦ 3♣` and `AS,7H,10D,3C` all parse — which
cuts a 56-card entry from 112 interactions to 14 short typed lines. The two paths stay in sync
in both directions, and focus advances automatically: rank → suit → next card → next draw.

### 2.8 Result display and the PDF record

**A CSS regression found while fixing this.** The reported symptom was word numbers running into
the words — `1pelican`. The cause was broader: an earlier range-replacement in the stylesheet had
removed the rules for `.out` (every result and warning box), `pre.mono`, `.progressbar`,
`table.sheet` and `#wordGrid` in one go. Headless tests read class names and text content, so they
never saw it. There is now a CSS coverage check in the test pass that asserts every class and id
referenced in the HTML or JS has a matching rule; it reports 51 of 74 selectors styled, with the
remainder being ids used purely as JavaScript handles.

The word list is now a two-column grid per cell — a monospace, right-aligned index on a darker
panel, then the word — so numbers and words can never collide. Below a separator, the full phrase
is printed on one line in monospace with widened word spacing and `user-select:all`, so a single
click selects the whole thing.

**PDF record.** Written by hand, byte by byte, in about 200 lines: no library, no CDN, no network,
because the tool has to keep working air-gapped. It uses only the PDF base-14 fonts (Helvetica,
Helvetica-Bold, Courier), which require no embedding, and strictly ASCII text, so no encoding table
is needed. Card suits are written `C D H S` rather than `♣ ♦ ♥ ♠` for that reason.

The record contains the configuration, the entropy accounting, every draw in order with both card
codes and full names, the exact SHA-256 preimage with a `printf | sha256sum` line to reproduce it,
the digest, the entropy, the checksum computation, the numbered words, the full phrase, and the
draw fingerprint. It carries **no creation date** — the generator has no access to the clock by
design, and adding one would trip its own RNG audit.

Validated as follows:

- `qpdf --check`: no syntax or stream encoding errors, both the 2-page and 3-page outputs.
- `pypdf` parses both without error.
- **Round-trip:** the draw table was extracted from the finished PDF with `pdftotext`, the preimage
  rebuilt from those cards alone, and the seed recomputed independently in Python. Entropy, full
  phrase, numbered grid and fingerprint all match what the PDF printed, and the printed phrase
  passes an independent BIP-39 checksum check. The PDF verifies itself.
- 200 seeds across all eight mode combinations: 200 valid PDFs, 200 seeds checksum-valid, numbered
  grid identical to the full phrase line in every case.

**One bug fixed on the way.** Verify mode told the user "the seed will not be shown again until the
two entries match" — and then left it on screen. It now clears the word grid, the phrase, the
derivation detail and the buttons when verification starts, so the message is true.

The PDF is seed-equivalent and says so on the first page. The card draws alone reproduce the seed,
so there is no meaningful redacted version: omitting the word list would not make the file safe.

### 2.9 Why v2 has no dieharder-style statistical test

v1 shipped a 200,000-draw statistical suite — chi-square, KL divergence, autocorrelation, runs
test, top-5 and bottom-5 word lists. It was measuring `crypto.getRandomValues` plus the simulated
shuffle. v2 has neither, so rebuilding it would mean either reintroducing an RNG — breaking the
core guarantee and tripping the page's own audit — or feeding it a deterministic counter, in which
case it tests SHA-256 and always passes.

**Demonstrated rather than argued.** I built a derivation that silently ignores the 4th card of
every draw: a bug costing 44.9 of 181.1 bits, dropping head-room from 53.1 to 8.1. Then ran
exactly v1's statistics over 300,000 word samples from each build:

| | chi-square (2047 df) | p-value | KL | max abs Z | Verdict |
|---|---|---|---|---|---|
| Correct | 1970.8 | 0.883 | 0.0047 | 3.68 | **PASS** |
| Ignores 25% of the cards | 2072.5 | 0.348 | 0.0050 | 4.09 | **PASS** |

The broken build's numbers are closer to ideal than the correct one's. Top-5 and bottom-5 lists
look equally healthy in both. SHA-256 whitens its output regardless of how little entropy went in,
so no distribution statistic can see the difference. **A test that passes a build discarding a
quarter of your cards is worse than no test — it teaches you to trust the green light.**

**What replaced it: the card-sensitivity sweep.** Every card position is substituted with all 48
legal alternatives across three deterministic baselines, and every resulting entropy value must be
new:

| | substitutions | distinct outputs | dead positions | Verdict |
|---|---|---|---|---|
| Correct | 12,672 | all distinct | 0 | **PASS** |
| Ignores card 4 | 1,536 (12w) | 384 collisions | 8 | **FAIL** |

It also checks that swapping two cards within a draw, or two whole draws, always changes the seed —
order carries information, and this proves the code honours that. The sweep ships with its own
negative control: a test that confirms the broken build *would* be caught, so the sweep cannot
silently stop working. 9 checks, 0 failures, ~12,700 derivations.

### 2.10 The shuffle check — measuring the risk the software cannot otherwise see

The real risk was never the code. It is the shuffle, and software cannot watch you shuffle. Except
partially, because a sealed casino deck starts in **known order**: within each suit the ranks run in
sequence, and insufficient riffling leaves those runs partly intact.

Statistic: pairs within a single draw that are the same suit and one rank apart, summed over all
draws. Calibration is analytic, so nothing needs simulating — a deck holds 4 x 12 = 48 such pairs
out of C(52,2) = 1326, each draw contributes C(4,2) = 6 pairs, so the expectation is
6 x 48/1326 = 0.2172 per draw and the total is Poisson to a very good approximation.

| Riffles | Mean pairs (8 draws) | Warning rate | Strong alarm |
|---|---|---|---|
| 1 | 16.08 | **100%** | **100%** |
| 2 | 9.19 | **97.5%** | 82.0% |
| 3 | 5.19 | 41.7% | 9.8% |
| 4 | 2.92 | 5.2% | 0.3% |
| 7 | 1.76 | 0.3% | 0.0% |
| 12 | 1.78 | 0.6% | 0.0% |

Thresholds come straight from the Poisson tail at 1% and 0.1%, and the simulated false-alarm rate
(0.6% at 12 riffles) matches the nominal 1%. Across 200 regression sessions on well-shuffled decks
there were zero false alarms. The power sits exactly where Part 1 showed the danger is — one to
three riffles — and goes quiet once the shuffle is adequate.

Two limits, stated in the UI and in the PDF: it assumes the deck started in new-deck order, so an
already-shuffled deck shows no signal and always passes; and it is one-sided, catching
under-shuffling but never certifying good shuffling. Four or more riffles are invisible to it. It
is a blunder detector, not a certificate, and it says so.

The result appears with every derivation and is written into the PDF record, listing the offending
pairs by name so you can check them against the table.

---

## Part 3 — v2 test results

**Deterministic self-test, built into the page: 23 passed, 0 failed.**

```
PASS  Wordlist: 2048 entries, sorted, unique 4-char prefixes, official sha256
PASS  SHA-256 known-answer tests (empty string, "abc")
PASS  All four official BIP-39 test vectors (12-word and 24-word)
PASS  All 52 card codes distinct, fixed-width, round-trip correctly
PASS  BIP-39 index round-trips for all 2048 words
PASS  Golden vector: 12-word seed from a fixed 32-card sequence
PASS  Golden vector: 24-word seed from a fixed 56-card sequence
PASS  Sweep: 8192 derived mnemonics pass an independent BIP-39 check
PASS  Sweep: words round-trip back to the exact entropy every time
PASS  Sweep: all 2048 word indices reachable on both the 12- and 24-word paths
```

The golden vectors pin the entire card-to-seed pipeline to fixed expected output. They fail
only if the page has been altered — which is the point of them.

**Integration testing in a headless browser:**

- 240 seeds derived across all four modes (12/24 words × margin/minimum).
  240 independently checksum-valid. 0 invalid.
- Draw counts correct per mode: 8 / 6 / 14 / 12.
- Golden vector reproduced through the real UI: entropy `0ac0bfcc…8bffa2f`, seed
  `approve album veteran lounge noble enemy win napkin cousin echo write galaxy`.
- Determinism: same cards always give the same seed.
- Avalanche: one card changed out of 32 → 11 of 12 words change.
- Deal-through duplicate trap catches an injected cross-draw duplicate and suppresses output.
- Incomplete input is caught and named by draw number.
- Verify mode: correctly names "Draw 5 … differs at card 4" on a single injected error,
  then reproduces the original seed identically on correct re-entry.
- External reproducibility: `printf '%s' "<preimage>" | sha256sum` on the command line matches
  the entropy the page derived.

**RNG audit of the shipped v2 file:** zero call sites for `Math.random`,
`crypto.getRandomValues`, `Date.now`, `new Date` or `performance.now` in executable code.
The only crypto call is `crypto.subtle.digest("SHA-256", …)`, which is deterministic.
The page can run this audit on its own source at the click of a button.

---

## Summary

| | v1 | v2 |
|---|---|---|
| Entropy source | browser RNG, or manual with an RNG-chosen checksum word | physical draws only |
| RNG call sites | `Math.random`, `crypto.getRandomValues` | none |
| Extraction efficiency | 48.6% | 70.7% (12w) / 80.8% (24w) |
| Draws for a 12-word seed | 12 | 8 |
| Draws for a 24-word seed | 24 | 14 |
| Entropy bits derived from cards | 121 + 7 from a dedicated draw | 128, all pooled |
| Checksum | selected by a physical draw | computed, per the standard |
| Head-room against a poor shuffle | none | 53.1 bits (12w) / 60.8 bits (24w) |
| Typo protection | duplicate check within one draw | duplicates, deal-through distinctness, verify-by-re-entry, print sheet |
| Self-test | statistics on a random number generator | deterministic proofs about the mapping |
| Paper sheet alone reproduces seed | yes | yes |
| Self-test | statistics on a random number generator | deterministic proofs and golden vectors |

The core mathematics in v1 was sound. What it wasted was your shuffling.

---

## Part 4 — Self-audit of v2.01, and what it found

I reviewed my own work with an independent reviewer plus an executable harness. It found real
defects, including one that invalidated a claim I had made prominently.

### 4.1 CRITICAL — the self-tests did not test the shipped code

The golden vectors and the card-sensitivity sweep each **re-implemented** the derivation inline
instead of calling the function the button uses. So they verified their own arithmetic, not the
tool.

Demonstrated: I sabotaged the production `preimageString` to drop the 4th card of every draw —
the exact 44.9-bit bug from §2.9 — and ran the shipped tests against it.

```
Golden vector: 12-word seed from a fixed 32-card sequence     PASS
Golden vector: 24-word seed from a fixed 56-card sequence     PASS
FAST SELF-TEST                                    18 passed, 0 failed
SENSITIVITY SWEEP                                  9 passed, 0 failed
  "Negative control: a build that ignored card 4 would be caught"  PASS
RNG audit                                                     Clean
```

The seed changed completely and every test passed. This is precisely the failure I criticised
the chi-square for in §2.9, reproduced in the test I wrote to replace it. My claim that "a
golden vector fails only if this page has been altered" was false.

**Fixed.** There is now one `deriveFromCards()` that the interface, the golden vectors and the
sweep all call. Re-running the same sabotage:

```
FAST SELF-TEST                                    16 passed, 2 failed
  FAIL  Golden vector: 12-word seed from a fixed 32-card sequence
  FAIL  Golden vector: 24-word seed from a fixed 56-card sequence
SENSITIVITY SWEEP                                  5 passed, 4 failed
```

The lesson generalises: a test that reproduces the logic it is checking is not a test.

### 4.2 HIGH — "Download this page" wrote the seed into the saved file

`downloadPage()` serialised the live DOM. After a derivation that includes `#detail`, which
holds the card list, the preimage, the entropy hex and the phrase — `display:none` does not
remove text from `outerHTML`. The file was named like a pristine copy of the tool and sat under
a "Security" heading. Confirmed: the saved HTML contained the seed phrase, the entropy and the
preimage. It now refuses while a seed is loaded and tells you to wipe first.

### 4.3 HIGH — verify mode kept the plaintext it promised not to

The UI said the first entry was "held only as a fingerprint". It actually stored every card, and
on mismatch printed the first entry back — so a deliberate typo made the page reveal what had
been typed before. It now stores one SHA-256 hash per draw, names which draws differ, and never
echoes the original.

### 4.4 HIGH — cancelling verification discarded the seed from the screen

`startVerify()` blanked the grid and hid the result; `cancelVerify()` restored none of it. The
seed sat in memory with every control that could display it hidden, and the only recovery was
retyping every draw. Cancel now restores the phrase, the grid and the draws.

### 4.5 Other confirmed defects, all fixed

| | Defect |
|---|---|
| Import | Blended two records together, left stale cards where a token failed to parse, and ignored the record's own seed-length header — silently deriving a wrong seed. Now clears first, blanks unreadable slots by name, and refuses a record whose length or draw count does not match. |
| Fail-open | A validation error, a SHA-256 error or a failed checksum left the previous seed on screen with Copy and Download live. All four paths now clear the output and null the result. |
| Deal-through detail | The derivation detail reported the reshuffle figure (181.05 bits) while the panel and PDF reported the correct 164.50 — the same page stating two entropy figures for one derivation. |
| Wipe races | A self-test or derivation in flight wrote its results back into the DOM *after* the wipe reported success. A generation counter now cancels anything in flight. |
| Clipboard | The wipe banner always claimed the clipboard was cleared; the failure path was unreachable code, and `doWipe` runs from a timer rather than the click, so Firefox refuses the write. It no longer claims success. |
| RNG audit | Scanned only `<script>` text, so it could not see the inline `onclick` handlers this page uses for every button, and reported "Clean" for an injected external script. Now covers inline handlers, flags external scripts, and states plainly that it is a text scan and not a proof. |
| Stale state | `rebuild()` left `#drawMsg` showing an error under a freshly emptied grid, and left `state.verify.fingerprint` set, so `startVerify()` threw a TypeError after a settings change. |
| Quick entry | `parseQuick` computed a `bad` flag and discarded it, silently truncating a draw on a typo. Now shown as "unreadable card code". |
| Self-test transcript | Claimed byte-identical output on every machine while formatting numbers with `toLocaleString` (`8,192` vs `8.192` by locale). Replaced with a locale-independent formatter. |
| PDF | Shaded warning panels were fixed-height and half the text fell outside them; they are now sized to their content. The `printf … | sha256sum` line wraps, which would produce a different hash if retyped verbatim — now flagged in the document. |
| Deal-through label | Said "One shuffle" while 12-word + minimum yields four passes. Relabelled "fewest shuffles"; the banner already stated the real count. |

### 4.6 Verification after the fixes

- Golden vector unchanged: `0ac0bfcc…8bffa2f` → `approve album veteran … write galaxy`.
- 23/23 deterministic self-tests, 9/9 sensitivity sweep.
- 90 seeds across all six reachable mode combinations, all externally checksum-valid; 90 record
  PDFs and 6 blank sheets, `qpdf --check` clean.
- Tamper test: sabotaging the production derivation now fails 2 golden vectors and 4 sweep checks.
- Wipe: nothing in flight can restore output afterwards; no trace of the seed, entropy or
  fingerprint anywhere in the rendered DOM.

---

## Part 5 — v2.03

Three changes. The derivation is untouched: `DERIVATION_ID` is still `1deck-bip39-v2` and the
golden vector still yields `0ac0bfcc…8bffa2f` → `approve album veteran … write galaxy`.

### 5.1 The shuffle check now sees across draw boundaries

Part 4 closed with a known weakness: the statistic counted same-suit adjacent pairs only *within*
a 4-card draw, so under deal-through — the one protocol where a single bad shuffle is fatal — the
signal sitting between the last card of one draw and the first card of the next was invisible.

My first attempt was to count every pair within a pass. **Simulation showed that is much worse**,
and the measurement is worth recording:

| Riffles | All 496 pairs in the pass | Windowed, 90 pairs |
|---|---|---|
| 1 | **5.8%** detected | **100%** |
| 2 | 0.0% | 100% |
| 3 | 0.0% | 66% |

Under-shuffling creates adjacency between cards that end up *near each other in dealing order*.
Counting distant pairs adds 496 pairs of pure Poisson noise to catch the same handful of signal
pairs. Locality is the whole source of the test's power.

The shipped version counts pairs at a dealing-order distance of **3 or less, within a pass**. For
a 4-card pass that is all 6 pairs, so the reshuffle protocol is bit-for-bit unchanged. For a
32-card deal-through pass it is 90 pairs that straddle the draw boundaries. Measured against the
GSR model, versus the old statistic:

| Riffles | Windowed warn / alarm | Old within-draw warn / alarm |
|---|---|---|
| 1 | 100% / 100% | 100% / 100% |
| 2 | **100% / 99.9%** | 98.6% / 87.4% |
| 3 | **66.0% / 31.4%** | 43.4% / 11.3% |
| 12 (control) | **0.3%** false alarm | 0.7% |

Strictly better everywhere, including a lower false-alarm rate. λ stays analytic —
`pairs_examined × 48/1326` — so nothing is simulated at run time and no RNG is involved.

Demonstration with 32 cards whose only same-suit runs sit at draw boundaries:

```
reshuffle    pairs examined  48   found 0   expected 1.74   -> OK
dealthrough  pairs examined  90   found 1   expected 3.26   -> OK
             hits: AS and 2S (draw 1/2)
```

The old statistic could never have seen that pair; the new one names both draws.

### 5.2 Typed draws survive a settings change

`rebuild()` replaced the whole grid, so touching seed length, protocol or entropy margin silently
destroyed every card typed so far, with no warning and no undo — easy to trigger by switching
margin mid-session just to compare. Draws are now captured before the rebuild and restored
afterwards. If the new settings need fewer draws, the surplus is reported rather than dropped in
silence, with a note that the draw count is part of the derivation.

### 5.3 Keyboard flow

Enter in a completed draw's quick box moves to the next draw; Enter in the last draw derives, but
only when every draw is complete. Escape cancels the wipe countdown. Entering 56 cards no longer
needs the mouse.

### 5.4 Verification

- Golden vector unchanged; `DERIVATION_ID` untouched, so every existing draw record still
  reproduces its seed.
- 72 seeds across all six reachable mode combinations, all externally checksum-valid; 72 record
  PDFs, 6 blank sheets, `qpdf --check` clean.
- 23/23 self-tests, 9/9 sensitivity sweep, RNG audit clean.
- 0 shuffle-check false alarms in 72 well-shuffled sessions.
- Tamper test still bites: sabotaging the production derivation fails both golden vectors.

---

## Part 6 — v2.04: how the seed is presented in the browser

Threat model: the machine itself is trusted. A keylogged or malware-infected host is outside
anything a page can fix. What a page *can* reduce is how long the seed sits legible on a screen,
how long it sits on the clipboard, and whether the browser can bring the draws back afterwards.

### 6.1 What the audit found

Clean, measured on the shipped file: **0** absolute URLs, **0** `src`/`href` attributes, no
`@import`, no `url()`, no `fetch`/`XHR`/`WebSocket`/`sendBeacon`, no `<form>`, no cookies, and
**0** `console.*` calls. Nothing reaches a URL bar, a page title or a devtools console. The
quick-entry boxes already carried `spellcheck="false"`, which matters because Chrome's enhanced
spell check uploads typed text.

Three real gaps:

| Channel | Before |
|---|---|
| `#phraseText`, 12 word cells, `#detail` (phrase + entropy + preimage) | painted immediately, visible indefinitely, no blur, no idle timeout |
| Clipboard after Copy | written, never cleared |
| 64 card `<select>` elements | no `autocomplete="off"`, no `pagehide` handler |

### 6.2 Masking

The seed is now blurred on arrival and revealed only on request. Reveal re-hides after 20 idle
seconds, and immediately on `visibilitychange` or window blur — which is what screen-share
pickers, window switchers and operating-system thumbnails capture. Activity while revealed pushes
the deadline out, so writing 24 words onto metal by hand is not interrupted; walking away is.
`#detail` is masked by the same switch, since it carries the preimage and entropy as well.

Honest limit, stated in the tool: a CSS blur plus `user-select:none` defeats eyes and cameras, not
a browser extension reading the DOM. The wipe button remains the real answer.

### 6.3 Clipboard

Copy now starts a visible 60-second countdown on the button and then overwrites the clipboard.
The hint next to it says plainly that writing the words by hand is safer, that every application
on the machine can read the clipboard, and that a clipboard manager keeps history this page
cannot reach.

### 6.4 Browser restore

This was the only *persistent* leak. `autocomplete="off"` is now on all 64 card selects and all
3 setup selects, and a `pagehide` handler blanks every input, so session restore and the
back/forward cache have nothing to repopulate. Verified: 32 cards before `pagehide`, 0 after.

### 6.5 The tool caught my own change

Adding the two countdowns introduced `Date.now()`, and the page's own RNG audit immediately
reported **"Found: Date"**. The clock never touched the derivation — it only drove a UI counter —
but an audit that has to be explained away is worthless, so both timers now count whole ticks
instead. `grep` confirms the only remaining `Date` references are the audit's own regex and the
comment explaining why. Audit back to Clean.

### 6.6 Verification

- Golden vector unchanged; `DERIVATION_ID` untouched.
- 60 seeds across all six reachable modes, all externally checksum-valid, **60/60 masked by
  default** on arrival; 60 record PDFs and 6 blank sheets, `qpdf --check` clean.
- 23/23 self-tests, 9/9 sensitivity sweep, RNG audit Clean.
- Timer behaviour verified on a shortened build: reveal auto-hides on idle, survives continuous
  activity, and the clipboard is overwritten with a space when the countdown expires.
- Tamper test still bites: sabotaging the production derivation fails both golden vectors.

---

## Part 7 — v2.05: provenance, execution context, physical protocol

Derivation untouched. `DERIVATION_ID` is still `1deck-bip39-v2` and the golden vector still
yields `approve album veteran … write galaxy`.

### 7.1 Verify this file before you trust it (new section 7)

Measured on v2.04: **0** mentions of verifying the file's hash, **0** signature material. This
was the largest remaining hole — every other guarantee assumes you are running the genuine file,
and the RNG audit is self-referential, so a tampered copy simply reports "Clean".

The new section gives the exact command for each platform (`sha256sum`, `shasum -a 256`,
`Get-FileHash`) plus `minisign -Vm` and `gpg --verify`, and says three things plainly:

- **The page cannot hash itself.** A local page may not read its own bytes, and what JavaScript
  can see is a re-serialisation of the parsed document, not the file on disk. Any self-reported
  hash would be unverifiable and trivially faked.
- Compare against **more than one independent channel**. One compromised host can change the file
  and the hash beside it; it cannot as easily change the same value somewhere it does not control.
- A signature beats a bare hash, because it checks a key you already trusted rather than whatever
  the site says today.

The RNG audit's own text now points at this section and states it reads text and is not proof.

### 7.2 Execution-context check

Measured on v2.04: **0** checks of `location.protocol`, `navigator.onLine` or `isSecureContext`.

A banner now sits above everything else. Four states, all verified:

| `location.protocol` | `navigator.onLine` | Banner |
|---|---|---|
| `file:` | false | green — running locally, no network reported |
| `file:` | true | amber — the machine says it is online |
| `https:` | false | **red** — served from a web server |
| `https:` | true | **red** — served from a web server |

The red state says what matters: a server can send different code to different people, so nothing
you verified once still holds, and anything generated there should be treated as compromised. It
is advisory and says so — a hostile copy would just delete the check. It exists to catch the
ordinary mistake of clicking a link instead of downloading the file. No clock is read, so the RNG
audit stays Clean.

### 7.3 Wash first, and where the deck came from

"Wash" appeared exactly twice in v2.04, both in the footer; panel 1 and the printed sheet said
only *riffle*. A wash destroys factory order far faster than riffling, and every entropy figure
the tool quotes assumes that order is gone.

The wash is now step 2 of the printed sheet in capitals, the opening instruction of panel 1, and
the first bullet of the footer protocol. It is also named in the remedy text when the shuffle
check fires.

Deck provenance is now stated where it matters. The printed sheet's step 1 tells you to check for
drilled holes and clipped corners, because a cancelled casino deck resealed in a box can arrive in
a known order — and both the on-screen caveat and the PDF now say that such a deck **passes the
shuffle check regardless**, since the check assumes factory order specifically.

### 7.4 Verification

- Golden vector unchanged; panels renumber cleanly 1–8.
- 60 seeds across all six reachable modes, all externally checksum-valid; 60 record PDFs, 6 blank
  sheets, `qpdf --check` clean.
- 23/23 self-tests, 9/9 sensitivity sweep, RNG audit Clean.
- Context banner verified in all four protocol/online combinations.

### 7.5 Still open

- **Point 2 from the security review** — showing the BIP-32 master fingerprint so a seed can be
  checked against the wallet it restores into. Feasibility already proven: PBKDF2-HMAC-SHA512 and
  HMAC-SHA512 are native in WebCrypto, secp256k1 point multiplication is ~12 lines of BigInt, and
  the chain was verified end-to-end against the standard test mnemonic (XFP `73c5da0a`). Needs
  RIPEMD-160, about 60 lines, or an xpub instead which needs only SHA-256 and base58.
- **Point 4** — an optional second entropy source, to be extended to cover the overhand shuffle
  and three common real-world shuffling methods, then a guidance pass over the result.

---

## Part 8 — v2.06: shuffle methods, and the master fingerprint

Derivation untouched. `DERIVATION_ID` is still `1deck-bip39-v2`; golden vector unchanged.

### 8.1 Point 4 — how people actually shuffle

Each method was simulated against the tool's own shuffle statistic, from factory order, 3,000
sessions per row. Uniform expectation is 3.26 pairs; the check warns above 8.

| Method | Repetitions and measured mean |
|---|---|
| **Table riffle** | 1 → 24.7 · 3 → 9.2 (check fires 62%) · 4 → 5.3 · **5 → 3.8** · 7 → 3.31 |
| **Overhand / Hindu** | 1 → 24.4 · 5 → 13.3 · **10 → 7.4 (check still fires 30%)** · 25 → 3.7 · 50 → 3.30 |
| **Wash / smoosh** | reaches 3.3 almost immediately in the model; wash + 1 riffle already measures 3.28 |
| **Faro** | see below |

**Overhand is the finding worth publishing.** It is not wrong, it is *slow*: ten passes still leave
more than double the uniform pair count and trip the check three times in ten. It takes roughly
**50 passes** to settle. Most people do five or six. The tool now says so, with the numbers.

**Faro exposed a real limit of the shuffle check.** A perfect out-faro contains no randomness at
all — eight of them return a 52-card deck to its exact original order. Measured, two faros score
**0.00 adjacent pairs**, better than a genuinely random deck, so the check passes with a perfect
result on a deck holding zero entropy. This is now stated in the tool: a low score means the deck
does not look like a *new* deck. It never means the deck is random.

A **Shuffle method** selector in panel 1 shows the relevant guidance, colour-coded — riffle and
wash informational, overhand amber, faro red. It changes advice only; nothing about the
derivation.

The wash figure carries an honest caveat in the tool: the model idealises a wash as free random
exchanges, which is kinder than reality, where cards stay in loose clumps. Published work on
physical smooshing puts a good wash at 30–60 seconds, and that is what the tool tells you to do.

### 8.2 Point 2 — BIP-32 master fingerprint

Until now nothing could tell you the seed you are about to fund is the seed your wallet will
actually hold. The checksum only proves the words are well-formed; verify-by-re-entry only proves
you typed the same cards twice.

```
mnemonic → PBKDF2-HMAC-SHA512 (2048 iters, salt "mnemonic"+passphrase)  [WebCrypto]
         → HMAC-SHA512, key "Bitcoin seed"                              [WebCrypto]
         → secp256k1 public key                                         [~35 lines BigInt]
         → RIPEMD160(SHA256(pubkey))[0..4]                              [~50 lines]
```

Everything is deterministic — no randomness, no clock, nothing leaves the page. Verified in the
built-in self-test against published vectors, which is why the suite went from 23 to **28 checks**:

```
PASS  RIPEMD-160 matches all five known-answer vectors
PASS  secp256k1 + fingerprint match both BIP-32 specification vectors   (3442193e, bd16bee5)
PASS  Master fingerprint of the standard test mnemonic is 73c5da0a
PASS  BIP-39 seed with a passphrase matches the official vector          (c55257c3…)
PASS  A passphrase changes the fingerprint
```

**The fingerprint stays readable while the words remain blurred.** That is deliberate: a master
fingerprint is not a secret — it travels in every PSBT and signing devices display it openly — so
you can check it against your device without putting the seed on screen.

An optional passphrase field recomputes it live. The passphrase is cleared by the wipe and on
`pagehide`, and is deliberately **not** written into the PDF record, so that record stays
seed-equivalent rather than becoming a complete wallet backup.

**One bug caught in testing.** `renderFingerprint` wrote into `state.lastResult` before
`deriveSeed` had assigned it, so the value never reached the PDF. Moved after the assignment;
the PDF now carries it, verified 30/30.

### 8.3 Verification

- 30 seeds across five mode combinations: all checksum-valid, fingerprint matching an independent
  Node implementation **30/30**, present in the PDF **30/30**.
- 28/28 self-tests, 9/9 sensitivity sweep, RNG audit Clean, PDFs `qpdf --check` clean.
- Tamper test still bites: sabotaging the derivation fails both golden vectors.
