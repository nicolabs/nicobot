# nicobot

Python package :

[![Build Status on 'master' branch][travisci-shield]][travisci-link] [![PyPi][pypi-shield]][pypi-link]

Docker images :

[![Build and publish to Docker Hub][dockerhub-shield]][dockerhub-link]  
[![Docker debian][docker-debian-size] ![Docker debian-signal][docker-debian-signal-size] ![Docker alpine][docker-alpine-size]](https://hub.docker.com/r/nicolabs/nicobot/tags)



## About

A collection of 🤟 *cool* 🤟 chat bots :

- **_Transbot_** is a demo chatbot interface to IBM Watson™ Language Translator service
- **_Askbot_** is a one-shot chatbot that will send a message and wait for an answer

**⚠️** My bots are cool, but they are absolutely **EXPERIMENTAL** use them at your own risk !

This project features :

- Participating in [Signal](https://www.signal.org/fr/) conversations
- Participating in [XMPP / Jabber](https://xmpp.org) conversations
- Using [IBM Watson™ Language Translator](https://cloud.ibm.com/apidocs/language-translator) cloud API

This document is about how to **use** the bots.
To get more details on how to **build / develop** with this project, see [Develop.md](Develop.md).



## Requirements & installation

The bots can be installed and run at your choice from :

- the Python package
- the source code
- the Docker images



### Python package installation

A classic (Python package) installation requires :

- Python 3 (>= 3.5) and pip ([should already be bundled with Python](https://pip.pypa.io/en/stable/installing)) ; e.g. on Debian : `sudo apt install python3 python3-pip`
- [signal-cli](https://github.com/AsamK/signal-cli) for the *Signal* backend (see [Using the Signal backend](#using-the-signal-backend) below for requirements)
- For *transbot* : an IBM Cloud account ([free account ok](https://www.ibm.com/cloud/free))

To install,  simply do :

    pip3 install nicobot

Then, you can run the bots by their name :

    # Runs the 'transbot' bot
    transbot [options...]

    # Runs the 'askbot' bot
    askbot [options...]



### Installation from source

To install from source you need to fulfill the requirements for a package installation (see above), then download the code and build it :

    git clone https://github.com/nicolabs/nicobot.git
    cd nicobot
    python3 setup.py build
    pip3 install -r requirements-runtime.txt

> **NOTE**
> Depending on your platform, `pip install` may trigger a compilation for some or all of the dependencies (i.e. when *Python wheels* are not available).
> In this case you may need to install more requirements for the build to succeed : looking at [the Dockerfiles in this project](Develop.md) may help you gather the exact list.

Now you can run the bots by their name as if they were installed via the package :

    # Runs the 'transbot' bot
    transbot [options...]

    # Runs the 'askbot' bot
    askbot [options...]



### Docker usage

At the present time there are [several Docker images available](https://hub.docker.com/r/nicolabs/nicobot/tags), with the following tags :

- **debian** : this is the most portable image ; in order to keep it relatively small it does not include the *Signal* backend (will throw an error if you try --> use XMPP instead)
- **debian-signal** : this is the most complete image ; it is also the largest one, but allows *Signal* messaging
- **alpine** : this should be the smallest image, but it's more complex to maintain and therefore might not always meet this expectation. Also, due to the lack/complexity of Alpine support for some Python, Java & native dependencies, images may support less platforms and it currently doesn't provide the Signal backend (you can use XMPP instead).

Please have a look at the status pills at the top of this document to get more details like status and size.

> **ADVICE**
> The current state of those images is such that I suggest you try the **alpine** image first and switch to a **debian\*** one if you need Signal or encounter runtime issues.

The container is invoked this way :

    docker ... [--signal-register <device name>] [--qrcode-options <qr options] <bot name> [<bot arguments>]

- `--signal-register` is Signal-specific. It will display a QR code in the console : scan it with the Signal app on the device to link the bot with (it will simply do the *signal-cli link* command inside the container ; read more about this later in this document). If this option is not given and the _signal_ backend is used, it will use the `.local/share/signal-cli` directory from the container (you _have_ to mount it) or fail. This option takes a custom device name as its argument.
- `--qrcode-options` is Signal-specific. It takes as argument a string of options to pass to the QR code generation command (see [python-qrcode](https://github.com/lincolnloop/python-qrcode)).
- `<bot name>` is either `transbot` or `askbot`
- `<bot arguments>` is the list of arguments to pass to the bot (see bots' usage)

If any doubt, just invoke the image without argument to print the inline help statement.

Sample command to start a container :

    docker run --rm -it -v "$(pwd)/myconfdir:/etc/nicobot" nicolabs/nicobot transbot -C /etc/nicobot

In this example `myconfdir` is a local directory with configuration files for the bot (`-C` option), but you could also set most parameters on the command line.

You can also use _docker volumes_ to persist _signal_, _XMPP_ and other configuration :

    docker run --rm -it -v "$(pwd)/myconfdir:/usr/src/app" -v "$HOME/.local/share/signal-cli:/root/.local/share/signal-cli" -v "$HOME/.omemo:/usr/src/app/.omemo" nicolabs/nicobot transbot

All options that can be passed to the bots' command line can also be passed to the docker command line.



## How to use the bots



### Askbot usage

*Askbot* is a one-shot chatbot that will send a message and wait for an answer.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

When run, it will send a message and wait for an answer, in different ways (see options below).
Once the configured conditions are met, the bot will terminate and print the result in [JSON](https://www.json.org/) format.
This JSON structure will have to be parsed in order to retrieve the answer and determine what were the exit(s) condition(s).



#### Main configuration options

Run `askbot -h` to get a description of all options.

Below are the most important configuration options for this bot (please also check the generic options below) :

- **--max-count <integer>** will define how many messages to read at maximum before exiting. This allows the recipient to split the answer in several messages for instance. However currently all messages are returned by the bot at once at the end, so they cannot be parsed on the fly by an external program. To give _x_ tries to the recipient, run _x_ times this bot instead.
- **--pattern <name> <pattern>** defines a pattern that will end the bot when matched. This is the way to detect an answer. It takes 2 arguments : a symbolic name and a [regular expression pattern](https://docs.python.org/3/howto/regex.html#regex-howto) that will be tested against each message. You can define multiple patterns in the same command line, hence the `<name>` argument, which will allow identifying which pattern(s) matched.

Sample configuration can be found in `tests/askbot-sample-conf`.



#### Examples

##### Simple example (with Jabber)

    askbot -b jabber -U mybot@myserver.im -r me@myserver.im --jabber-password 'Myb0tp@SSword' -m "Hello You !" -p bye 'bye'

Will say 'Hello You !' to me@myserver.im, and for a message containing 'bye' to quit.
If the recipient handles it, the communication will be end-to-end encrypted with OMEMO.

##### More complex example (and with Signal)

    askbot -m "Do you like me ?" -p yes '(?i)\b(yes|ok)\b' -p no '(?i)\bno\b' -p cancel '(?i)\b(cancel|abort)\b' --max-count 3 -b signal -U '+33123456789' --recipient '+34987654321'

The previous command will :

1. Send the message "Do you like me" to +34987654321 on Signal
2. Wait for a maximum of 3 messages in answer and return
3. Or return immediately if a message matches one of the given patterns labeled 'yes', 'no' or 'cancel'

If the user *+34987654321* replies with 2 messages :

 1. I don't know
 2. Ok then : NO !

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

A few notes about the _regex_ usage in this example : in `-p yes '(?i)\b(yes|ok)\b'` :
- `(?i)` enables case-insensitive match
- `\b` means "edge of a word" ; it is used to make sure the wanted text will not be part of another word (e.g. `tik tok` would match `ok` otherwise)
- Note that a regex _search_ is done on the messages (not a _match_) so it is not required to specify a full _regular expression_ with `^` and `$` (though you may do, if you want to). This makes the pattern more readable.
- The pattern is labeled 'yes' so it can be easily identified in the JSON output and counted as a positive match

You may also have noticed the importance of defining patterns that don't overlap (here the message matched both 'yes' and 'no') or being ready to handle unknown states.

To make use of the bot, you could parse its output with a script, or with a command-line client like [jq](https://stedolan.github.io/jq/).

Here's an example snippet for a _Python_ program to extract the name of the matched patterns :

```python
# loads the JSON output
output = json.loads('{ "max_responses": false, "messages": [...] }')
# 'matched' is the list of the names of the patterns that matched against the last message
matched = [ p['name'] for p in output['messages'][-1]['patterns'] if p['matched'] ]
# e.g. matched = `['yes','no']`
```


### Transbot usage

*Transbot* is a demo chatbot interface to IBM Watson™ Language Translator service.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

It is triggered by messages :
- either matching the configured pattern
- or containing a keyword from a given list

When triggered, it will answer with a translation of the given text.

It will reply either to direct messages or to a group chat, depending on the given parameters.

The sample configuration in `tests/transbot-sample-conf`, demoes how to make the bot answer messages given in the form `nicobot <text_to_translate> in <language>` (or simply `nicobot  <text_to_translate>`, into the current language) with a translation of _<text_to_translate>_.

Transbot can also pick a random language to translate into ; the sample configuration file shows how to make it translate messages containing "Hello" or "Goodbye" into a random language.


### Quick start

1. Install **nicobot** (see above)
2. [Create a *Language Translator* service instance on IBM Cloud](https://cloud.ibm.com/catalog/services/language-translator) and [get the URL and API key from your console](https://cloud.ibm.com/resources?groups=resource-instance)
3. Make a local copy of files in [`tests/transbot-sample-conf/`](tests/transbot-sample-conf/) and fill the `ibmcloud_url` and `ibmcloud_apikey` values into `config.yml`
4. Run `transbot -C ./transbot-sample-conf` (with docker it will be something like `docker run -it "$(pwd)/transbot-sample-conf:/etc/nicobot" nicolabs/nicobot transbot -C /etc/nicobot`)
5. Type `Hello world` in the console : the bot will print a random translation of "Hello World"
6. Type `Bye nicobot` : the bot will terminate

You may now explore the dedicated chapters below for more options, including sending & receiving messages through *XMPP* or *Signal* instead of keyboard & console.



#### Main configuration options and files

This paragraph introduces the most important parameters to make this bot work. Please also check the generic options below ; finally run `transbot -h` to get an exact list of all options.

The bot needs several configuration files that will be generated / downloaded the first time if not provided :

- **--keyword** and **--keywords-file** will help you generate a list of translations for the given keywords so they will trigger the bot even if written in other languages. To do it, run this **a first time** : `transbot --keyword <a_keyword> --keyword <another_keyword> ...` to download all known translations for these keywords and save them into a `keywords.json` file. Next time you run the bot, **don't** use the `--keyword` option : it will reuse this saved keywords list. You can use `--keywords-file` to change the file name.
- **--languages-file** : The first time the bot runs it will download the list of supported languages (to translate into) into `languages.<locale>.json` and reuse it afterwards. You can edit it, to keep just the set of languages you want for instance. You can also use the `--locale` option to indicate the desired locale.
- **--locale** will select the locale to use for default translations (with no target language specified) and as the default parsing language for keywords.
- **--ibmcloud-url** and **--ibmcloud-apikey** take arguments you can obtain from your IBM Cloud account ([create a Language Translator instance](https://cloud.ibm.com/apidocs/language-translator) then go to [the resource list](https://cloud.ibm.com/resources?groups=resource-instance))

The patterns and custom texts the bot speaks & recognizes can be defined in the **i18n.\<locale>.yml** file :
- *Transbot* will say "Hello" when started and "Goodbye" before shutting down : you can configure those banners in this file.
- It also defines the pattern that terminates the bot.

A sample configuration is available in the `tests/transbot-sample-conf/` directory.



### Generic instructions



#### Common options

The following options are common to both bots :

- **--config-file** and **--config-dir** let you change the default configuration directory and file. All configuration files will be looked up from this directory ; `--config-file` allows overriding the location of `config.yml`.
- **--backend** selects the *chatter* system to use : it currently supports "console", "signal" and "jabber" (see below)
- **--stealth** will make the bot connect and listen to messages but print answers to the console instead of sending it ; useful to observe the bot's behavior in a real chatroom...



#### Configuration file : config.yml

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



#### Using the Jabber/XMPP backend

By specifying `--backend jabber` you can make the bot chat with XMPP (a.k.a. Jabber) users.


##### Jabber-specific options

- `--jabber-username` and `--jabber-password` are the JabberID (e.g. *myusername@myserver.im*) and password of the bot's account used to send and read messages. If `--jabber-username` is missing, `--username` will be used.
- `--jabber-recipient` is the JabberID of the person to send the message to. If missing, `--recipient` will be used.


##### Example

    transbot -C tests/transbot-sample-conf -b jabber -U mybot@myserver.im -r me@myserver.im`

With :

- `-b jabber` to select the XMPP/Jabber backend
- `-U mybot@myserver.im` the *JabberID* of the bot
- `-r me@myserver.im` the *JabberID* of the correspondent



#### Using the Signal backend

By specifying `--backend signal` you can make the bot chat with Signal users.


##### Prerequistes

For package and source installations, you must first [install and configure *signal-cli*](https://github.com/AsamK/signal-cli#installation).

For all installations, you must [*register* or *link*](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) the computer where the bot will run ; e.g. :

    signal-cli link --name MyComputer

With docker images you can do this registration by using the `--signal-register` option. This will save the registration files into `/root/.local/share/signal-cli/` inside the container. If this location is bound to a persistent volume, it can be reused on next launch.

Please see [signal-cli's man page](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) for more details about the registration process.


##### Signal-specific options

- `--signal-username` selects the account to use to send and read message : it is a phone number in international format (e.g. `+33123456789`). In `config.yml`, make sure to put quotes around it to prevent YAML thinking it's an integer (because of the 'plus' sign). If missing, `--username` will be used.
- `--signal-recipient` and `--signal-group` select the recipient (only one of them should be given). Make sure `--signal-recipient` is in international phone number format and `--signal-group` is a base 64 group ID (e.g. `--signal-group "mABCDNVoEFGz0YeZM1234Q=="`). If `--signal-recipient` is missing, `--recipient` will be used. To get the IDs of the groups you are in, run : `signal-cli -U +336123456789 listGroups`

Example :

    transbot -b signal -U +33612345678 -g "mABCDNVoEFGz0YeZM1234Q==" --ibmcloud-url https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/a234567f-4321-abcd-efgh-1234abcd7890 --ibmcloud-apikey "f5sAznhrKQyvBFFaZbtF60m5tzLbqWhyALQawBg5TjRI"



## External resources

- [IBM Watson Language Translator service](https://cloud.ibm.com/catalog/services/language-translator)
- Signal messaging : https://signal.org
- XMPP resources : https://xmpp.org/software/libraries.html
- OMEMO compatible clients : https://omemo.top/
- *Gaijim*, a Windows/MacOS/Linux XMPP client with OMEMO support : [gajim.org](https://gajim.org/) | [dev.gajim.org/gajim](https://dev.gajim.org/gajim)
- *Conversations*, an Android XMPP client with OMEMO support and paid hosting : https://conversations.im



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
