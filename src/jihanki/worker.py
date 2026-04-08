from typing import Optional
import docker

from rq import get_current_job

import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from jihanki.pipeline import Pipeline

import logging

log = logging.getLogger(__name__)

RUN_UID = os.getuid()


@contextmanager
def init_volumes(job_id: str, variables, pipeline: Pipeline):
    """Create a scratchdir and populate it with stuff to be volume mounted in.
    The scratchdir is a temporary folder on the host, volume mounted into the container, where inputs can be passed.
    This could be files with content from the HTTP request that fired up the job, but we can also copy in source code already existing on the host.
    As a result, you can either put the source code in the build container, or provide it afterwards - it doesn't really matter.
    """
    tempdir = Path(os.environ.get("SCRATCH_DIR"))
    scratchdir = tempdir / job_id
    log.info(f"Preparing scratchdir {scratchdir}")

    if scratchdir.exists():
        log.warning(
            "!! Scratchdir already exists, possibly retrying a failed job. Deleting"
        )
        scratchdir.delete()
    scratchdir.mkdir(parents=True)

    # Some directories we always make
    # inputs are used for variables
    input_dir = scratchdir / "inputs"
    # outputs is where we export from
    output_dir = scratchdir / "out"

    input_dir.mkdir()
    output_dir.mkdir()

    # Outputs go to a hardcoded place for now, inputs are a bit more tricky.
    volumes = ["%s:%s" % (output_dir.absolute(), "/output")]

    # Copy code files
    code_dir: Optional[Path] = None
    if pipeline.build.build_material_source is not None:
        code_dir = scratchdir / "code"
        pipeline.build.get_code(code_dir)
        volumes.append("%s:%s" % (str(code_dir.absolute()), pipeline.build.workdir))

    # Ensure permissions
    # yolo
    """
    log.info(f"Chowning with user {RUN_UID}")
    shutil.chown(code_dir, user=RUN_UID)
    for root, dirs, files in os.walk(code_dir):  
        for directory in dirs:
            shutil.chown(Path(root, directory), user=RUN_UID)
        for file in files:
            shutil.chown(Path(root, file), user=RUN_UID)

    """
    volumes.extend(pipeline.input.create_variable_files(input_dir, variables))
    volumes.extend(pipeline.build.shared_cache)

    log.info("Created files")

    yield volumes, output_dir

    log.info(f"Cleaning up scratchdir {scratchdir}")
    shutil.rmtree(scratchdir)


def docker_exec_run(container, pwd: str, command: str, user: str, environment=None):
    log.debug(f"Docker exec run: user={user} command={command}")
    result, data = container.exec_run(
        command, workdir=pwd, user=user, stream=True, environment=environment, tty=True
    )
    if result is not None:
        raise RuntimeError(f"Invalid result: {result}")

    collected_lines = []
    line_builder = ""
    for line in data:
        line_builder += line.decode()
        if "\n" in line_builder:
            contents = line_builder.split("\n")
            for content in contents:
                log.debug(f"docker STDOUT/ERR: {content}")
                collected_lines.append(content)
            line_builder = contents[-1]
    if line_builder:
        collected_lines.append(line_builder)
    return "\n".join(collected_lines)


def run_job(variables, pipeline):
    job = get_current_job()
    log.info(f"Job is running, job id {job.id}")

    with init_volumes(job.id, variables, pipeline) as (volumes, output_dir):
        log.info("Launching with volumes:")
        for volume in volumes:
            log.info(f" -> {volume}")
        # Set up docker connection
        client = docker.from_env()
        if pipeline.build.regcred_directory != "":
            log.info(
                f"Logging in to registry defined at {pipeline.build.regcred_directory}"
            )
            status = client.login(
                username="foo", dockercfg_path=pipeline.build.regcred_directory
            )
            log.info("Login succeeded?")

        log.info(f"Container is {pipeline.build.container}, preparing to build...")

        should_pull = pipeline.build.force_pull
        if not should_pull:
            try:
                client.images.get(pipeline.build.container)
                log.info("Image already exists locally, not pulling")
            except docker.errors.ImageNotFound:
                log.info("Image doesn't exist locally, pulling")
                should_pull = True

        if should_pull:
            log.info("Pulling image")
            client.images.pull(pipeline.build.container)
            log.info("Image has been pulled")

        workdir = pipeline.build.workdir

        log.debug("Creating supporting container")
        environment = pipeline.get_env_variables(variables)

        log.debug(
            f"Creating container with volumes {volumes}, environment {environment}, UID {RUN_UID}"
        )

        container = client.containers.create(
            pipeline.build.container,
            ["sleep", "1000000"],
            volumes=volumes,
            environment=environment,
            user=RUN_UID,
            detach=True,
        )
        container.start()

        build_logs = ""

        if pipeline.build.privileged_command != "":
            log.info("Starting privileged container")
            build_logs += docker_exec_run(
                container,
                workdir,
                pipeline.build.privileged_command,
                "root",
                environment,
            )
            log.info("Done running privileged container")

        log.info(
            f"Starting normal container, running as {RUN_UID}, running {pipeline.build.command} from {workdir}"
        )
        # Run unprivileged
        build_logs += docker_exec_run(
            container, workdir, pipeline.build.command, f"{RUN_UID}", environment
        )
        log.info("Done running normal container")

        container.stop()
        container.remove()

        log.info("Done running container")

        # Persist build logs
        pipeline.build.persist_build_logs(job.id, build_logs)

        # Deliver the results
        pipeline.deliver(job.id, output_dir)
    log.info("Done")
