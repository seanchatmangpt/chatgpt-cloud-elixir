"""Regular package marker for the repository test suite.

Without this file `tests` is a namespace package, and any regular package named
`tests` installed in site-packages wins the import, so
`python3 -m unittest tests.test_xaas_relay` (the Remote Relay Live-Leg Court
command) fails with ModuleNotFoundError before a single relay test runs.
"""
