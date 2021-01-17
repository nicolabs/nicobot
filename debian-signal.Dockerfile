############################
# STAGE 1
#
# Getting around this bug : https://github.com/docker/buildx/issues/395
# > warning: spurious network error (2 tries remaining): could not read directory '/root/.cargo/registry/index/github.com-1ecc6299db9ec823/.git//refs': Value too large for defined data type; class=Os (2)
#
# Downloads files into this temporary image, including .cargo/*
#
#ARG BUILDPLATFORM
FROM --platform=$BUILDPLATFORM rust:1.49-buster AS rust_fix

RUN apt-get update && \
    apt-get install -y git

RUN git clone https://github.com/signalapp/zkgroup.git /usr/src/zkgroup
WORKDIR /usr/src/zkgroup
ENV USER=root
RUN mkdir -p .cargo \
  && cargo vendor > .cargo/config



######################################
# STAGE 2
#
# Builder for signal-cli & libzkgroupn its native dependency
#
FROM rust:1.49-buster as signal_builder

ARG TARGETPLATFORM
ARG signal_version=0.7.1
# Buggy tzdata installation : https://serverfault.com/questions/949991/how-to-install-tzdata-on-a-ubuntu-docker-image
ARG TZ=Europe/Paris

RUN apt-get update
RUN apt-get install -y \
      # rustc must be > 1.36 or libzkgroup build will fail
      # jfsutils to create a FS that works as a workaround for bug
      # wget does not recognizes github certificates so curl replaces it well...
      git zip curl tar cargo rustc make \
      # seems missing on ubuntu images
      ca-certificates
      #python3 python3-pip && \
RUN update-ca-certificates

# Signal unpacking
WORKDIR /root
ENV SIGNAL_VERSION=${signal_version}
RUN curl -L -o signal-cli.tar.gz "https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_VERSION}/signal-cli-${SIGNAL_VERSION}.tar.gz"
RUN tar xf "signal-cli.tar.gz" -C /opt
RUN mv "/opt/signal-cli-${SIGNAL_VERSION}" /opt/signal-cli

# Compiles (or downloads) the native libzkgroup library for signal-cli
# See https://github.com/AsamK/signal-cli/wiki/Provide-native-lib-for-libsignal
COPY docker/libzkgroup libzkgroup
COPY --from=rust_fix /usr/src/zkgroup libzkgroup/zkgroup
WORKDIR libzkgroup
# This script tries to download precompiled binaries before falling back to compilation
RUN ./build.sh

# Copies libzkgroup where it belongs
WORKDIR ${TARGETPLATFORM}
# TODO Use option a. ; it allows running this step before the signal-cli installation
# and doesn't touch the signal-cli files
# Option a : Removes the classic library from the JAR (the alpine-compatible one has to be put somewhere in java.library.path)
RUN zip -d /opt/signal-cli/lib/zkgroup-java-*.jar libzkgroup.so
# Option b : Replaces the classic library directly inside the JAR with the compiled one
# Maybe less clean but also simpler in the second build stage
# RUN zip -d /opt/signal-cli/lib/zkgroup-java-*.jar libzkgroup.so && \
#     zip /opt/signal-cli/lib/zkgroup-java-*.jar libzkgroup.*



######################################
# STAGE 3
#
# Base image (with Signal)
#
# TODO Since this image now also derives from python:3, make it a separate Dockerfile
# that inherits from the default nicobot (without signal support)
#

FROM nicolabs/nicobot:debian

ARG TARGETPLATFORM

LABEL signal="true"

# apt-utils : not required ; but there is a warning asking for it
# lsb_release is required by pip and not present on slim + ARM images
RUN apt-get update && \
    apt-get install --reinstall -y apt-utils lsb-release && \
    rm -rf /var/lib/apt/lists/*

# Java installation : copying JRE files from the official images has proven
# to be quite portable & smaller than via package installation.
# The tricky thing is to make sure to get all required files from the source image.
# Luckily this means only 3 directories here...
# TODO Better prepare this in the builder by following all symlinks
# and gathering all target files
COPY --from=openjdk:11-jre-slim-stretch /etc/ssl/certs/java /etc/ssl/certs/java
COPY --from=openjdk:11-jre-slim-stretch /etc/java-11-openjdk /etc/java-11-openjdk
COPY --from=openjdk:11-jre-slim-stretch /docker-java-home /opt/java
ENV JAVA_HOME=/opt/java
ENV PATH=${JAVA_HOME}/bin:${PATH}
# basic smoke test
RUN java --version

# The 'qr' command is used in the process of linking the machine with a Signal account
RUN python3 -m pip install --no-cache-dir --user --upgrade pip && \
    python3 -m pip install --no-cache-dir --user qrcode[pil]

# signal-cli files
COPY --from=signal_builder /opt/signal-cli /opt/signal-cli
COPY --from=signal_builder /root/libzkgroup/${TARGETPLATFORM}/libzkgroup.* /opt/java/lib/
ENV PATH=/opt/signal-cli/bin:${PATH}
