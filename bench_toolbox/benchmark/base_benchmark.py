# coding: UTF-8

from __future__ import annotations

import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Tuple, Type

from coloredlogs import ColoredFormatter

from ..monitors import MonitorData
from ..monitors.base_monitor import BaseMonitor
from ..monitors.pipelines import BasePipeline, DefaultPipeline


class BaseBenchmark(metaclass=ABCMeta):
    _file_formatter = ColoredFormatter(
            '%(asctime)s.%(msecs)03d [%(levelname)s] (%(funcName)s:%(lineno)d in %(filename)s) $ %(message)s')
    _stream_formatter = ColoredFormatter('%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)14s $ %(message)s')

    def __new__(cls: Type[BaseBenchmark],
                identifier: str,
                workspace: Path,
                logger_level: int = logging.INFO) -> BaseBenchmark:
        obj: BaseBenchmark = super().__new__(cls)

        obj._identifier = identifier

        obj._monitors: Tuple[BaseMonitor[MonitorData], ...] = tuple()
        obj._pipeline: BasePipeline = DefaultPipeline()

        # setup for logger
        log_dir = workspace / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

        obj._log_path: Path = log_dir / f'{identifier}.log'

        logger = logging.getLogger(identifier)
        logger.setLevel(logger_level)

        return obj

    @abstractmethod
    async def start_and_pause(self, silent: bool = False) -> None:
        pass

    @abstractmethod
    async def monitor(self) -> None:
        pass

    @abstractmethod
    def pause(self) -> None:
        pass

    @abstractmethod
    def resume(self) -> None:
        pass

    @abstractmethod
    async def join(self) -> None:
        pass

    def _remove_logger_handlers(self) -> None:
        logger: logging.Logger = logging.getLogger(self._identifier)

        for handler in tuple(logger.handlers):  # type: logging.Handler
            logger.removeHandler(handler)
            handler.flush()
            handler.close()

    @property
    def identifier(self) -> str:
        return self._identifier

    @abstractmethod
    def all_child_tid(self) -> Tuple[int, ...]:
        pass
