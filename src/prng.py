"""splitmix64: a declared, deterministic PRNG. Satisfies D4.

No system entropy, no time, no OS randomness. Reproducible across platforms
and Python versions because every operation is masked to 64 bits.
"""
MASK = (1 << 64) - 1


class SplitMix64(object):
    def __init__(self, seed):
        self.state = seed & MASK

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def randint(self, lo, hi):
        """Uniform on [lo, hi] inclusive, by rejection (no modulo bias)."""
        span = hi - lo + 1
        limit = (1 << 64) - ((1 << 64) % span)
        while True:
            v = self.next_u64()
            if v < limit:
                return lo + (v % span)

    def unit_wad(self):
        """Uniform on [0,1) as a WAD-18 value. Floor-rounded from 53 raw bits;
        no float is constructed at any point."""
        import os, sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import wad18 as W
        return (self.next_u64() >> 11) * W.SCALE // (1 << 53)
