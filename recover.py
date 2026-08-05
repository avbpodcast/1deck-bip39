#!/usr/bin/env python3
"""
Rebuild a BIP-39 seed phrase from a 1-deck card draw record, without the generator.

Standard library only: hashlib. Needs the official BIP-39 English wordlist as a text file,
one word per line (sha256 2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda).

    python3 recover.py english.txt 12 "TD KD 8H 5C TS 2D 8C JH ..."
"""
import hashlib, sys

DERIVATION_ID = "1deck-bip39-v2"      # frozen; part of the derivation, never the version number

def seed_phrase(wordlist, words_wanted, cards):
    entropy_bits = 128 if words_wanted == 12 else 256
    preimage = "%s|%d|%s" % (DERIVATION_ID, words_wanted, cards)
    digest   = hashlib.sha256(preimage.encode("utf-8")).digest()
    entropy  = digest[: entropy_bits // 8]
    checksum = hashlib.sha256(entropy).digest()[0]
    bits  = "".join(bin(b)[2:].zfill(8) for b in entropy)
    bits += bin(checksum)[2:].zfill(8)[: entropy_bits // 32]
    words = [wordlist[int(bits[i:i+11], 2)] for i in range(0, len(bits), 11)]
    return preimage, entropy.hex(), " ".join(words)

if __name__ == "__main__":
    path, n, cards = sys.argv[1], int(sys.argv[2]), " ".join(sys.argv[3:]).upper()
    wl = [w.strip() for w in open(path, encoding="utf-8") if w.strip()]
    assert len(wl) == 2048, "wordlist must have exactly 2048 words, got %d" % len(wl)
    pre, ent, phrase = seed_phrase(wl, n, cards)
    print("preimage : %s" % pre)
    print("entropy  : %s" % ent)
    print("phrase   : %s" % phrase)
