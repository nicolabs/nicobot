#!/bin/sh

# There are numerous problems to build libzkgroup with Docker, and it's slow.
# This script attempts to download compiled binaries first.
# In the end the downloaded file will be in a directory named after $TARGETPLATFORM (defined by docker).
# E.g. `linux/arm/v7/libzkgroup.so` or 'windows/amd64/libzkgroup.dll'
# If download fails, some local files may be available as a fallback (but may be outdated as they are manually generated)
# If everything fails, it will compile it (but it could take a very long time)
# Not all platforms may compile.

ZKGROUP_FORCE_COMPILE=
ZKGROUP_VERSION=0.7.1
[ "$1" != "" ] && ZGROUP_VERSION=$1

if [ -z "${ZKGROUP_FORCE_COMPILE}" ]; then

  # First, tries downloading it
  case ${TARGETPLATFORM} in
      "linux/amd64")
          # This binary should already be provided by the zkgroup project
          mkdir -p "${TARGETPLATFORM}"
          curl -L -o "${TARGETPLATFORM}/libzkgroup.so" "https://github.com/signalapp/zkgroup/releases/download/v${ZKGROUP_VERSION}/libzkgroup.so"
          ;;
      "windows/amd64")
          # This binary should already be provided by the zkgroup project
          mkdir -p "${TARGETPLATFORM}"
          curl -L -o "${TARGETPLATFORM}/libzkgroup.dll" "https://github.com/signalapp/zkgroup/releases/download/v${ZKGROUP_VERSION}/libzkgroup.dll"
          ;;
      "linux/arm64")
          # This binary may already be provided within signal-cli-rest-api
          mkdir -p "${TARGETPLATFORM}"
          curl -L -o "${TARGETPLATFORM}/libzkgroup.so" "https://github.com/bbernhard/signal-cli-rest-api/raw/master/ext/libraries/zkgroup/v${ZKGROUP_VERSION}/arm64/libzkgroup.so"
          ;;
      "linux/arm/v7")
          # This binary may already be provided within signal-cli-rest-api
          mkdir -p "${TARGETPLATFORM}"
          curl -L -o "${TARGETPLATFORM}/libzkgroup.so" "https://github.com/bbernhard/signal-cli-rest-api/raw/master/ext/libraries/zkgroup/v${ZKGROUP_VERSION}/armv7/libzkgroup.so"
          ;;
  esac

  # Checks that there is a file at the destination path
  if [ `find ${TARGETPLATFORM} -name 'libzkgroup.*' 2>/dev/null | wc -l` -ge 1 ]; then
    echo "Found existing binary :"
    find ${TARGETPLATFORM} -name 'libzkgroup.*'
    return 0
  fi

# End if -z "${ZKGROUP_FORCE_COMPILE}"
fi

# Else, compiles libzkgroup
# This is by far the most risky and longest option...
# It requires : git, curl, make, rust
# Because of https://github.com/docker/buildx/issues/395 we need the files to be
# provided and the build to be offline
[ -d zkgroup ] || git clone https://github.com/signalapp/zkgroup.git zkgroup
cd zkgroup
if [ -d vendor ]; then
  RUSTFLAGS='-C link-arg=-s' cargo build --release --offline
else
  make libzkgroup
fi
cd ..
mkdir -p "${TARGETPLATFORM}"
mv zkgroup/target/release/libzkgroup.* "${TARGETPLATFORM}"
