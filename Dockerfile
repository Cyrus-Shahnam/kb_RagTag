FROM kbase/sdkpython:3.8.0
LABEL maintainer="ac.shahnam"
USER root

# ------------------------------------------------------------
# 1) System dependencies (for the micromamba bootstrap)
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl bzip2 ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

# The minimal sdkpython base does not bundle the JSON-RPC server dep.
RUN pip install jsonrpcbase

# ------------------------------------------------------------
# 2) micromamba bootstrap
# ------------------------------------------------------------
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV MAMBA_NO_BANNER=1
ENV MAMBA_DOCKERFILE_ACTIVATE=0
# Fetch micromamba via RUN (honors build-time http(s)_proxy, which buildkit's
# ADD does not always use). Primary source is micro.mamba.pm; fall back to the
# micromamba-releases GitHub assets if that host is unreachable.
RUN set -eux; \
    ( curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest \
        | tar -xj -C /usr/local/bin/ --strip-components=1 bin/micromamba ) \
    || ( curl -fsSL -o /usr/local/bin/micromamba \
           https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-linux-64 ); \
    chmod +x /usr/local/bin/micromamba; \
    micromamba --version

# ------------------------------------------------------------
# 3) Create the RagTag conda environment
#    bioconda provides ragtag, minimap2, and the full MUMmer suite
#    (nucmer plus its helper binaries: mummer, mgaps, delta-filter) together,
#    so no version-pinned binary downloads are needed.
# ------------------------------------------------------------
COPY env-ragtag.yml /tmp/env-ragtag.yml
RUN micromamba create -y -n ragtag -f /tmp/env-ragtag.yml && \
    micromamba clean -a -y

# ------------------------------------------------------------
# 4) Build-time sanity check
#    ragtag.py dispatches to ragtag_scaffold.py / ragtag_correct.py / etc. by
#    bare name, so the env bin must be on PATH for these to resolve -- exactly
#    as the app arranges at runtime via ragtag_utils.py. The PATH export is
#    scoped to this single RUN, so the final image PATH stays unchanged and the
#    KBase server keeps using the base image's Python.
# ------------------------------------------------------------
RUN export PATH=/opt/conda/envs/ragtag/bin:$PATH && \
    ragtag.py scaffold -h > /dev/null && \
    ragtag.py correct  -h > /dev/null && \
    ragtag.py patch    -h > /dev/null && \
    ragtag.py merge    -h > /dev/null && \
    minimap2 --version && \
    test -x /opt/conda/envs/ragtag/bin/nucmer

# NOTE: PATH is intentionally NOT modified in the image (no ENV PATH change).
# The wrapper invokes RagTag from /opt/conda/envs/ragtag/bin and injects that
# directory onto PATH *only for the RagTag subprocess* (see lib/kb_ragtag/
# ragtag_utils.py), so RagTag's sub-scripts and nucmer's helpers resolve at
# runtime while the KBase server keeps using the base image's Python.

# ------------------------------------------------------------
# 5) Copy module and finalize
# ------------------------------------------------------------
COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module
WORKDIR /kb/module
RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]
CMD [ ]
