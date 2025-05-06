import os
from pathlib import Path
from typing import Optional


class RichGmailMessageTemplate:
    """
    Base class for a rich email template.

    - TODO:
        1. support for simple keyword fills from a csv
        2. support for llm fills
    """

    def __init__(self, markdown_fp: str, attachments: Optional[list[Path]]) -> None:
        self.path = Path(markdown_fp)
        assert self.path.exists()
