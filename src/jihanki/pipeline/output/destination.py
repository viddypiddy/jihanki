import shutil
from pathlib import Path
import os
import logging

log = logging.getLogger(__name__)



class DestinationHandler:
    """Base class for delivering packaged build artifacts to their final destination."""

    def deliver(self, filename):
        raise RuntimeError("Not implemented")


class RedisDestinationHandler(DestinationHandler):
    """Stores packaged build artifacts in Redis with configurable key prefix and expiry.

    Only supports delivering a single file. Files are stored as binary data in Redis.
    """

    def __init__(self, options):
        self.prefix = options.get("key_prefix", "")
        self.expiry = options.get("expiry_seconds", 60 * 60 * 24)

    def deliver(self, foundfiles_dir: Path):
        # yolo-import to establish the redis connection
        log.debug("Connecting to redis")
        from ..redis import redis_connection

        # List files in folder. If more than one - not supported
        files = list(foundfiles_dir.iterdir())
        if len(files) != 1:
            raise RuntimeError(
                f"Redis destination handler only supports one file - got {len(files)}"
            )

        with files[0].open("rb") as file:
            keyname = "%s%s" % (self.prefix, job_id)
            redis_connection.set(keyname, file.read())
            redis_connection.expire(keyname, self.expiry)
            log.info("Delivered payload to redis")


class FilesystemDestinationHandler(DestinationHandler):
    """Delivers packaged build artifacts to a filesystem location.

    Copies all files from the source directory to the configured destination path,
    setting appropriate file permissions (0o664) on all delivered files and directories.
    """

    def __init__(self, options):
        self.location = Path(options["location"])

    def deliver(self, foundfiles_dir: Path):
        log.info(f"Delivering output to {self.location}")
        shutil.copytree(foundfiles_dir, self.location, dirs_exist_ok=True)
        # Walk foundfiles_dir and chmod it in dst dir
        for root, dirs, files in os.walk(foundfiles_dir, topdown=False):
            r_p = Path(root)

            # chmod dirs
            for d in [r_p / d for d in dirs]:
                os.chmod(self.location / d, 0o664)

            # chmod files
            for f in [r_p / f for f in files]:
                os.chmod(self.location / f, 0o664)
