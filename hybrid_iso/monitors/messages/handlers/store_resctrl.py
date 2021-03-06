# coding: UTF-8

from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING, Tuple, TypeVar

from aiofile_linux import WriteCmd

from benchmon.benchmark import BaseBenchmark
from benchmon.configs.containers import PrivilegeConfig
from benchmon.context import aio_context
from benchmon.monitors import ResCtrlMonitor
from benchmon.monitors.messages import PerBenchMessage
from benchmon.monitors.messages.handlers import BaseHandler
from benchmon.utils.privilege import drop_privilege

if TYPE_CHECKING:
    from pathlib import Path

    from benchmon import Context
    from benchmon.configs.containers import Privilege
    from benchmon.monitors.resctrl import DAT_TYPE as RESCTRL_MSG_TYPE

_MT = TypeVar('_MT')


class StoreResCtrl(BaseHandler):
    __slots__ = ('_event_order', '_aio_blocks', '_workspace')

    _event_order: Tuple[str, ...]
    _aio_blocks: Tuple[WriteCmd, ...]
    _workspace: Optional[Path]

    def __init__(self) -> None:
        super().__init__()

        self._event_order = tuple()
        self._aio_blocks = tuple()
        self._workspace = None

    async def on_init(self, context: Context) -> None:
        benchmark = BaseBenchmark.of(context)
        self._workspace = benchmark.bench_config.workspace / 'monitored' / 'resctrl'

        privilege_cfg = PrivilegeConfig.of(context).result
        with drop_privilege(privilege_cfg.user, privilege_cfg.group):
            self._workspace.mkdir(parents=True, exist_ok=True)

    def _create_aio_blocks(self, privilege: Privilege, bench_name: str,
                           message: RESCTRL_MSG_TYPE) -> Iterable[WriteCmd]:
        for socket_id in range(len(message)):
            with drop_privilege(privilege.user, privilege.group):
                file = open(str(self._workspace / f'{socket_id}_{bench_name}.csv'), mode='w')
            yield WriteCmd(file, '')

    def _generate_value_stream(self, message: RESCTRL_MSG_TYPE, idx: int) -> Iterable[int]:
        for event_name in self._event_order:
            yield message[idx][event_name]

    async def on_message(self, context: Context, message: PerBenchMessage[_MT]) -> Optional[PerBenchMessage[_MT]]:
        if not isinstance(message, PerBenchMessage) or not isinstance(message.source, ResCtrlMonitor):
            return message

        if self._aio_blocks is tuple():
            benchmark = BaseBenchmark.of(context)
            privilege_cfg = PrivilegeConfig.of(context).result

            self._aio_blocks = tuple(self._create_aio_blocks(privilege_cfg, benchmark.identifier, message.data))
            self._event_order = tuple(message.data[0].keys())

            for block in self._aio_blocks:
                block.buffer = (','.join(self._event_order) + '\n').encode()
            await aio_context().submit(*self._aio_blocks)
            for block in self._aio_blocks:
                block.offset += len(block.buffer)

        for idx, block in enumerate(self._aio_blocks):
            block.buffer = (','.join(map(str, self._generate_value_stream(message.data, idx))) + '\n').encode()
        await aio_context().submit(*self._aio_blocks)
        for block in self._aio_blocks:
            block.offset += len(block.buffer)

        return message

    async def on_end(self, context: Context) -> None:
        for block in self._aio_blocks:
            block.file.close()
