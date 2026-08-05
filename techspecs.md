# 1-Deck Card → BIP-39 · Technical specification

Generator version 2.13 · derivation id `1deck-bip39-v2`

This document specifies the derivation completely enough to reimplement it from scratch. Every
value shown was produced by executing the code, and the worked example in §9 carries every
intermediate so that an independent implementation can be checked step by step.

---

## 1. Scope

The generator turns physically drawn playing cards into a BIP-39 mnemonic. It contains no random
number generator, no clock access and no network access: no absolute URLs, no `src`, no `fetch`,
`XHR`, `WebSocket` or `sendBeacon`. The footer carries two relative links to documentation files
kept alongside it (`howitworks.pdf`, `techspecs.md`); these resolve against the local folder and
retrieve nothing. The derivation is a pure function of the cards and the chosen word count.

```
cards + word count  →  entropy  →  BIP-39 mnemonic  →  BIP-39 seed  →  BIP-32 master key
                                                                    →  master fingerprint
                                                                    →  BIP-84 addresses
```

Only the first arrow is specific to this tool. Everything after `entropy` is standard BIP-39,
BIP-32 and BIP-84, and is reproduced here only so the whole chain can be verified in one place.

---

## 2. Card representation

### 2.1 External form — what the user writes and what is hashed

A card is two ASCII characters: rank then suit, uppercase.

```
rank  A 2 3 4 5 6 7 8 9 T J Q K        T = ten
suit  C = clubs   D = diamonds   H = hearts   S = spades
```

So `TD` is the ten of diamonds, `AS` the ace of spades. This two-character form is the *only*
representation that enters the hash. Fixed width and a single space between cards makes the
preimage unambiguous: no card code is a prefix of another, and the encoding is injective.

### 2.2 Internal form — index, used only for validation and statistics

```
index = suit_number × 13 + rank_number

rank_number   A=0, 2=1, 3=2, …, 9=8, T=9, J=10, Q=11, K=12
suit_number   C=0, D=1, H=2, S=3
```

Range 0–51. `AC` = 0, `KS` = 51. This index is used for duplicate detection and for the shuffle
statistic in §8. **It never enters the derivation.** Reimplementations may ignore it entirely.

---

## 3. Draw structure and entropy accounting

### 3.1 A draw

A draw is four *distinct* cards recorded in the order dealt. Order is significant.

```
ordered draws of 4 from 52   P(52,4) = 52 × 51 × 50 × 49 = 6,497,400
                             log₂(6,497,400) = 22.6314 bits
unordered (for comparison)   C(52,4) = 270,725 → 18.0466 bits
```

### 3.2 Protocols

**Reshuffle** — cards returned and the full deck reshuffled between draws. Draws are independent;
*n* draws carry `22.6314 × n` bits.

**Deal-through** — one shuffle per *pass*, cards dealt off the top without replacement. Dealing
*m* ordered cards from one deck carries

```
Σ(i = 0 … m−1) log₂(52 − i)
```

### 3.3 Draw counts

| Word count | Entropy bits *N* | Margin mode | Minimum mode |
|---|---|---|---|
| 12 | 128 | 8 draws | 6 draws |
| 24 | 256 | 14 draws | 12 draws |

### 3.4 Pass layout for deal-through

Draws are distributed as evenly as possible across passes, not packed to 52 cards per pass,
because the tail of a pass is nearly worthless (the 52nd card contributes log₂(1) = 0 bits).

```
minPasses = ceil(draws × 4 / 52)
for p = minPasses … min(draws, 4):
    layout = draws split evenly into p parts, larger parts first
    if any part × 4 > 52: skip
    bits = Σ over parts of Σ(i = 0 … 4·part−1) log₂(52 − i)
    if bits ≥ N + 24: use this layout      ← first layout with comfortable head-room wins
keep the best layout seen otherwise
```

Deal-through is **unavailable for 24 words**: one deck ordering is worth at most
log₂(52!) = 225.58 bits, so a 256-bit seed can never come from a single shuffle.

### 3.5 Head-room

