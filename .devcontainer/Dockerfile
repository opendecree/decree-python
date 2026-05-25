ARG UV_VERSION=0.11.16
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM mcr.microsoft.com/devcontainers/python:3.12

COPY --from=uv /uv /uvx /usr/local/bin/
