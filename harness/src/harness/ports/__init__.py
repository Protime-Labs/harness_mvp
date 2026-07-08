"""Ports — the seams. Abstract interfaces the application depends on; adapters implement them.

  - ModelPort     (B2)  the single model I/O path       <- Janus, providers, Model Router plug here
  - EvidencePort  (B4)  chain-of-custody + replay store  <- audit, remediation, SIEM read here
  - Detector            deterministic content detector    <- Presidio / scanners plug here
  - HarnessDriver (B3)  the execution shape               <- agentic overlay, PyRIT/Garak plug here

Depending on these (not on concrete classes) is what makes the framework evolve by
*implementing a seam* instead of rewriting the core.
"""