| Word count | Mode | Protocol | Layout | Card bits in | Extracted | Head-room |
|---|---|---|---|---|---|---|
| 12 | margin | reshuffle | 1×8 | 181.05 | 128 | +53.05 |
| 12 | margin | deal-through | 8 | 164.50 | 128 | +36.50 |
| 12 | minimum | reshuffle | 1×6 | 135.79 | 128 | +7.79 |
| 12 | minimum | deal-through | 2,2,1,1 | 134.80 | 128 | +6.80 |
| 24 | margin | reshuffle | 1×14 | 316.84 | 256 | +60.84 |
| 24 | minimum | reshuffle | 1×12 | 271.58 | 256 | +15.58 |

Head-room is what makes SHA-256 act as a randomness extractor rather than a relabelling. It is
the margin that absorbs an imperfect shuffle.

---

## 4. Entropy derivation — the part unique to this tool

### 4.1 Preimage

```
preimage = DERIVATION_ID ‖ "|" ‖ word_count ‖ "|" ‖ card₁ ‖ " " ‖ card₂ ‖ … ‖ cardₖ
```

- `DERIVATION_ID` = the ASCII string `1deck-bip39-v2`, **frozen**, never tied to the program
  version. Versions 2.01 and 2.13 derive identically.
- `word_count` = decimal `12` or `24`.
- Cards in draw order, then card order within each draw, uppercase, single ASCII spaces, no
  trailing space, no terminating newline.
- The whole preimage is ASCII; encode as UTF-8 (identical for ASCII).

### 4.2 Entropy

```
N       = 128 if word_count = 12, else 256
entropy = first N bits (N/8 bytes) of SHA-256(preimage)
```

The digest is taken over the preimage bytes. The leading bytes are used; the remainder is
discarded.

---

## 5. Mnemonic — standard BIP-39

```
CS       = N / 32                                    4 bits for N=128, 8 for N=256
checksum = first CS bits of SHA-256(entropy)
bitstring = entropy_bits ‖ checksum_bits            132 bits for 12 words, 264 for 24
```

Split `bitstring` into 11-bit groups, most significant first. Each group is an index 0–2047 into
the official BIP-39 English wordlist.

The wordlist must be the canonical one: 2048 entries, sorted, unique 4-character prefixes,

```
SHA-256 of the list, one word per line, trailing newline:
2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda
```

---

## 6. Seed and BIP-32 master key — standard BIP-39 / BIP-32

```
mnemonic_nfkd = NFKD(words joined by single spaces)
salt          = NFKD("mnemonic" ‖ passphrase)        passphrase may be empty
bip39_seed    = PBKDF2-HMAC-SHA512(mnemonic_nfkd, salt, 2048 iterations, 64 bytes)

I          = HMAC-SHA512(key = ASCII "Bitcoin seed", message = bip39_seed)
master_key = I[0..32]        master_chaincode = I[32..64]
```

A BIP-39 passphrase changes the seed and therefore everything below it. The generator never
writes a passphrase into the PDF record.

---

## 7. Fingerprint and addresses

### 7.1 Master fingerprint (XFP)

```
master_pubkey = secp256k1 compressed public key of master_key
                (33 bytes: 0x02 if Y even else 0x03, then X big-endian)
hash160       = RIPEMD160(SHA-256(master_pubkey))
fingerprint   = first 4 bytes of hash160, hex
```

This is the value hardware wallets display as XFP / master key fingerprint / root fingerprint. It
is public information — it appears in every PSBT — so the generator shows it while the words stay
blurred.

### 7.2 Child key derivation (BIP-32, private parent → private child)

```
if index ≥ 0x80000000 (hardened):  data = 0x00 ‖ parent_key ‖ index_be32
else:                              data = compressed_pubkey(parent_key) ‖ index_be32

I  = HMAC-SHA512(key = parent_chaincode, message = data)
child_key       = (I[0..32] + parent_key) mod n
child_chaincode = I[32..64]

n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
reject and increment index if I[0..32] ≥ n or child_key = 0
```

### 7.3 Addresses (BIP-84, native SegWit)

Path `m/84'/0'/0'/0/i`, i.e. indices `84+2³¹`, `0+2³¹`, `0+2³¹`, `0`, `i`.

