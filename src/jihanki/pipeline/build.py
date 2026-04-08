from .source import FilesystemBuildMaterialSource

from pathlib import Path


class Build:
    def __init__(self, schema, pipeline_workdir: Path):
        self.command = schema.command
        self.privileged_command = schema.privileged_command
        self.force_pull = schema.force_pull
        self.container = schema.container
        self.workdir = schema.workdir
        self.regcred_directory = schema.regcred_directory
        self.shared_cache = schema.shared_cache

        match schema.build_material.source:
            case "filesystem":
                self.build_material_source = FilesystemBuildMaterialSource(
                    pipeline_workdir / schema.build_material.options.location
                )
            case "none":
                self.build_material_source = None

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
