from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional


class BuildMaterialOptionsSchema(BaseModel):
    location: str


class BuildMaterialSchema(BaseModel):
    source: Literal["filesystem", "none"] = "none"
    options: Optional[BuildMaterialOptionsSchema] = None


class BuildSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    command: str
    container: str
    privileged_command: str = ""
    force_pull: bool = True
    workdir: str = "/var/runner"
    regcred_directory: str = ""
    build_material: BuildMaterialSchema = Field(
        default_factory=BuildMaterialSchema, alias="build-material"
    )
    shared_cache: list[str] = []
    persist_build_logs_to: Optional[str] = None


class EnvVarSchema(BaseModel):
    source: Literal["field", "static"]
    fieldname: str = ""
    value: str = ""


class FileFromVarSchema(BaseModel):
    fieldname: str
    destination: str


class InputSchema(BaseModel):
    environment: dict[str, EnvVarSchema] = {}
    files: list[FileFromVarSchema] = []


class DestinationSchema(BaseModel):
    provider: Literal["redis", "filesystem"]
    options: dict = {}


class NotifySchema(BaseModel):
    destination: Literal["discord", "webhook", "cli", "none"]
    options: dict = {}


class OutputSchema(BaseModel):
    patterns: list[str]
    packager: Literal["zip", "copy"] = "zip"
    destination: DestinationSchema
    notify: NotifySchema


class PipelineSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    build: BuildSchema
    input: InputSchema = InputSchema()
    output: list[OutputSchema]


class PipelinesFileSchema(BaseModel):
    version: str
    pipelines: dict[str, PipelineSchema]
