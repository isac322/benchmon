# coding: UTF-8

from dataclasses import dataclass
from typing import Mapping, Union

from .base import GeneratedMessage


@dataclass(frozen=True)
class RabbitMQMessage(GeneratedMessage[Mapping[str, Union[int, float, str]]]):
    """
    RabbitMQ를 통해 전송될 목적으로 메시지 핸들러가 생성한 메시지

    .. seealso::
        :class:`benchmon.monitors.messages.handlers.rabbit_mq.RabbitMQHandler` 클래스
            본 메시지가 처리되는 메시지 핸들러
    """
    __slots__ = ('routing_key',)

    routing_key: str
    """ 전송할 RabbitMQ의 queue 이름 """
