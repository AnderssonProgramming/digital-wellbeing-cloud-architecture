"""Consumer behavior unit tests."""
from __future__ import annotations

import pytest
from rule_engine import consumer


class _DummyConsumer:
    def __init__(self) -> None:
        self.subscribed: list[list[str]] = []
        self.closed = False

    def subscribe(self, topics: list[str]) -> None:
        self.subscribed.append(topics)

    def poll(self, timeout: float):
        raise KeyboardInterrupt()

    def close(self) -> None:
        self.closed = True


def test_run_consumer_loop_closes_consumer() -> None:
    c = _DummyConsumer()
    with pytest.raises(KeyboardInterrupt):
        consumer.run_consumer_loop(c)  # type: ignore[arg-type]
    assert c.subscribed == [[consumer.TOPIC_RAW]]
    assert c.closed is True
