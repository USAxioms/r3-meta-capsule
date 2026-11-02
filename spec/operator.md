# Operator type declarations

    D            design space (here: formalisation states)
    C subset D   feasible set cut out by the hard invariants

    A    : D -> D x Sigma        audit; emits outstanding-violation summary
    F    : D x Sigma -> D        refinement
    Proj : D -> C                validation as projection (NOT rejection)

    Phi  = Proj . F . A : C -> C          total on C
    R3   = lfp(Phi)

`I` in the source expression `I . V . F . A` is the least-fixed-point
combinator, not a factor in a composition. The source expression does not
type-check and is retained only as informal shorthand.

## Existence routes (exactly one must be declared in manifest.json)

    lattice      Knaster-Tarski: (C, <=) complete lattice, Phi monotone
    metric       Banach: (C, ||.||) complete, Phi L-Lipschitz with L < 1
    termination  well-founded measure mu with mu(Phi(d)) < mu(d) when Phi(d) != d

This capsule declares `termination`. It therefore makes NO uniqueness claim and
emits NO a-posteriori error bound: certify.py returns NO_CONTRACTION by design,
not by failure.
