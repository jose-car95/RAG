"""Ports: what the use cases need from the outside, without knowing who.

Each port is a ``Protocol``. An outbound adapter names the port it
implements (``class FileCorpus(CorpusReader)``) so the link is visible and
mypy checks that every method is there; ``bootstrap`` plugs it in.
"""
