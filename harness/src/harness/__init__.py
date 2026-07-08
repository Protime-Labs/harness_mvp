"""Enterprise AI Assurance Harness — functional MVP reference prototype.

Architecture (clean / hexagonal). Dependencies point inward:

    interface  ->  application  ->  domain
         \\           |   \\          ^
          \\          v    \\         |
           +----->  ports  <+--- adapters

  - domain/       B0 contracts, B1 invariants, B5 gate, risk & aggregation — PURE (stdlib only).
  - ports/        the seams: ModelPort (B2), EvidencePort (B4), Detector, HarnessDriver (B3).
  - application/  the workflows W0-W9: contextualize, select, run, judge, govern, replay, calibrate.
  - adapters/     concrete plugs: mock/LiteLLM models, regex/Presidio detectors, file evidence, drivers.
  - interface/    the composition root: CLI wires adapters into the application.

Keystone invariant A1: agents generate & judge (data plane); deterministic policy decides
(control plane). No LLM ever runs in the gate/risk path.
"""

__version__ = "0.1.0"
