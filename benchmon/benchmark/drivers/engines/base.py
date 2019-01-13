# coding: UTF-8

from __future__ import annotations

import asyncio
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...base import BaseBenchmark


class BaseEngine(metaclass=ABCMeta):
    _benchmark: BaseBenchmark

    def __init__(self, benchmark: BaseBenchmark) -> None:
        super().__init__()

        self._benchmark = benchmark

    @abstractmethod
    async def launch(self, *cmd: str, **kwargs) -> asyncio.subprocess.Process:
        pass