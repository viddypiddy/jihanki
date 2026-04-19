import yaml

from .build import Build
from .input import Input
from .output import Output
from .schema import PipelinesFileSchema

from pathlib import Path

import logging

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, name, schema, pipeline_config_file):
        self.name = name
        self.build = Build(schema.build, pipeline_config_file.parent)
        self.input = Input(schema.input)
        self.file = pipeline_config_file
        self.output_configs = [Output(o) for o in schema.output]

    def dictify(self):
        d = {}
        d.update(self.build.dictify())
        d.update(self.input.dictify())
        outputs = []
        for i, output in enumerate(self.output_configs):
            outputs.append(output.dictify())
        if len(outputs) == 1:
            d["Output"] = outputs[0]
        elif outputs:
            d["Outputs"] = {f"Output {i + 1}": o for i, o in enumerate(outputs)}
        return d

    def validate(self, request):
        return self.input.validate(request)

    def deliver(self, job_id, output_dir, started_at=None):
        log.info(f"Delivering to {len(self.output_configs)} outputs")
        for output in self.output_configs:
            output.deliver(job_id, output_dir, started_at)

    def get_env_variables(self, variables):
        return self.input.get_env_variables(variables)


def get_pipelines(file: Path):
    with file.open("r") as f:
        raw = yaml.safe_load(f)

    manifest = PipelinesFileSchema.model_validate(raw)

    pipelines = {}
    for key, pipeline_schema in manifest.pipelines.items():
        pipelines[key] = Pipeline(key, pipeline_schema, file)

    return pipelines
