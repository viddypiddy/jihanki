# build

Configures the container image, commands, and build material for the pipeline.

```yaml
build:
  command: ./startup.sh
  container: "my-build-image:latest"
  privileged_command: ./setup.sh    # optional
  workdir: /var/runner               # optional, default: /var/runner
  regcred_directory: /regcred/config.json  # optional
  persist_build_logs_to: /var/log/builds  # optional
  build-material:                    # optional, default: none
    source: filesystem
    options:
      location: ./my-source
input:
  # [...]
output:
  # [...]
```

## Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | string | Yes | | Command to run inside the container as the unprivileged user |
| `container` | string | Yes | | Docker image to pull and run |
| `force_pull` | boolean | No | | If the docker image should be force pulled, even if it exists locally |
| `privileged_command` | string | No | `""` | Command to run as root before the main command |
| `workdir` | string | No | `/var/runner` | Working directory inside the container where build material is mounted |
| `regcred_directory` | string | No | `""` | Path to Docker registry credentials file. If set, Bob logs in before pulling the image |
| `persist_build_logs_to` | string | No | | Directory to write build logs to. Log files are named `<datetime>-<job_id>.log`. The directory is created if it doesn't exist |

## build-material

Defines where to source the code/files for the build. If build-material is set, the source code is copied and volume mounted into `workdir`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | Yes | Source type: `filesystem` or `none` |
| `options` | map | When source is `filesystem` | Source-specific options |

### source: filesystem

Copies a directory into the container's workdir.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `location` | string | Yes | Path to the directory to copy |

### source: none

No build material is copied. The `options` field can be omitted.
