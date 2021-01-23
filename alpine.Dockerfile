######################################
# DISCLAIMER
# This image is based on Alpine linux in the hope of acheiving a minimum memory footprint.
# There isn't a consensus on using alpine with Python :
# - https://pythonspeed.com/articles/alpine-docker-python
# - https://nickjanetakis.com/blog/the-3-biggest-wins-when-using-alpine-as-a-base-docker-image
# However it may help reclaim some MB on low-end computers like Raspberry Pi...
######################################


######################################
# STAGE 1 : Builder image
#

FROM python:3-alpine as builder

# python:3-alpine misses gcc, ffi.h, ...
#
# GCC part :
# https://number1.co.za/alpine-python-docker-base-image-problem-with-gcc/
# https://wiki.alpinelinux.org/wiki/How_to_get_regular_stuff_working
#
# Python cryptography part :
# https://stackoverflow.com/questions/35736598/cannot-pip-install-cryptography-in-docker-alpine-linux-3-3-with-openssl-1-0-2g
# https://github.com/pyca/cryptography/blob/1340c00/docs/installation.rst#building-cryptography-on-linux
# XEdDSA needs at least make & cmake (future versions will not : see https://github.com/Syndace/python-xeddsa)
#
# build-base gcc ... : required to build Python dependencies
# openjdk : javac to compile GetSystemProperty.java (to check the value of java.library.path)
# git zip cargo make : to compile libzkgroup
# See also https://blog.logrocket.com/packaging-a-rust-web-service-using-docker/
RUN apk add --no-cache build-base gcc abuild binutils cmake \
    # See https://cryptography.io/en/latest/installation.html#alpine for cryptography dependencies
    gcc musl-dev python3-dev libffi-dev libressl-dev \
    zip make \
    # Rust is a requirement to build the 'cryptography' Python module
    # The recommended procedure is to use 'rustup' but Alpine ships with packages
    # for more CPU architectures so we use the OS' packages.
    # At the time of writing rustup only provides installers for x86_64 and
    # aarch64 (arm64) with *musl* (i.e. Alpine).
    # https://forge.rust-lang.org/infra/other-installation-methods.html
    # Alpine packages : https://pkgs.alpinelinux.org/packages?name=rust
    #RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    cargo rust \
    # git required by setuptools-scm during 'pip install'
    git

WORKDIR /usr/src/app

# Builds & installs requirements (shoduld not change often)
COPY requirements-*.txt \
     setup.py \
     .
# This step WILL trigger a compilation on platforms without matching Python wheels
RUN python3 -m pip install --no-cache-dir --user --upgrade pip && \
    python3 -m pip install --no-cache-dir --user -r requirements-build.txt -r requirements-runtime.txt

# Builds & installs nicobot (should change often, especially the .git directory)
COPY LICENSE \
     README.md \
     .
COPY nicobot nicobot
COPY .git .git
RUN python3 -m pip install --no-cache-dir --user .



######################################
# STAGE 2 : Final image
#

# The base image must provide :
# - Python version > 3.4.2
# - bash
# - glibc
FROM python:3-alpine

WORKDIR /usr/src/app

# Runtime packages requirements
#
# libressl-dev : seems required for python to locate modules, or for omemo ?
# bash is to use extended syntax in entrypoint.sh (in particular tee >(...))
RUN apk add --no-cache libressl-dev bash

# Required by slixmpp-omemo plugin
RUN mkdir -p .omemo

# Not used currently (we just copy the /root/.local directory which has everyting thanks to the --user option)
#COPY --from=builder /usr/src/app/wheels ./wheels
#RUN pip install --no-cache-dir --force-reinstall --ignore-installed --upgrade --no-index wheels/*

# https://www.docker.com/blog/containerized-python-development-part-1/
ENV PATH=/root/.local/bin:$PATH
# All Python files, including nicobot's ones
COPY --from=builder /root/.local /root/.local/

# The 'docker-entrypoint.sh' script allows :
# - packaging several bots in the same image (to be cleaner they could be in
#   separate images but they're so close that it's a lot easier to package and
#   does not waste space by duplicating layers)
# - also adds extra command line options for Signal device linking
# Otherwise the ENTRYPOINT would simply be [ "python"]
# Also copying some default configuration files
COPY docker/docker-entrypoint.sh docker/default-conf/* .
ENTRYPOINT [ "./docker-entrypoint.sh" ]
