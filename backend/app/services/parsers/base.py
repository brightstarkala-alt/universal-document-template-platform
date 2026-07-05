"""
Contract every format adapter implements: given raw bytes, return
`ParsedContent` (a Universal Document Model's units + structural stats,
minus the file-identity/timing envelope only the orchestrator can know).

Adapters are pure — no Storage, database, or HTTP imports anywhere under
app/services/parsers/. `app/services/parser_service.py` is the only layer
that touches those, which is what lets parsing evolve into a
background-job model later without this contract changing.
"""

from typing import Protocol

from app.schemas.document_model import ParsedContent


class Parser(Protocol):
    name: str
    version: str

    def parse(self, content: bytes) -> ParsedContent: ...
