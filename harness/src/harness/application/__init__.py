"""Application layer — the workflows (W0-W9). Depends on domain + ports only (never adapters).

  contextualize (W1) -> select (W2) -> run (W3/B3) -> judge quorum (W7) -> govern (H5.1)
                                                     -> gate (W8/B5, domain) -> report
  plus: replay (Mode-A), calibrate (C1), remediation (W9), acceptance (invariant suite).

Concrete adapters are injected by the composition root (interface/), so this layer is
provider-independent and unit-testable with the mock.
"""
