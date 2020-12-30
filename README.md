# nicobot

Python package :

[![Build Status on 'master' branch](https://travis-ci.com/nicolabs/nicobot.svg?branch=master)](https://travis-ci.com/nicolabs/nicobot)   [![PyPi](https://img.shields.io/pypi/v/nicobot?label=pypi)](https://pypi.org/project/nicobot)

Docker :

![Build and publish to Docker Hub](https://github.com/nicolabs/nicobot/workflows/Build%20and%20publish%20to%20Docker%20Hub/badge.svg)  
![Docker debian-slim](https://img.shields.io/docker/image-size/nicolabs/nicobot/debian-slim.svg?label=debian-slim)
![layers](https://img.shields.io/microbadger/layers/nicolabs/nicobot/debian-slim.svg)  
![Docker debian](https://img.shields.io/docker/image-size/nicolabs/nicobot/debian.svg?label=debian)
![layers](https://img.shields.io/microbadger/layers/nicolabs/nicobot/debian.svg)  
![Docker alpine](https://img.shields.io/docker/image-size/nicolabs/nicobot/alpine.svg?label=alpine)
![layers](https://img.shields.io/microbadger/layers/nicolabs/nicobot/alpine.svg)  


## About

A collection of 🤟 *cool* 🤟 chat bots :

- *Transbot* is a demo chatbot interface to IBM Watson™ Language Translator service
- *Askbot* is a one-shot chatbot that will send a message and wait for an answer

⚠️ My bots are cool, but they are absolutely **EXPERIMENTAL** use them at your own risk ⚠️

This project features :

- Participating in [Signal](https://www.signal.org/fr/) conversations
- Participating in [XMPP / Jabber](https://xmpp.org) conversations
- Using [IBM Watson™ Language Translator](https://cloud.ibm.com/apidocs/language-translator) cloud API


## Requirements & installation

The bots can be installed and run from :

- the Python package
- the source code
- the Docker images

### Python package installation

A classic (Python package) installation requires :

- Python 3 (>= 3.5) and pip ([should be bundled with Python](https://pip.pypa.io/en/stable/installing)) ; e.g. on Debian : `sudo apt install python3 python3-pip`
- [signal-cli](https://github.com/AsamK/signal-cli) for the *Signal* backend (see [Using the Signal backend] below for requirements)
- For *transbot* : an IBM Cloud account ([free account ok](https://www.ibm.com/cloud/free))

To install,  simply do :

    pip3 install nicobot

Then, you can run the bots by their name, thanks to the provided commands :

    # Runs the 'transbot' bot
    transbot [options...]
    # Runs the 'askbot' bot
    askbot [options...]



### Installation from source

To install from source you need to fulfill the same requirements as for a package installation (see above), then download the code and build it :

    git clone https://github.com/nicolabs/nicobot.git
    cd nicobot
    pip3 install -r requirements-runtime.txt

Now you can run the bots by their name as if they were installed via the package :

    # Runs the 'transbot' bot
    transbot [options...]
    # Runs the 'askbot' bot
    askbot [options...]



### Docker usage

There are [several Docker images available](https://hub.docker.com/repository/docker/nicolabs/nicobot), with the following tags :

- **debian** : if you have several images with the _debian_ base, this may be the most space-efficient (as base layers will be shared with other images)
- **debian-slim** : if you want a smaller-sized image and you don't run other images based on the  _debian_ image (as it will not share as much layers as with the above `debian` tag)
- **alpine** : this should be the smallest image in theory, but it's more complex to maintain and thereore might not meet this expectation ; please check/test before use

The current state of those images is such that I suggest you try the _debian-slim_ image first and switch to another one if you encounter issues or have a specific use case to solve.

Sample command to start a container :

    docker run --rm -it -v "myconfdir:/etc/nicobot" nicolabs/nicobot:debian-slim transbot -C /etc/nicobot

In this example `myconfdir` is a local directory with configuration files for the bot (`-C` option), but you could set all arguments on the command line if you don't want to deal with files.

You can also use _docker volumes_ to persist _signal_ and _IBM Cloud_ credentials and configuration :

    docker run --rm -it -v "myconfdir:/etc/nicobot" -v "$HOME/.local/share/signal-cli:/root/.local/share/signal-cli" nicolabs/nicobot:debian-slim transbot -C /etc/nicobot

All options that can be passed to the bots' command line can also be passed to the docker command line.



## Transbot instructions

*Transbot* is a demo chatbot interface to IBM Watson™ Language Translator service.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

It detects configured patterns or keywords in messages (either received directly or from a group chat) and answers with a translation of the given text.

The sample configuration in `tests/transbot-sample-conf`, demoes how to make the bot answer messages given in the form `nicobot <text_to_translate> in <language>` (or simply `nicobot  <text_to_translate>`, into the current language) with a translation of _<text_to_translate>_.

Transbot can also pick a random language to translate into ; the sample configuration file shows how to make it translate messages containing "Hello" or "Goodbye" into a random language.

### Quick start

1. Install **nicobot** (see above)
2. [Create a *Language Translator* service instance on IBM Cloud](https://cloud.ibm.com/catalog/services/language-translator) and [get the URL and API key from your console](https://cloud.ibm.com/resources?groups=resource-instance)
3. Fill them into `tests/transbot-sample-conf/config.yml` (`ibmcloud_url` and `ibmcloud_apikey`)
4. Run `transbot -C tests/transbot-sample-conf` (with docker it will be something like `docker run -it "tests/transbot-sample-conf:/etc/nicobot" nicolabs/nicobot:debian-slim transbot -C /etc/nicobot`)
5. Type `Hello world` in the console : the bot will print a random translation of "Hello World"
6. Type `Bye nicobot` : the bot will terminate

You may now explore the dedicated chapters below for more options, including sending & receiving messages through *XMPP* or *Signal* instead of keyboard & console.



### Main configuration options and files

This paragraph introduces the most important options to make this bot work. Please also check the generic options below, and finally run `transbot -h` to get an exact list of all options.

The bot needs several configuration files that will be generated / downloaded the first time if not provided :

- **--keyword** and **--keywords-file** will help you generate the list of keywords that will trigger the bot. To do this, run `transbot --keyword <a_keyword> --keyword <another_keyword> ...` **a first time** : this will download all known translations for these keywords and save them into a `keywords.json` file. Next time you run the bot, **don't** use the `--keyword` option : it will reuse this saved keywords list. You can use `--keywords-file` to change the file name.
- **--languages-file** : The first time the bot runs it will download the list of supported languages into `languages.<locale>.json` and reuse it afterwards. You can edit it, to keep just the set of languages you want for instance. You can also use the `--locale` option to indicate the desired locale.
- **--locale** will select the locale to use for default translations (with no target language specified) and as the default parsing language for keywords.
- **--ibmcloud-url** and **--ibmcloud-apikey** take arguments you can obtain from your IBM Cloud account ([create a Language Translator instance](https://cloud.ibm.com/apidocs/language-translator) then go to [the resource list](https://cloud.ibm.com/resources?groups=resource-instance))

The **i18n.\<locale>.yml** file contains localization strings for your locale :
- *Transbot* will say "Hello" when started and "Goodbye" before shutting down : you can configure those banners in this file.
- It also defines the pattern that terminates the bot.

A sample configuration is available in the `tests/transbot-sample-conf/` directory.



## Askbot instructions

*Askbot* is a one-shot chatbot that will send a message and wait for an answer.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

When run, it will send a message and wait for an answer, in different ways (see options below).
Once the configured conditions are met, the bot will terminate and print the result in [JSON](https://www.json.org/) format.
This JSON structure will have to be parsed in order to retrieve the answer and determine what were the exit(s) condition(s).

### Main configuration options

Run `askbot -h` to get a description of all options.

Below are the most important configuration options for this bot (please also check the generic options below) :

- **--max-count <integer>** will define how many messages to read at maximum before exiting. This allows the recipient to split the answer in several messages for instance. However currently all messages are returned by the bot at once at the end, so they cannot be parsed on the fly by an external program. To give _x_ tries to the recipient, run _x_ times this bot instead.
- **--pattern <name> <pattern>** defines a pattern that will end the bot when matched. This is the way to detect an answer. It takes 2 arguments : a symbolic name and a [regular expression pattern](https://docs.python.org/3/howto/regex.html#regex-howto) that will be tested against each message. It can be passed several times in the same command line, hence the `<name>` argument, which will allow identifying which pattern(s) matched.

Sample configuration can be found in `tests/askbot-sample-conf`.

### Example

The following command will :

1. Send the message "Do you like me" to +34987654321 on Signal
2. Wait for a maximum of 3 messages in answer and return
3. Or return immediately if a message matches one of the given patterns labeled 'yes', 'no' or 'cancel'

    askbot -m "Do you like me ?" -p yes '(?i)\b(yes|ok)\b' -p no '(?i)\bno\b' -p cancel '(?i)\b(cancel|abort)\b' --max-count 3 -b signal -U '+33123456789' --recipient '+34987654321'

If the user *+34987654321* would reply :

 > I don't know    
 > Ok then : NO !
 
 Then the output would be :

```json
{
    "max_responses": false,
    "messages": [{
        "message": "I don't know...",
        "patterns": [{
            "name": "yes",
            "pattern": "(?i)\\b(yes|ok)\\b",
            "matched": false
        }, {
            "name": "no",
            "pattern": "(?i)\\bno\\b",
            "matched": false
        }, {
            "name": "cancel",
            "pattern": "(?i)\\b(cancel|abort)\\b",
            "matched": false
        }]
    }, {
        "message": "Ok then : NO !",
        "patterns": [{
            "name": "yes",
            "pattern": "(?i)\\b(yes|ok)\\b",
            "matched": true
        }, {
            "name": "no",
            "pattern": "(?i)\\bno\\b",
            "matched": true
        }, {
            "name": "cancel",
            "pattern": "(?i)\\b(cancel|abort)\\b",
            "matched": false
        }]
    }]
}
```

A few notes about the example : in `-p yes '(?i)\b(yes|ok)\b'` :
- `(?i)` enables case-insensitive match
- `\b` means "edge of a word" ; it is used to make sure the wanted text will not be part of another word (e.g. `tik tok` would match `ok` otherwise)
- Note that a _search_ is done on the messages (not a _match_) so it is not required to specify a full _regular expression_ with `^` and `$` (though you may do, if you want to). This makes the pattern more readable.
- The pattern is labeled 'yes' so it can be easily identified in the JSON output and counted as a positive match

Also you may have noticed the importance of defining patterns that don't overlap (here the message matched both 'yes' and 'no') or being ready to handle unknow states.

You could parse the output with a script, or with a command-line client like [jq](https://stedolan.github.io/jq/).
For instance, to get the name of the matched patterns in Python :

```python
# loads the JSON output
output = json.loads('{ "max_responses": false, "messages": [...] }')
# 'matched' is the list of the names of the patterns that matched against the last message, e.g. `['yes','no']`
matched = [ p['name'] for p in output['messages'][-1]['patterns'] if p['matched'] ]
```


## Generic instructions


### Common options

The following options are common to both bots :

- **--config-file** and **--config-dir** let you change the default configuration directory and file. All configuration files will be looked up from this directory ; `--config-file` allows overriding the location of `config.yml`.
- **--backend** selects the *chatter* system to use : it currently supports "console", "signal" and "jabber" (see below)
- **--stealth** will make the bot connect and listen to messages but print answers to the console instead of sending it ; useful to observe the bot's behavior in a real chatroom...


### Configuration file : config.yml

Options can also be taken from a configuration file.
By default it reads the `config.yml` file in the current directory but can be changed with the `--config-file` and `--config-dir` options.

This file is in YAML format with all options at root level.
Keys are named after the command line options, with middle dashes `-` replaced with underscores `_` and a `s` appended for lists (option `--ibmcloud-url https://api...` will become `ibmcloud_url: https://api...` and `--keywords-file 1.json --keywords-file 2.json` will become :
```yaml
keywords_files:
    - 1.json
    - 2.json
```

See also sample configurations in the `tests/` directory.

If unsure,  please first review [YAML syntax](https://yaml.org/spec/1.1/#id857168) as it has a few traps.



### Using the Jabber/XMPP backend

By using `--backend jabber` you can make the bot chat with XMPP (a.k.a. Jabber) users.

#### Jabber-specific options

- `--jabber-username` and `--jabber-password` are the JabberID (e.g. *myusername@myserver.im*) and password of the bot's account used to send and read messages. If `--jabber-username` missing, `--username` will be used.
- `--jabber-recipient` is the JabberID of the person to send the message to. If missing, `--recipient` will be used.

#### Example

    transbot -C tests/transbot-sample-conf -b jabber -U mybot@myserver.im -r me@myserver.im`

With :

- `-b jabber` to select the XMPP/Jabber backend
- `-U mybot@myserver.im` the *JabberID* of the bot
- `-r me@myserver.im` the *JabberID* of the correspondent



### Using the Signal backend

By using `--backend signal` you can make the bot chat with Signal users.

#### Prerequistes

You must first [install and configure *signal-cli*](https://github.com/AsamK/signal-cli#installation).

Then you must [*register* or *link*](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) the computer when the bot will run ; e.g. :

    signal-cli link --name MyComputer

With docker images it is recommended to do this registration on a computer (may be the host but not required), then share the `$HOME/.local/share/signal-cli` as the `/root/.local/share/signal-cli` volume. Otherwise the bot will ask to link again everytime it starts.

Please see the [man page](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) for more details.

#### Signal-specific options

- `--signal-username` selects the account to use to send and read message : it is a phone number in international format (e.g. `+33123456789`). In `config.yml`, make sure to put quotes around it to prevent YAML thinking it's an integer (because of the 'plus' sign). If missing, `--username` will be used.
- `--signal-recipient` and `--signal-group` select the recipient (only one of them should be given). Make sure `--signal-recipient` is in international phone number format and `--signal-group` is a base 64 group ID (e.g. `--signal-group "mABCDNVoEFGz0YeZM1234Q=="`). If `--signal-recipient` is missing, `--recipient` will be used. To get the IDs of the groups you are in, run : `signal-cli -U +336123456789 listGroups`

Example :

    transbot -b signal -U +33612345678 -g "mABCDNVoEFGz0YeZM1234Q==" --ibmcloud-url https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/a234567f-4321-abcd-efgh-1234abcd7890 --ibmcloud-apikey "f5sAznhrKQyvBFFaZbtF60m5tzLbqWhyALQawBg5TjRI"



## Development

Install Python dependencies (both for building and running) with :

    pip3 install -r requirements-build.txt -r requirements-runtime.txt

To run unit tests :

    python3 -m unittest discover -v -s tests

To run directly from source (without packaging) :

    python3 -m nicobot.askbot [options...]

To build locally (more at [pypi.org](https://packaging.python.org/tutorials/packaging-projects/)) :

    python3 setup.py sdist bdist_wheel

To upload to test.pypi.org :

    # Defines username and password (or '__token__' and API key) ; alternatively CLI `-u` and `-p` options or user input may be used (or even certificates, see `python3 -m twine upload --help`)
    TWINE_USERNAME=__token__
    TWINE_PASSWORD=`pass pypi/test.pypi.org/api_token | head -1`
    python3 -m twine upload --repository testpypi dist/*

To upload to PROD pypi.org :

    TODO

Otherwise, it is automatically tested, built and uploaded to pypi.org using _Travis CI_ on each push to GitHub.


### Docker build

There are several Dockerfiles, each made for specific use cases (see [Docker-usage](#Docker-usage) above) :

`Dockerfile-debian` and `Dockerfile-debian-slim` are quite straight and very similar. They still require multi-stage build to address enough platforms. 

`Dockerfile-alpine` requires a [multi-stage build](https://docs.docker.com/develop/develop-images/multistage-build/) anyway because most of the Python dependencies need to be compiled first.
The result however should be a far smaller image than with a Debian base. 

> Note that the _signal-cli_ backend needs a _Java_ runtime environment, and also _rust_ dependencies to support Signal's group V2. This currently doubles the size of the images and ruins the advantage of alpine over debian...

Those images are limited to CPU architectures :
- supported by [the base images](https://hub.docker.com/_/python)
- for which the Python dependencies are built or able to build
- for which the native dependencies of signal (libzkgroup) can be built (alpine only)

Simple _build_ command (single architecture) :

    docker build -t nicolabs/nicobot:debian-slim -f Dockerfile-debian-slim .

Sample _buildx_ command (multi-arch) :

    docker buildx build --platform linux/386,linux/amd64,linux/arm/v6,linux/arm/v7,linux/arm64,linux/ppc64le,linux/s390x -t nicolabs/nicobot:debian-slim -f Dockerfile-debian-slim .

Then run with the provided sample configuration :

    docker run --rm -it -v "$(pwd)/tests:/etc/nicobot" nicolabs/nicobot:debian-slim askbot -c /etc/nicobot/askbot-sample-conf/config.yml

_Github actions_ are currently used (see [dockerhub.yml](.github/workflows/dockerhub.yml) to automatically build and push the images to Docker Hub so they are available whenever commits are pushed to the _master_ branch.

The images have all the bots inside, as they only differ by one script from each other.
The `entrypoint.sh` script takes the name of the bot to invoke as its first argument, then its own options and finally the bot's arguments.


### Versioning

The command-line option to display the scripts' version relies on _setuptools_scm_, which extracts it from the underlying git metadata.
This is convenient because the developer does not have to manually update the version (or forget to do it prior a release), however it either requires the version to be fixed inside a package or the `.git` directory to be present.

There were several options among which the following one has been retained :
- Running `setup.py` creates / updates the version inside the `version.py` file
- The scripts then load this module at runtime

The remaining requirement is that `setup.py` must be run before the version can be extracted. In exchange :
- it does not require _setuptools_ nor _git_ at runtime
- it frees us from having the `.git` directory around at runtime ; this is especially useful to make the docker images smaller



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

Python libraries :

- [xmpppy](https://github.com/xmpppy/xmpppy) : this library is very easy to use but it does allow easy access to thread or timestamp, and no OMEMO...
- [github.com/horazont/aioxmpp](https://github.com/horazont/aioxmpp) : officially referenced library from xmpp.org, seems the most complete but misses practical introduction and [does not provide OMEMO OOTB](https://github.com/horazont/aioxmpp/issues/338).
- [slixmpp](https://lab.louiz.org/poezio/slixmpp) : seems like a cool library too and pretends to require minimal dependencies ; plus it [supports OMEMO](https://lab.louiz.org/poezio/slixmpp-omemo/) so it's the winner. [API doc](https://slixmpp.readthedocs.io/).
