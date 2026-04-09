from sanic import Sanic
from sanic.response import text, json

from rq import Queue

from .worker import run_job
from .pipeline import get_pipelines
from .redis import redis_connection

from pathlib import Path
import os
import yaml

import logging

log = logging.getLogger(__name__)

pipeline_location = os.environ.get("PIPELINES_LOCATION", "pipelines.yaml")

log.info(f"Starting Jihanki with pipeline location {pipeline_location}")

pipelines = get_pipelines(Path(pipeline_location))

for name, pipeline in pipelines.items():
    log.info(
        f"Pipeline '{name}' docker view:\n{yaml.dump({name: pipeline.dictify()}, default_flow_style=False, sort_keys=False)}"
    )

app = Sanic("Jihanki")

q = Queue(connection=redis_connection, deault_timeout=10 * 60)

token = os.environ["JIHANKI_TOKEN"]


@app.on_request
async def token_checker(request):
    if request.path.startswith("/healthz"):
        log.debug(f"Allowing healthcheck request")
        return

    if "Authorization" not in request.headers:
        return json({"error": "No token"}, status=401)

    auth_parts = request.headers["Authorization"].split(" ")
    if auth_parts[0] != "Token":
        return json(
            {"error": "Invalid authorization type. Only Token is allowed"}, status=403
        )

    if auth_parts[1] != token:
        return json({"error": "Invalid token"}, status=403)


@app.get("/")
async def hello_world(request):
    return text("Beep boop")


@app.get("/healthz")
async def healthcheck(request):
    return text("OK")


@app.post("/api/v1/job")
async def enqueue_job(request):
    log.info("Working on enqueueing job")
    if request.json is None:
        log.info("No json body")
        return json({"error": "Missing JSON body"}, status=400)

    if "pipeline" not in request.json:
        log.info("No pipeline")
        return json({"error": "Missing pipeline"}, status=400)

    requested_pipeline = request.json["pipeline"]

    if requested_pipeline not in pipelines:
        log.info(f"Unknown pipeline: {requested_pipeline}")
        return json({"error": "Pipeline not found"}, status=400)

    pipeline = pipelines[requested_pipeline]
    validation_result = pipeline.validate(request)
    if validation_result is not None:
        log.info(f"Validation failed: {validation_result}")
        return json({"error": f"Validation failed: {validation_result}"}, status=400)

    job = q.enqueue(
        run_job, request.json, pipeline, job_timeout=5 * 60
    )  # Job needs to be done in 4 minutes
    return json({"job_id": job.id})
