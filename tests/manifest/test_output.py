import pytest
from pydantic import ValidationError
from jihanki.pipeline.output import Output
from jihanki.pipeline.output.packager import ZipPackager, CopyPackager
from jihanki.pipeline.output.destination import (
    FilesystemDestinationHandler,
    RedisDestinationHandler,
)
from jihanki.pipeline.output.notification import (
    DiscordNotificationHandler,
    WebhookNotificationHandler,
    CliNotificationHandler,
)
from jihanki.pipeline.schema import OutputSchema


def _make_output(overrides=None):
    base = {
        "patterns": ["out/**"],
        "packager": "zip",
        "destination": {
            "provider": "filesystem",
            "options": {"location": "/tmp/out"},
        },
        "notify": {
            "destination": "none",
            "options": {},
        },
    }
    if overrides:
        base.update(overrides)
    return Output(OutputSchema(**base))


def test_minimal_output():
    o = _make_output()
    assert o.patterns == ["out/**"]
    assert isinstance(o.packager, ZipPackager)
    assert isinstance(o.destination_handler, FilesystemDestinationHandler)
    assert o.notification_handler is None


def test_packager_defaults_to_zip():
    s = OutputSchema(
        patterns=["*.bin"],
        destination={"provider": "filesystem", "options": {"location": "/out"}},
        notify={"destination": "none", "options": {}},
    )
    o = Output(s)
    assert isinstance(o.packager, ZipPackager)


def test_copy_packager():
    o = _make_output({"packager": "copy"})
    assert isinstance(o.packager, CopyPackager)


def test_unknown_packager():
    with pytest.raises(ValidationError):
        _make_output({"packager": "tar"})


def test_filesystem_destination():
    o = _make_output()
    assert isinstance(o.destination_handler, FilesystemDestinationHandler)


def test_redis_destination():
    o = _make_output(
        {
            "destination": {
                "provider": "redis",
                "options": {"key_prefix": "build:", "expiry_seconds": 3600},
            },
        }
    )
    assert isinstance(o.destination_handler, RedisDestinationHandler)


def test_redis_destination_defaults():
    o = _make_output(
        {
            "destination": {
                "provider": "redis",
                "options": {},
            },
        }
    )
    handler = o.destination_handler
    assert handler.prefix == ""
    assert handler.expiry == 86400


def test_invalid_destination_provider():
    with pytest.raises(ValidationError):
        _make_output(
            {
                "destination": {"provider": "s3", "options": {}},
            }
        )


def test_discord_notification():
    o = _make_output(
        {
            "notify": {
                "destination": "discord",
                "options": {"webhook": "https://discord.com/api/webhooks/123/abc"},
            },
        }
    )
    assert isinstance(o.notification_handler, DiscordNotificationHandler)


def test_webhook_notification_url():
    o = _make_output(
        {
            "notify": {
                "destination": "webhook",
                "options": {"url": "https://example.com/hook"},
            },
        }
    )
    assert isinstance(o.notification_handler, WebhookNotificationHandler)
    assert o.notification_handler.url == "https://example.com/hook"


def test_webhook_notification_url_from_env(monkeypatch):
    monkeypatch.setenv("TEST_HOOK_URL", "https://example.com/hook")
    o = _make_output(
        {
            "notify": {
                "destination": "webhook",
                "options": {"url_from_env": "TEST_HOOK_URL"},
            },
        }
    )
    assert isinstance(o.notification_handler, WebhookNotificationHandler)
    assert o.notification_handler.url == "https://example.com/hook"


def test_webhook_notification_serializes_paths(monkeypatch):
    queued = {}

    class DummyQueue:
        def __init__(self, connection=None):
            pass

        def enqueue(self, func, url, payload, headers=None):
            queued["func"] = func
            queued["url"] = url
            queued["payload"] = payload
            queued["headers"] = headers

    monkeypatch.setattr("jihanki.pipeline.output.notification.Queue", DummyQueue)
    monkeypatch.setattr(
        "jihanki.pipeline.output.notification.redis_connection", object(), raising=False
    )

    handler = WebhookNotificationHandler({"url": "https://example.com/hook"})
    handler.notify("job-123", {"job-123/out.bin": "abc123"}, {})

    assert queued["url"] == "https://example.com/hook"
    assert queued["payload"] == {
        "job_id": "job-123",
        "files": {"job-123/out.bin": "abc123"},
    }
    assert queued["headers"] is None


def test_webhook_notification_supports_headers(monkeypatch):
    queued = {}

    class DummyQueue:
        def __init__(self, connection=None):
            pass

        def enqueue(self, func, url, payload, headers=None):
            queued["func"] = func
            queued["url"] = url
            queued["payload"] = payload
            queued["headers"] = headers

    monkeypatch.setattr("jihanki.pipeline.output.notification.Queue", DummyQueue)
    monkeypatch.setattr(
        "jihanki.pipeline.output.notification.redis_connection", object(), raising=False
    )
    monkeypatch.setenv("TEST_WEBHOOK_TOKEN", "secret-token")

    handler = WebhookNotificationHandler(
        {
            "url": "https://example.com/hook",
            "headers": {"Content-Type": "application/json"},
            "headers_from_env": {"X-Webhook-Token": "TEST_WEBHOOK_TOKEN"},
        }
    )
    handler.notify("job-123", {"job-123/out.bin": "abc123"}, {})

    assert queued["url"] == "https://example.com/hook"
    assert queued["payload"] == {
        "job_id": "job-123",
        "files": {"job-123/out.bin": "abc123"},
    }
    assert queued["headers"] == {
        "Content-Type": "application/json",
        "X-Webhook-Token": "secret-token",
    }


def test_cli_notification():
    o = _make_output(
        {
            "notify": {
                "destination": "cli",
                "options": {},
            },
        }
    )
    assert isinstance(o.notification_handler, CliNotificationHandler)


def test_none_notification():
    o = _make_output(
        {
            "notify": {"destination": "none", "options": {}},
        }
    )
    assert o.notification_handler is None


def test_invalid_notification_destination():
    with pytest.raises(ValidationError):
        _make_output(
            {
                "notify": {"destination": "email", "options": {}},
            }
        )


def test_missing_patterns():
    with pytest.raises(ValidationError):
        OutputSchema(
            destination={
                "provider": "filesystem",
                "options": {"location": "/out"},
            },
            notify={"destination": "none", "options": {}},
        )