```
pubkey  = compressed secp256k1 public key of the child key
program = RIPEMD160(SHA-256(pubkey))                   20 bytes
address = bech32("bc", [0x00] ‖ convertbits(program, 8, 5, pad=true))
```

Witness version 0, so the bech32 checksum constant is 1 (not bech32m).

---

## 8. Shuffle-quality statistic (advisory only — not part of the derivation)

Counts pairs of cards that are **same suit and one rank apart**, among cards dealt within
`W = 3` positions of each other inside the same pass.

```
positions examined per pass of length L:  Σ(d = 1 … 3) max(0, L − d)
adjacent pairs in a deck:                 4 suits × 12 = 48
P(two random distinct cards adjacent):    48 / C(52,2) = 48 / 1326 = 0.036199
λ = 0.036199 × (positions examined)
```

Thresholds are the Poisson tails of λ at 1 % (warning) and 0.1 % (strong alarm); nothing is
simulated at run time.

| Configuration | Pairs examined | λ | Warn above | Alarm above |
|---|---|---|---|---|
| 8 draws, reshuffle | 48 | 1.74 | 5 | 7 |
| 8 draws, deal-through (one pass of 32) | 90 | 3.26 | 8 | 10 |

Two limits, stated because they matter:

- It assumes the deck started in **factory order**. A deck in some other known order — a cancelled
  casino deck resealed in a box — passes regardless.
- A low score means the deck does not look like a *new* deck. It never means the deck is random.
  Measured: two perfect faro shuffles score **0.00** pairs, better than a random deck, while the
  ordering is fully deterministic.

Separately, two patterns are flagged because a shuffled deck almost never deals them: **≥ 2 draws
that are a straight run of ranks**, and **≥ 3 draws that are all one suit**. Measured false-alarm
rates over 200,000 random sessions: 0.002 % and 0.008 % at 8 draws.

---

## 9. Complete worked example

Every intermediate value, 12 words, reshuffle protocol, margin mode, 8 draws, no passphrase.

**Input**

```
TD KD 8H 5C   TS 2D 8C JH   8C 9C KH TC   KD 7H 3S QH
8H 7H AD JH   7S KS 5S 6C   5D QH 7S 3C   AC JS QS 3H
```

**Preimage** — 113 bytes of ASCII

```
1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H
```

**Entropy**

```
SHA-256(preimage) = 56cd7feb1647fd133477bc54589f7c2d5eefb33dec0fac06f085518495a628a2
entropy (128 b)   = 56cd7feb1647fd133477bc54589f7c2d
```

**Checksum**

```
SHA-256(entropy)  = 8d228cb19edc18fe9b18551bafbe5e0d32d45f211d3a82f0c5416b83889769ba
first byte        = 10001101
checksum (4 bits) = 1000
```

**Bit string** — 132 bits

```
01010110110011010111111111101011000101100100011111111101000100110011
0100011101111011110001010100010110001001111101111100001011011000
```

**Word indices**

```
694  863  2006  356  1022  1100  1678  1980  674  1575  1784  728
```

**Mnemonic**

```
fine hip width clutch lemon maze spike wasp february shaft tenant force
```

**BIP-39 seed** — PBKDF2-HMAC-SHA512, 2048 iterations, salt `mnemonic`

```
dd8c5518647d1e2dee54b2af3187c93f67af875560c7885af60c47142613206f
f2862a7881592f04d95dfeb67ce7f61c0049cbb107468ecc507bfaabb28e28d6
```

**BIP-32 master**

```
key        3302869330d82c9ad0a11eb5d85da600a9e7a26b0b1fa50c1fa359f9535aa263
chaincode  d3f0307341a17d2b284f8b0bb8e105bb0229c8ec11b10ff93e06612fe2d27805
pubkey     027580d3fc6f29f035cb49ea50cdcaf5208629931c795140fd0228b8cab483d9a4
hash160    b8428efe9b1e08d0f2478a05fd5a70a9b95de2c3
XFP        B8428EFE
```

**BIP-84 addresses**

