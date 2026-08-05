# Recovering your seed phrase on iancoleman.io/bip39

If this generator is ever gone, you do not need it. Your PDF seed record prints everything
required. This guide starts from one line of that record:

```
Step 3. The leading 128 bits of that digest are the entropy:
        56cd7feb1647fd133477bc54589f7c2d
```

That hex string is your entropy. Every BIP-39 implementation on earth can turn it back into your
words, and iancoleman's tool is the most widely available one. Below is exactly how, verified by
running it.

*(The example throughout uses the entropy above. Substitute your own.)*

---

## Before you start

Do this **offline**. Download the iancoleman page (the "Standalone version" link at the bottom of
the site), disconnect the machine, and open the saved file. Pasting a live seed's entropy into a
page served over the internet defeats the point.

---

## The steps

**1. Open the saved iancoleman BIP-39 page.**

**2. Find the *Entropy* section.** If the entropy field is not visible, tick **Show entropy
details**.

**3. Set *Entropy Type* explicitly to `Hex`.**

Do not rely on auto-detection. The tool picks the *lowest* base that fits your characters, so an
entropy that happens to contain no letters `a`–`f` would be read as base-10 and give you the wrong
seed silently. That happens for roughly 1 entropy in 3.4 million — rare enough to never see, and
catastrophic if you do. Setting the type takes one click.

**4. Leave *Mnemonic Length* on `Use Raw Entropy (3 words per 32 bits)`.**

This is the setting that matters most, and it is counterintuitive.

`Use Raw Entropy` means "these bits *are* the entropy" — which is exactly what you want, because
your entropy has already been derived. Any other setting makes the tool run SHA-256 over what you
typed, **hashing your entropy a second time** and producing a completely different seed.

For the example above, the wrong setting gives:

| Setting | Resulting first words |
|---|---|
| ✅ `Use Raw Entropy` | `fine hip width clutch lemon maze spike…` |
| ❌ `12 Words` (lowercase hex) | `rent around hurdle coral cube switch…` |
| ❌ `12 Words` (uppercase hex) | `wet salute clap produce electric accuse…` |

All three are valid BIP-39 phrases. Only the first is yours.

**5. Paste your entropy into the *Entropy* field.**

```
56cd7feb1647fd133477bc54589f7c2d
```

32 hex characters for a 12-word seed, 64 for a 24-word seed. Case does not matter in raw mode.

**6. Read your seed phrase from the *BIP39 Mnemonic* box.**

```
fine hip width clutch lemon maze spike wasp february shaft tenant force
```

It should appear immediately and match your record word for word.

---

## Check it before you trust it

Compare at least one of these against your PDF record. If any disagree, stop.

**Master fingerprint.** Scroll to *Derivation Path*, and read the **BIP32 Root Key** area. For the
example:

```
XFP  B8428EFE
```

**First two receive addresses.** Select the **BIP84** tab under *Derivation Path* — this is native
SegWit, `m/84'/0'/0'/0`, the same path this generator reports. The first two addresses in the
table should be:

```
m/84'/0'/0'/0/0   bc1qv96hhcapy3x55jk8w59nsxeut5vytnuga8fn6l
m/84'/0'/0'/0/1   bc1qp3phvf9aagm6t74geaspmcpy3vac9h0mt827my
```

Matching addresses are the strongest confirmation available: they prove the entropy, the words,
the derivation path and the wallet software all agree.

---

## If you only have the cards, not the entropy

Recompute the entropy first, then start at step 3 above. One command:

```bash
printf '%s' '1deck-bip39-v2|12|TD KD 8H 5C TS 2D 8C JH 8C 9C KH TC KD 7H 3S QH 8H 7H AD JH 7S KS 5S 6C 5D QH 7S 3C AC JS QS 3H' | sha256sum | cut -c1-32
→ 56cd7feb1647fd133477bc54589f7c2d
```

For a 24-word seed use `|24|` and keep all 64 hex characters. Details in
*Entropy method, comparison and recovery*, §3.2.

---

## Why you cannot paste the cards straight into iancoleman

You can, and it will produce a seed — just not *your* seed. Its card mode uses a different
encoding: each card becomes a 5-, 4- or 2-bit code and those bits are used directly, where this
generator hashes the whole sequence. Same cards, different method, different words. Both are valid
BIP-39; they are simply not the same derivation.

The entropy hex is the bridge between the two. Once you are holding the entropy, every tool
agrees.

---

## Summary card

Worth copying onto the draw sheet or the back of the PDF:

```
RECOVERY WITHOUT THE GENERATOR
1. entropy = first 32 hex chars of:
      printf '%s' '1deck-bip39-v2|12|<your cards>' | sha256sum
   (or read it from the PDF record, Step 3)
2. iancoleman.io/bip39, offline copy
3. Entropy Type = Hex
4. Mnemonic Length = Use Raw Entropy      <- not "12 Words"
5. paste the entropy -> the phrase appears
6. verify: BIP84 tab, first address matches your record
```
