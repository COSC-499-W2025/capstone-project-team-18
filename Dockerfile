# Build from a Devcontainer Image
FROM mcr.microsoft.com/devcontainers/python:3.12

RUN rm -f /etc/apt/sources.list.d/yarn.list \
	&& apt-get update \
	&& apt-get install -y --no-install-recommends \
		texlive-latex-base texlive-latex-extra texlive-fonts-extra \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

