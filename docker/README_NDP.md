# NDP-Compatible Jupyter Image

This directory contains an image definition designed to run on the
National Data Platform (NDP) JupyterHub using the **“Bring Your Own Image”**
option.

## Dockerfile.ndp

Key properties:

- **Base image**: `quay.io/jupyter/datascience-notebook:latest`
- Keeps the default Jupyter user (`${NB_UID}`) and start command.
- Installs project Python dependencies from `requirements.txt` plus:
  - `pydeck`, `streamlit`, `psutil`
- Adds a startup hook (`ndp-resources.sh`) that:
  - Detects available CPU cores and RAM inside the container.
  - Sets `NDP_CPUS` and `NDP_MEM_GB`.
  - Sets sensible defaults for:
    - `OMP_NUM_THREADS`
    - `NUMEXPR_MAX_THREADS`
    - `N_THREADS_DEFAULT`
  - Respects any values you explicitly set in the NDP UI / env.
- Exposes port `8888` and **does not override** the base image CMD
  (`start-notebook.sh`), as required by NDP.

## Building and Pushing

```bash
docker build -t YOUR_DOCKERHUB_USER/biz-graph-ndp:latest -f docker/Dockerfile.ndp .
docker push YOUR_DOCKERHUB_USER/biz-graph-ndp:latest
```

In the NDP JupyterHub UI, paste:

```text
YOUR_DOCKERHUB_USER/biz-graph-ndp:latest
```

into **“Or Bring Your Own Image (JupyterLab Compatible)”**.

## Resource Behaviour

Inside notebooks you can inspect:

```python
import os

os.getenv("NDP_CPUS")
os.getenv("NDP_MEM_GB")
os.getenv("N_THREADS_DEFAULT")
```

and use these values to size parallel jobs (e.g. `n_jobs=int(os.getenv("N_THREADS_DEFAULT", "1"))`).

