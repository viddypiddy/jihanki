import logging

log = logging.getLogger(__name__)

import requests
import os

from rq import Queue


class NotificationHandler:
    """Base class for sending notifications about completed CI pipeline jobs."""

    def notify(self, job_id):
        raise RuntimeError("Not implemented")


def send_webhook_async(url, payload):
    requests.post(url, json=payload)


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

    def notify(self, job_id, files, destination_metadata):
        from jihanki.redis import redis_connection

        q = Queue(connection=redis_connection)
        q.enqueue(
            send_webhook_async,
            self.url,
            {"job_id": job_id, "files": [str(path) for path in files]},
        )


class CliNotificationHandler(NotificationHandler):
    """Simply prints info about the build to CLI. Useful for testing."""

    def __init__(self):
        pass

    def notify(self, job_id, files, destination_metadata):
        log.info(f"BUILD COMPLETE: jobid {job_id} files {files}")
