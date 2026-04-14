# Persistent Storage for Experiments

Modal Volumes provide persistent storage that survives across training runs and experiments. Download a dataset once and every future run can access it.

## Creating Volumes

```python
data_volume = modal.Volume.from_name("training-data", create_if_missing=True)
ckpt_volume = modal.Volume.from_name("training-checkpoints", create_if_missing=True)

@app.function(
    volumes={"/data": data_volume, "/checkpoints": ckpt_volume},
)
def train():
    # /data and /checkpoints are persistent across runs
    ...
```

## Committing Changes

After writing to a volume inside a function, call `commit()` to persist:

```python
@app.function(volumes={"/data": data_volume})
def download_data():
    # Download files to /data/...
    ...
    data_volume.commit()
```

Without `commit()`, changes are lost when the container exits.

## Data Download Pattern

Use a separate function to download/preprocess data once:

```python
@app.function(timeout=60 * 60 * 4, volumes={"/data": data_volume})
def download_data(max_shards: int = None):
    from huggingface_hub import hf_hub_download
    # Download to /data/...
    data_volume.commit()
```

```bash
# Download data (one-time)
modal run my_train.py::download_data --max-shards 64

# Train (data already on volume)
modal run my_train.py
```

## CLI Commands

```bash
# List files
modal volume ls training-data /

# Download a file
modal volume get training-checkpoints /my-experiment/latest.pt ./latest.pt

# Upload a file
modal volume put training-data ./dataset.tar.gz /dataset.tar.gz
```

## References

- Modal Volumes docs: https://modal.com/docs/guide/volumes
