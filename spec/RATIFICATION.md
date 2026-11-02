# How to ratify this capsule's invariant set

This is the only open item that cannot be closed by writing more code, and it
is deliberately cheap to close by someone who did not write the code.

## Why it exists

`R3` validated against `spec/meta_invariants.json` establishes
`R3 |= M` and nothing more. If `M` was written by the same agent that runs
`Phi` — which it was — then `M` was written already knowing which defects it
would be asked to find, and the certificate is vacuous. See Proposition 4.

## What ratification is not

It is not approval of the conclusions, the code, or the paper. It is a
narrower claim: *that this invariant set is a reasonable standard to hold this
kind of artefact to, judged without having seen which defects it catches.*

## Procedure

1. Read `spec/meta_invariants.json`. Ignore the rest of the capsule while you
   do; the point is to judge the standard, not the thing being judged.
2. Decide whether M1-M8 are the right invariants. Add, remove or reword as you
   see fit, and edit the file directly if so — a ratification of a set you
   changed is worth more than a ratification of mine.
3. Compute the hash of the file as it then stands:

       python3 -c "import hashlib;print(hashlib.sha3_256(open('spec/meta_invariants.json','rb').read()).hexdigest())"

4. Write `spec/ratification.json`:

       {
         "attestor": "name, role, and a way to contact you",
         "attested_sha3": "<the hash from step 3>",
         "attested_utc": "YYYY-MM-DDTHH:MM:SSZ",
         "statement": "what you are attesting to, in your own words",
         "independent": true
       }

5. Run `python3 src/ratify.py`. It should print `RATIFIED`.

## What happens if the invariants are edited afterwards

The hash stops matching and `ratify.py` returns `REVOKED_BY_EDIT`. You cannot
ratify a set and then quietly change it. That is the whole mechanism.

## Obligation 6

Ratification closes M6. It does NOT close Obligation 6, which asks for
comparison against data from outside the calibration set. That needs an
external benchmark, not a signature, and the capsule does not pretend
otherwise.
