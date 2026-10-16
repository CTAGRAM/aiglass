"""EventHub — the real-time sync spine. Verifies fan-out to multiple subscribers and clean unsubscribe.

`python3 backend/tests/test_events.py`
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.events import EventHub  # noqa: E402


def test_publish_fans_out_to_all_subscribers():
    async def run():
        hub = EventHub()
        a, b = hub.subscribe(), hub.subscribe()
        await hub.publish({"type": "turn", "text": "hello"})
        ea = await asyncio.wait_for(a.get(), 1)
        eb = await asyncio.wait_for(b.get(), 1)
        assert ea["text"] == "hello" and eb["text"] == "hello"

    asyncio.run(run())


def test_unsubscribe_stops_delivery():
    async def run():
        hub = EventHub()
        a, b = hub.subscribe(), hub.subscribe()
        hub.unsubscribe(a)
        await hub.publish({"type": "turn", "text": "bye"})
        assert b.get_nowait()["text"] == "bye"   # still subscribed
        assert a.empty()                          # dropped, got nothing
        assert hub.subscriber_count == 1

    asyncio.run(run())


def test_gemini_and_hermes_share_one_stream():
    """A Gemini turn and a Hermes result both reach the same subscriber, in order."""
    async def run():
        hub = EventHub()
        app_client = hub.subscribe()
        await hub.publish({"type": "turn", "source": "gemini", "text": "what am I looking at?"})
        await hub.publish({"type": "turn", "source": "hermes", "text": "Added it to your cart."})
        first = await asyncio.wait_for(app_client.get(), 1)
        second = await asyncio.wait_for(app_client.get(), 1)
        assert first["source"] == "gemini"
        assert second["source"] == "hermes"

    asyncio.run(run())


def _main():
    tests = [
        test_publish_fans_out_to_all_subscribers,
        test_unsubscribe_stops_delivery,
        test_gemini_and_hermes_share_one_stream,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
