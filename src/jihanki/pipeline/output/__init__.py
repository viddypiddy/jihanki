from .destination import RedisDestinationHandler, FilesystemDestinationHandler
from .notification import (
    DiscordNotificationHandler,
    WebhookNotificationHandler,
    CliNotificationHandler,
)
from .packager import ZipPackager, CopyPackager

from pathlib import Path

import glob
import hashlib
import tempfile

import logging

log = logging.getLogger(__name__)


def find_files(patterns, path):
    log.info(f"Looking for files in {path}")
    files = set()
    for pattern in patterns:
        log.debug(f" -> {pattern}")
        add_files = glob.glob(pattern, root_dir=path, recursive=True)
        for file in add_files:
            p_f = Path(path) / file
            if p_f.is_file():
                log.debug(f"Found: {file}")
                files.add(file)
    log.info(f"Found {len(files)} files")
    return list(files)


class Output:
    """Manages the output delivery process for CI pipeline artifacts.

    Coordinates packaging, destination delivery, and notifications for build artifacts
    based on manifest configuration. Supports multiple packaging formats (zip, copy)
    and destination types (Redis, filesystem).
    """

    def __init__(self, schema):
        self.patterns = schema.patterns
        match schema.packager:
            case "zip":
                self.packager = ZipPackager()
            case "copy":
                self.packager = CopyPackager()

        dest = schema.destination
        match dest.provider:
            case "redis":
                self.destination_handler = RedisDestinationHandler(dest.options)
            case "filesystem":
                self.destination_handler = FilesystemDestinationHandler(dest.options)

        notify = schema.notify
        match notify.destination:
            case "discord":
                self.notification_handler = DiscordNotificationHandler(notify.options)
            case "webhook":
                self.notification_handler = WebhookNotificationHandler(notify.options)
            case "cli":
                self.notification_handler = CliNotificationHandler()
            case "none":
                self.notification_handler = None

    def dictify(self):
        d = {
            "Artifact patterns": self.patterns,
            "Packager": "zip" if isinstance(self.packager, ZipPackager) else "copy",
        }
        if isinstance(self.destination_handler, FilesystemDestinationHandler):
            d["Destination"] = f"Filesystem at {self.destination_handler.location}"
        elif isinstance(self.destination_handler, RedisDestinationHandler):
            d["Destination"] = (
                f"Redis with key prefix '{self.destination_handler.prefix}' (expires in {self.destination_handler.expiry}s)"
            )

        if self.notification_handler:
            if isinstance(self.notification_handler, DiscordNotificationHandler):
                d["Notification"] = "Discord webhook"
            elif isinstance(self.notification_handler, WebhookNotificationHandler):
                d["Notification"] = f"Webhook to {self.notification_handler.url}"
            elif isinstance(self.notification_handler, CliNotificationHandler):
                d["Notification"] = "CLI (stdout)"
        else:
            d["Notification"] = "None"
        return d

    def deliver(self, job_id: str, out_dir: Path):
        # Use glob to create list of all files that should be included in the end result
        log.debug("Finding files to deliver")
        files = find_files(self.patterns, out_dir)

        log.info("Creating artifact zip file")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_p = Path(tmpdir)

            result_files = self.packager.package(job_id, files, out_dir, tmpdir_p)

            # TODO calculate size of all files

            # Deliver the results
            metadata = self.destination_handler.deliver(tmpdir_p)
            log.info("Successfully delivered file")
            if self.notification_handler:
                file_checksums = {}
                for p in result_files:
                    sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
                    file_checksums[str(p.relative_to(tmpdir))] = sha256
                self.notification_handler.notify(job_id, file_checksums, metadata)
                log.info("Successfully notified of completion")
