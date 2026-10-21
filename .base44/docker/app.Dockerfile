# Sandbox runtime for DIY Diag (Base44 preview).
#
# DIY Diag is a dependency-free Python CLI with no HTTP server of its own, so the
# preview runs the real CLI inside a browser terminal (ttyd) on the app's port.
#
# This image deliberately bakes NO application source: the repository is
# bind-mounted at /app at runtime, so edits are live and no rebuild is needed.
# Debian no longer packages ttyd, so the official static release binary is pinned
# here by version and checksum.
FROM python:3.12-slim

ARG TTYD_VERSION=1.7.7
ARG TTYD_SHA256=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/local/bin/ttyd \
      "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
 && echo "${TTYD_SHA256}  /usr/local/bin/ttyd" | sha256sum -c - \
 && chmod +x /usr/local/bin/ttyd

# The app itself has no third-party dependencies (standard library only).
# pytest is installed here solely so `python -m pytest -q` can run in the sandbox.
RUN pip install --no-cache-dir pytest

WORKDIR /app
