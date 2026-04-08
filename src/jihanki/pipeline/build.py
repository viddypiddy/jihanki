from .source import FilesystemBuildMaterialSource

from datetime import datetime
from pathlib import Path

import logging

log = logging.getLogger(__name__)


class Build:
    def __init__(self, schema, pipeline_workdir: Path):
        self.command = schema.command
        self.privileged_command = schema.privileged_command
        self.force_pull = schema.force_pull
        self.container = schema.container
        self.workdir = schema.workdir
        self.regcred_directory = schema.regcred_directory
        self.shared_cache = schema.shared_cache
        self.persist_build_logs_to = None
        if schema.persist_build_logs_to:
            self.persist_build_logs_to = Path(schema.persist_build_logs_to)
            self.persist_build_logs_to.mkdir(parents=True, exist_ok=True)

        match schema.build_material.source:
            case "filesystem":
                self.build_material_source = FilesystemBuildMaterialSource(
                    pipeline_workdir / schema.build_material.options.location
                )
            case "none":
                self.build_material_source = None

    def persist_build_logs(self, job_id: str, build_logs: str):
        if not self.persist_build_logs_to:
            return
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = self.persist_build_logs_to / f"{date_str}-{job_id}.log"
        log_file.write_text(build_logs)
        log.info(f"Build logs persisted to {log_file}")

    def get_code(self, code_dir: Path):
        self.build_material_source.get_code(code_dir)

    def dictify(self):
        d = {
            "Container image": self.container,
            "Build command": self.command,
            "Working directory": self.workdir,
        }
        if self.privileged_command:
            d["Privileged setup command"] = self.privileged_command
        if self.regcred_directory:
            d["Registry credentials"] = self.regcred_directory
        if self.persist_build_logs_to:
            d["Build logs"] = str(self.persist_build_logs_to)

        volumes = {}
        if self.build_material_source and isinstance(
            self.build_material_source, FilesystemBuildMaterialSource
        ):
            volumes["Build material"] = (
                f"{self.build_material_source.location} -> $SCRATCH_DIR/<job_uuid>/code (mounted at {self.workdir})"
            )
        else:
            volumes["Scratch space"] = (
                f"$SCRATCH_DIR/<job_uuid>/code (mounted at {self.workdir})"
            )
        if volumes:
            d["Volumes"] = volumes
        return d
