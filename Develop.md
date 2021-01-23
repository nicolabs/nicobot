# Devops notes for nicobot

[![Build Status on 'master' branch][travisci-shield]][travisci-link] [![PyPi][pypi-shield]][pypi-link]  
[![Build and publish to Docker Hub][dockerhub-shield]][dockerhub-link]  
[![Docker debian][docker-debian-size] ![Docker debian-signal][docker-debian-signal-size] ![Docker alpine][docker-alpine-size]](https://hub.docker.com/r/nicolabs/nicobot/tags)



## Basic development

Install Python dependencies (for both building and running) and generate `nicobot/version.py` with :

    pip3 install -r requirements-build.txt -r requirements-runtime.txt
    python3 setup.py build

To run unit tests :

    python3 -m unittest discover -v -s tests

To run directly from source (without packaging) :

    python3 -m nicobot.askbot [options...]

To build locally (more at [pypi.org](https://packaging.python.org/tutorials/packaging-projects/)) :

    rm -rf ./dist ; python3 setup.py build sdist bdist_wheel

### PyPi upload

To upload to test.pypi.org :

    python3 -m twine upload --repository testpypi dist/*

To install the test package from test.pypi.org and check that it works :

    # First create a virtual environment not to mess with the host system
    python3 -m venv venv/pypi_test && source venv/pypi_test/bin/activate

    # Then install dependencies using the regular pypi repo
    pip3 install -r requirements-runtime.txt

    # Finally install this package from the test repo
    pip3 install -i https://test.pypi.org/simple/ --no-deps nicobot

    # Do some test
    python -m nicobot.askbot -V
    ...

    # Exit the virtual environment
    deactivate

To upload to PROD pypi.org :

    python3 -m twine upload dist/*

Both above *twine upload* commands will ask for a username and a password.
To prevent this, you could set variables :

    # Defines username and password (or '__token__' and API key)
    export TWINE_USERNAME=__token__
    # Example reading the token from a local 'passwordstore'
    export TWINE_PASSWORD=`pass pypi/test.pypi.org/api_token`

Or store them in `~/.pypirc` ([see doc](https://packaging.python.org/specifications/pypirc/)) :

    [pypi]
    username = __token__
    password = <PyPI token>

    [testpypi]
    username = __token__
    password = <TestPyPI token>

Or even use CLI options `-u` and `-p`, or certificates...
See `python3 -m twine upload --help` for details.



### Automation for PyPi

The above instructions allow to build manually but otherwise it is automatically tested, built and uploaded to pypi.org using _Travis CI_ on each push to GitHub (see [`.travis.yml`](.travis.yml)).



## Docker build

There are several Dockerfiles, each made for specific use cases (see [README.md](README.md#Docker-usage)).
They all have [multiple stages](https://docs.docker.com/develop/develop-images/multistage-build/).

`debian.Dockerfile` is quite straight. It builds using *pip* in one stage and copies the resulting *wheels* into the final one.

`debian-signal.Dockerfile` is more complex because it needs to address :
- including both Python and Java while keeping the image size small
- compiling native dependencies (both for _signal-cli_ and _qr_)
- circumventing a number of bugs in multiarch building

`debian-alpine.Dockerfile` produces smaller images but may not be as much portable than debian ones and misses Signal support for now.

Note that the _signal-cli_ backend needs a _Java_ runtime environment, and also _rust_ dependencies to support Signal's group V2. This approximately doubles the size of the images and almost ruins the advantage of alpine over debian...

Those images are limited on each OS (debian+glibc / alpine+musl) to CPU architectures which :
1. have base images (python, openjdk, rust)
2. have Python dependencies have _wheels_ or are able to build them
3. can build libzkgroup (native dependencies for signal)
4. have the required packages to build

At the time of writing, support is dropped for :
- `linux/s390x` : lack of _python:3_ image (at least)
- `linux/riscv64` : lack of _python:3_ image (at least)
- Signal backend on `linux/arm*` _for Alpine variants_ : lack of JRE binaries

All images have all the bots inside (as they would otherwise only differ by one script from each other).
The [`docker-entrypoint.sh`](docker/docker-entrypoint.sh) script takes the name of the bot to invoke as its first argument, then its own options and finally the bot's arguments.

Sample _build_ command (single architecture) :

    docker build -t nicolabs/nicobot:debian -f debian.Dockerfile .

Sample _buildx_ command (multi-arch) :

    docker buildx build --platform linux/amd64,linux/arm64,linux/386,linux/arm/v7 -t nicolabs/nicobot:debian -f debian.Dockerfile .

Then run with the provided sample configuration :

    docker run --rm -it -v "$(pwd)/tests:/etc/nicobot" nicolabs/nicobot:debian askbot -c /etc/nicobot/askbot-sample-conf/config.yml


### Automation for Docker Hub

_Github actions_ are currently used (see [`.github/workflows/dockerhub.yml`](.github/workflows/dockerhub.yml) to automatically build and push the images to [Docker Hub](https://hub.docker.com/r/nicolabs/nicobot) so they are available whenever commits are pushed to the _master_ branch :

1. A *Github Action* is triggered on each push to [the central repo](https://github.com/nicolabs/nicobot)
2. All images are built in order using caching (see [.github/workflows/dockerhub.yml](.github/workflows/dockerhub.yml))
3. Images are uploaded to [Docker Hub](https://hub.docker.com/repository/docker/nicolabs/nicobot)


### Docker build process overview

This is the view from the **master** branch on this repository.
It emphasizes *FROM* and *COPY* relations between the images (base and stages).

![nicobot docker images build process](http://www.plantuml.com/plantuml/proxy?cache=no&src=https%3A%2F%2Fraw.github.com%2Fnicolabs%2Fnicobot%2Fmaster%2Fdocker%2Fdocker-images.puml)


### Why no image is available for x arch ?

[The open issues labelled with *docker*](https://github.com/nicolabs/nicobot/labels/docker) should reference the reasons for missing arch / configuration.


### Docker image structure

Here are the main application files and directories from within the images :

    📦 /
     ┣ 📂 root/
     ┃ ┗ 📂 .local/
     ┃   ┣ 📂 bin/  - - - - - - - - - - - - - -> shortcuts
     ┃   ┃ ┣ 📜 askbot
     ┃   ┃ ┣ 📜 transbot
     ┃   ┃ ┗ 📜 ...
     ┃   ┣ 📂 lib/pythonX.X/site-packages/  - -> Python packages (nicobot & dependencies)
     ┃   ┗ 📂 share/signal-cli/ - - - - - - - -> signal-cli configuration files
     ┗ 📂 usr/src/app/  - - - - - - - - - - - -> app's working directory, default configuration files, ...
       ┣ 📂 .omemo/ - - - - - - - - - - - - - -> OMEMO keys (XMPP)
       ┣ 📜 docker-entrypoint.sh
       ┣ 📜 i18n.en.yml
       ┗ 📜 ...


## Versioning

The `--version` command-line option that displays the bots' version relies on _setuptools_scm_, which extracts it from the underlying git metadata.
This is convenient because the developer does not have to manually update the version (or forget to do it), however it either requires the version to be fixed inside a Python module or the `.git` directory to be present.

There were several options among which the following one has been retained :
1. Running `setup.py` creates / updates the version inside the `version.py` file
2. The scripts then load this module at runtime

Since the `version.py` file is not saved into the project, `setup.py build` must be run before the version can be queried. In exchange :
- it does not require _setuptools_ nor _git_ at runtime
- it frees us from having the `.git` directory around at runtime ; this is especially useful to make the docker images smaller

Tip : `python3 setup.py --version` will print the guessed version.



## Building signal-cli

The _signal_ backend (actually *signal-cli*) requires a Java runtime, which approximately doubles the image size.
This led to build separate images (same _repo_ but different _tags_), to allow using smaller images when only the XMPP backend is needed.



## Resources

### IBM Cloud

- [Language Translator service](https://cloud.ibm.com/catalog/services/language-translator)
- [Language Translator API documentation](https://cloud.ibm.com/apidocs/language-translator)

### Signal

- [Signal home](https://signal.org/)
- [signal-cli man page](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc)

### Jabber

- Official XMPP libraries : https://xmpp.org/software/libraries.html
- OMEMO compatible clients : https://omemo.top/
- [OMEMO official Python library](https://github.com/omemo/python-omemo) : looks very immature
- *Gaijim*, a Windows/MacOS/Linux XMPP client with OMEMO support : [gajim.org](https://gajim.org/) | [dev.gajim.org/gajim](https://dev.gajim.org/gajim)
- *Conversations*, an Android XMPP client with OMEMO support and paid hosting : https://conversations.im

### Python libraries

- [xmpppy](https://github.com/xmpppy/xmpppy) : this library is very easy to use but it does allow easy access to thread or timestamp, and no OMEMO...
- [github.com/horazont/aioxmpp](https://github.com/horazont/aioxmpp) : officially referenced library from xmpp.org, seems the most complete but misses practical introduction and [does not provide OMEMO OOTB](https://github.com/horazont/aioxmpp/issues/338).
- [slixmpp](https://lab.louiz.org/poezio/slixmpp) : seems like a cool library too and pretends to require minimal dependencies ; plus it [supports OMEMO](https://lab.louiz.org/poezio/slixmpp-omemo/) so it's the winner. [API doc](https://slixmpp.readthedocs.io/).

### Dockerfile

- [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker development best practices](https://docs.docker.com/develop/dev-best-practices/)
- [DEBIAN_FRONTEND=noninteractive trick](https://serverfault.com/questions/500764/dpkg-reconfigure-unable-to-re-open-stdin-no-file-or-directory)
- [Dockerfile reference](https://docs.docker.com/engine/reference/builder/#copy)

### JRE + Python in Docker

- [Docker hub - python images](https://hub.docker.com/_/python)
- [docker-library/openjdk - ubuntu java package has broken cacerts](https://github.com/docker-library/openjdk/issues/19)
- [Openjdk Dockerfiles @ github](https://github.com/docker-library/openjdk)
- [phusion/baseimage-docker @ github - not used in the end, because not so portable](https://github.com/phusion/baseimage-docker)
- [Azul JDK - not used in the end because not better than openjdk](http://docs.azul.com/zulu/zuludocs/ZuluUserGuide/PrepareZuluPlatform/AttachAPTRepositoryUbuntuOrDebianSys.htm)
- [rappdw/docker-java-python image - not used because only for amd64](https://hub.docker.com/r/rappdw/docker-java-python)
- [Use OpenJDK builds provided by jdk.java.net?](https://github.com/docker-library/openjdk/issues/212)
- [How to install tzdata on a ubuntu docker image?](https://serverfault.com/questions/949991/how-to-install-tzdata-on-a-ubuntu-docker-image)

### Multiarch & native dependencies

- [docker.com - Automatic platform ARGs in the global scope](https://docs.docker.com/engine/reference/builder/#automatic-platform-args-in-the-global-scope)
- [docker/buildx @ github](https://github.com/docker/buildx)
- [Compiling 'crytography' for Python](https://cryptography.io/en/latest/installation.html#building-cryptography-on-linux)
- [signal-cli - Providing native lib for libsignal](https://github.com/AsamK/signal-cli/wiki/Provide-native-lib-for-libsignal)
- [github.com/signalapp/zkgroup - Compiling on raspberry pi fails](https://github.com/signalapp/zkgroup/issues/6)
- [Multi-Platform Docker Builds (including cargo-specific cross-building)](https://www.docker.com/blog/multi-platform-docker-builds/)
- [How to build ARMv6 and ARMv7 in the same manifest file. (Compatible tag for ARMv7, ARMv6, ARM64 and AMD64)](https://github.com/KEINOS/Dockerfile_of_Alpine/issues/3)
- [The "dpkg-split: No such file or directory" bug](https://github.com/docker/buildx/issues/495)
- [The "Command '('lsb_release', '-a')' returned non-zero exit status 1" bug](https://github.com/docker/buildx/issues/493)
- [Binfmt / Installing emulators](https://github.com/tonistiigi/binfmt#installing-emulators)
- [Cross-Compile for Raspberry Pi With Docker](https://itsze.ro/blog/2020/11/29/cross-compile-for-raspberry-pi-with-docker.html)

### Python build & Python in Docker

- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [What Are Python Wheels and Why Should You Care?](https://realpython.com/python-wheels)
- [Using Alpine can make Python Docker builds 50× slower](https://pythonspeed.com/articles/alpine-docker-python/)
- [pip install manual](https://pip.pypa.io/en/stable/reference/pip_install/)
- [pip is showing error 'lsb_release -a' returned non-zero exit status 1](https://stackoverflow.com/questions/44967202/pip-is-showing-error-lsb-release-a-returned-non-zero-exit-status-1)

### Rust

- [Compiling with rust](https://www.rust-lang.org/tools/install)
- [Packaging a Rust web service using Docker](https://blog.logrocket.com/packaging-a-rust-web-service-using-docker/)
- [docker/buildx - Value too large for defined data type](https://github.com/docker/buildx/issues/395)



<!-- MARKDOWN LINKS & IMAGES ; thks to https://github.com/othneildrew/Best-README-Template -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[travisci-shield]: https://travis-ci.com/nicolabs/nicobot.svg?branch=master
[travisci-link]: https://travis-ci.com/nicolabs/nicobot
[pypi-shield]: https://img.shields.io/pypi/v/nicobot?label=pypi
[pypi-link]: https://pypi.org/project/nicobot
[dockerhub-shield]: https://github.com/nicolabs/nicobot/workflows/Build%20and%20publish%20to%20Docker%20Hub%20(master%20branch)/badge.svg
[dockerhub-link]: https://hub.docker.com/r/nicolabs/nicobot
[docker-debian-signal-size]: https://img.shields.io/docker/image-size/nicolabs/nicobot/debian-signal.svg?label=debian-signal
[docker-debian-size]: https://img.shields.io/docker/image-size/nicolabs/nicobot/debian.svg?label=debian
[docker-alpine-size]: https://img.shields.io/docker/image-size/nicolabs/nicobot/alpine.svg?label=alpine
