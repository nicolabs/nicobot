######################################
# STAGE 1 : Builder image
#

FROM python:3 as builder

RUN apt-get update && \
    # The following fails on arm : https://github.com/docker/buildx/issues/495
    apt-get install -y \
        # "make" tools required to compile the Python modules
        # not all may be required on all platforms...
        cmake g++ make \
        # Rust is a requirement to build the 'cryptography' Python module
        # The recommended procedure is to use 'rustup but the both Debian &
        # Alpine ship with more CPU architectures so we use the OS' packages.
        # At the time of writing rustup only provides installers for x86_64 and
        # aarch64 (arm64).
        # https://forge.rust-lang.org/infra/other-installation-methods.html
        # Alpine packages : https://pkgs.alpinelinux.org/packages?name=rust
        # Debian packages : https://packages.debian.org/buster/rustc
        #RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        rustc \
        # More dependencies for the 'cryptography' module
        # See https://cryptography.io/en/latest/installation.html#debian-ubuntu
        build-essential libssl-dev libffi-dev python3-dev \
        # git required by setuptools-scm during 'pip install'
        git

WORKDIR /usr/src/app

COPY . .

# This step WILL trigger a compilation on platforms without Python wheels
RUN python3 -m pip install --no-cache-dir --user --upgrade pip && \
    python3 -m pip install --no-cache-dir --user -r requirements-runtime.txt .

# Not used currently (we just copy the /root/.local directory which has everyting thanks to the --user option)
# Finally put (only runtime) compiled wheels under ./wheels/
# https://pip.pypa.io/en/stable/user_guide/#installation-bundles
#RUN pip wheel -r requirements-runtime.txt . --wheel-dir=wheels



######################################
# STAGE 2 : Final image
#

# The base image must provide :
# - Python version > 3.4.2
# - bash
# - glibc
FROM python:3-slim

WORKDIR /usr/src/app

# Not used currently (we just copy the /root/.local directory which has everyting thanks to the --user option)
#COPY --from=builder /usr/src/app/wheels ./wheels
#RUN pip install --no-cache-dir --force-reinstall --ignore-installed --upgrade --no-index wheels/*

# https://www.docker.com/blog/containerized-python-development-part-1/
ENV PATH=/root/.local/bin:$PATH
# All Python files, including nicobot's ones
COPY --from=builder /root/.local /root/.local/

# This script allows :
# - packaging several bots in the same image (to be cleaner they could be in
#   separate images but they're so close that it's a lot easier to package and
#   does not waste space by duplicating layers)
# - also adds extra command line options for Signal device linking
# Otherwise the ENTRYPOINT would simply be [ "python"]
COPY docker/docker-entrypoint.sh .
ENTRYPOINT [ "./docker-entrypoint.sh" ]
