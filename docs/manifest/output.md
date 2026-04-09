# output

A list of output configurations. Each entry defines which artifacts to collect, how to package them, where to deliver them, and how to notify on completion.

```yaml
build:
  # [...]
input:
  # [...]
output:
  - patterns:
      - out/**
      - build/*.bin
    packager: zip
    destination:
      provider: filesystem
      options:
        location: /out
    notify:
      destination: webhook
      options:
        url_from_env: BUILD_SUCCESS_WEBHOOK
```

### Fields

Output files in jihanki **MUST** be placed in `/out`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `patterns` | list of strings | Yes | | Glob patterns matched against the workdir to select artifacts |
| `packager` | string | No | `zip` | Packaging method: `zip` or `copy` |
| `destination` | map | Yes | | Where to deliver the packaged artifacts |
| `notify` | map | Yes | | How to notify on completion |

## packager

The packager is what collects the files found earlier using patterns from the container and prepares them for delivery. 

| Value | Description |
|-------|-------------|
| `zip` | Creates a ZIP archive containing all matched files |
| `copy` | Copies matched files into a directory named after the job ID (filenames only, paths are not preserved) |

## destination

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Destination type: `filesystem` or `redis` |
| `options` | map | Yes | Provider-specific options |

### `filesystem` provider

Copies packaged artifacts to a directory on disk.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `location` | string | Yes | Target directory path |

### `redis` provider

Stores a single packaged file in Redis as binary data.

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `key_prefix` | string | No | `""` | Prefix prepended to the job ID to form the Redis key |
| `expiry_seconds` | int | No | `86400` | TTL for the Redis key in seconds |

## notify

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `destination` | string | Yes | Notification type: `discord`, `webhook`, `cli`, or `none` |
| `options` | map | When not `none` | Destination-specific options |

### `discord` destination

Posts a message to a Discord webhook.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `webhook` | string | Yes | Discord webhook URL |

### `webhook` destination

Posts job results as JSON to an HTTP endpoint.

| Option | Type | Description |
|--------|------|-------------|
| `url` | string | Webhook URL (provide one of `url` or `url_from_env`) |
| `url_from_env` | string | Environment variable name containing the webhook URL |
| `headers` | map | Optional static HTTP headers to send with the webhook |
| `headers_from_env` | map | Optional map of header name to environment variable for secret header values |

### `cli` destination

Prints build results to the log. Takes no options. Useful for testing.

### `none` destination

No notification is sent. The `options` field can be omitted.
