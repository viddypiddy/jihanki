import requests
import os
import logging

from rq import Queue

log = logging.getLogger(__name__)


class NotificationHandler:
    """Base class for sending notifications about completed CI pipeline jobs."""

    def notify(self, job_id):
        raise RuntimeError("Not implemented")


def send_webhook_async(url, payload, headers=None):
    response = requests.post(url, json=payload, headers=headers)
    if not response.ok:
        log.warning(
            "Webhook to %s returned %s: %s", url, response.status_code, response.text
        )


class DiscordNotificationHandler(NotificationHandler):
    def __init__(self, options):
        self.webhook = options["webhook"]

    def notify(self, job_id, files, destination_metadata):
        from jihanki.redis import redis_connection

        q = Queue(connection=redis_connection)
        q.enqueue(
            send_webhook_async,
            self.webhook,
            {
                "name": "Jihanki",
                "content": f"Jihanki finished building job {job_id}",
            },
        )


class WebhookNotificationHandler(NotificationHandler):
    def __init__(self, options):
        if "url_from_env" in options:
            self.url = os.environ[options["url_from_env"]]
        elif "url" in options:
            self.url = options["url"]
        else:
            raise RuntimeError(
                "Unable to setup webhook notifications: Neither url_from_env or url is specified in the notification options"
            )
        self.headers = dict(options.get("headers", {}))
        for header_name, env_name in options.get("headers_from_env", {}).items():
            self.headers[header_name] = os.environ[env_name]

    def notify(self, job_id, files, destination_metadata):
        from jihanki.redis import redis_connection

        q = Queue(connection=redis_connection)
        q.enqueue(
            send_webhook_async,
            self.url,
            {"job_id": job_id, "files": [str(path) for path in files]},
            self.headers or None,
        )


class CliNotificationHandler(NotificationHandler):
    """Simply prints info about the build to CLI. Useful for testing."""

    def __init__(self):
        pass

    def notify(self, job_id, files, destination_metadata):
        log.info(f"BUILD COMPLETE: jobid {job_id} files {files}")
