# coding: UTF-8

from __future__ import annotations

import asyncio
from typing import Mapping, TYPE_CHECKING, Union

from .base import BaseMonitor
from .messages import PerBenchMessage
from .pipelines import BasePipeline
from ..benchmark import BaseBenchmark
from ..utils.asyncio_subprocess import check_output

if TYPE_CHECKING:
    from .. import Context
    from ..configs.containers import PerfConfig

DAT_TYPE = Mapping[str, Union[int, float]]


class PerfMonitor(BaseMonitor[PerBenchMessage, DAT_TYPE]):
    __slots__ = ('_perf_config', '_is_stopped')

    _perf_config: PerfConfig
    _is_stopped: bool

    def __init__(self, perf_config: PerfConfig) -> None:
        super().__init__()

        self._perf_config = perf_config
        self._is_stopped = False

    async def _monitor(self, context: Context) -> None:
        benchmark = BaseBenchmark.of(context)

        perf_proc = await asyncio.create_subprocess_exec(
                'perf', 'stat', '-e', self._perf_config.event_str,
                '-p', str(benchmark.pid), '-x', ',', '-I', str(self._perf_config.interval),
                stderr=asyncio.subprocess.PIPE)

        if self._perf_config.interval < 100:
            version_line: bytes = await check_output('perf', '--version', stderr=asyncio.subprocess.DEVNULL)
            version_str: str = version_line.decode().split()[2]
            major, minor = map(int, version_str.split('.')[:2])  # type: int, int
            if (major, minor) < (4, 17):
                # remove warning message of perf from buffer
                await perf_proc.stderr.readline()

        record = dict.fromkeys(event.alias for event in self._perf_config.events)

        while not self._is_stopped and perf_proc.returncode is None:
            ignored = False

            for event in self._perf_config.events:
                raw_line = await perf_proc.stderr.readline()

                line: str = raw_line.decode().strip()
                line_split = line.split(',')

                try:
                    if line_split[1].isdigit():
                        record[event.alias] = int(line_split[1])
                    else:
                        record[event.alias] = float(line_split[1])
                except (IndexError, ValueError):
                    ignored = True

            if not self._is_stopped and not ignored:
                msg = await self.create_message(context, record.copy())
                await BasePipeline.of(context).on_message(context, msg)

        if perf_proc.returncode is None:
            try:
                perf_proc.kill()
            except ProcessLookupError as e:
                context.logger.debug(f'The perf kill was unsuccessful for the following reasons: {e}', e)

    async def stop(self) -> None:
        self._is_stopped = True

    @property
    async def is_stopped(self) -> bool:
        return self._is_stopped

    @property
    def config(self) -> PerfConfig:
        return self._perf_config

    async def create_message(self, context: Context, data: DAT_TYPE) -> PerBenchMessage[DAT_TYPE]:
        return PerBenchMessage(data, self, BaseBenchmark.of(context))