```
m/84'/0'/0'/0/0
  pubkey   033273207425a4f75c7e869bc21231f2226550472f9219072007fadc85984b619c
  hash160  61757be3a1244d4a4ac7750b381b3c5d1845cf88
  address  bc1qv96hhcapy3x55jk8w59nsxeut5vytnuga8fn6l

m/84'/0'/0'/0/1
  pubkey   034911ab21db4007f288b97d7effa5f1f6643bf151a171fb5dbeca93f2e41baf5a
  hash160  0c437624bdea37a5faa8cf601de0248b3b82ddfb
  address  bc1qp3phvf9aagm6t74geaspmcpy3vac9h0mt827my
```

---

## 10. Test vectors

### 10.1 This derivation

| | 12-word | 24-word |
|---|---|---|
| Cards | `AS 7H TD 3C KD 2S 9C JH 4H QS 6D 8C TC AD 5S 7D 3H JC KS 2D 9H 4C QD 6S 8S TH AC 5D 2H 6C JS 4D` | see the generator's self-test |
| Entropy | `0ac0bfccc2295a93fed4973168bffa2f` | `2f1ec656ea10b9fba9169a42a1128631a429d0b54b55d5b093f4f1714d01af94` |
| Mnemonic | `approve album veteran lounge noble enemy win napkin cousin echo write galaxy` | `congress wage noble stage argue worry picture spy dress ancient pave globe dream tribe steel height stick loyal wood title below liar salad original` |

### 10.2 Standards conformance, all verified in the built-in self-test

| Standard | Vector | Expected |
|---|---|---|
| BIP-39 | entropy `00000000000000000000000000000000` | `abandon abandon … abandon about` |
| BIP-39 | entropy `7f7f…7f` | `legal winner thank year … yellow` |
| BIP-39 | entropy `8080…80` | `letter advice cage absurd … cage above` |
| BIP-39 | entropy `ffff…ff` (256-bit) | `zoo zoo zoo … zoo vote` |
| BIP-39 | `abandon…about` + passphrase `TREZOR` | seed `c55257c360c07c72029aebc1b53c05ed…` |
| BIP-32 | seed `000102030405060708090a0b0c0d0e0f` | fingerprint `3442193e` |
| BIP-32 | seed `fffcf9f6…4542` | fingerprint `bd16bee5` |
| BIP-84 | `abandon…about`, m/84'/0'/0'/0/0 | `bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu` |
| BIP-84 | `abandon…about`, m/84'/0'/0'/0/1 | `bc1qnjg0jd8228aq7egyzacy8cys3knf9xvrerkf9g` |
| RIPEMD-160 | `""`, `"a"`, `"abc"`, `"message digest"`, `a…z` | five published digests |
| Wordlist | official English list | `2f5eed53…3b24dbda` |

---

## 11. Reimplementation notes

Pitfalls that will silently produce a different seed:

1. **A trailing newline in the preimage.** Use `printf '%s'`, never `echo`.
2. **Lowercase cards or `10` instead of `T`.** The preimage is uppercase, two characters per card.
3. **Sorting a draw.** Order is significant; record cards as dealt.
4. **Omitting the `DERIVATION_ID|word_count|` prefix.**
5. **Hashing the entropy again.** The entropy is the *output* of SHA-256, not an input to it.
   This is the most common recovery error — see the note on other tools' "raw entropy" settings.
6. **Taking trailing rather than leading bits** of the digest.

The minimal recovery path needs only SHA-256 and the wordlist. A dependency-free implementation is
provided as `recover.py`; the derivation itself is four lines.

---

## 12. Reference files

| File | SHA-256 |
|---|---|
| `1-Deck Casino Card BIP-39 Seed Generator v2.13.html` | `1e7a1754b6f7ce53085917a82c237bb2086d2430112c443c1d27ab02ec60c45f` |
| `recover.py` | `9f75dea67ebcabd08cbcb62ce70a09256a2ed21a1fbe72d4c6dff3956568dea9` |
| `BIP-39 english wordlist.txt` | `2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda` |

Verify the generator's hash against a copy published somewhere the file's host does not control.
The page cannot hash itself: a local page may not read its own bytes, and any self-reported hash
would be unverifiable and trivially faked.
