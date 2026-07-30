from __future__ import annotations
import hashlib
import numpy as np

MOD = 2**63 - 25

def domain_seed(*parts: object) -> int:
    s = '|'.join(str(p) for p in parts)
    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
    return int(h[:16], 16) % MOD

def sha_arr(a) -> str:
    return hashlib.sha256(np.asarray(a, dtype=np.int8).tobytes()).hexdigest()[:16]
