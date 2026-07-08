"""
ports/font_converter.py
=======================

PURPOSE
-------
The seam between the pipeline and piliwela. The core depends on this small
interface, never the piliwela module directly -- so it can be faked in tests and
swapped/upgraded without touching any stage.

THE CONTRACT
------------
    convert(text, font) -> str

Given one span's raw text and its font name, return the correct Unicode:
    * legacy font (FMAbhaya, DL-..., etc.) -> convert legacy bytes to Unicode Sinhala
    * non-legacy font (Arial, Times, ...) -> return the text unchanged

Deciding "Sinhala vs English typed in a legacy font" is the CONVERTER'S job
(piliwela's dictionary filter), not the caller's. The caller passes every span
through and trusts the contract.
"""

from __future__ import annotations

from typing import Protocol


class FontConverter(Protocol):
    def convert(self, text: str, font: str) -> str:
        ...
