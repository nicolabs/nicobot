# nicobot

[![Build Status on 'master' branch](https://travis-ci.com/nicolabs/nicobot.svg?branch=master)](https://travis-ci.com/nicolabs/nicobot)

A collection of 🤟 *cool* 🤟 chat bots :

- *Transbot* is a demo chatbot interface to IBM Watson™ Language Translator service
- *Askbot* is a one-shot chatbot that will throw a question and wait for an answer

> My bots are cool, but they are absolutely **EXPERIMENTAL** use them at your own risk !

This project features :

- Participating in [Signal](https://www.signal.org/fr/) conversations
- Using [IBM Watson™ Language Translator](https://cloud.ibm.com/apidocs/language-translator) cloud API


## Requirements & installation

Requires :

- Python 3 (>= 3.4.2)
- [signal-cli](https://github.com/AsamK/signal-cli) (for the *Signal* backend)
- For *transbot* : an IBM Cloud account ([free account ok](https://www.ibm.com/cloud/free))

Install Python dependencies with :

    pip3 install -r requirements.txt

See below for *Signal* requirements.



## Transbot

*Transbot* is a demo chatbot interface to IBM Watson™ Language Translator service.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

The included sample configuration in `tests/transbot-sample-conf`, demoes how to make it translate any message like `nicobot <message> in chinese` or simply `nicobot  <message>` (into the current language).

It can also automatically translate messages containing keywords into a random language.
The sample configuration shows how to make it translate any message containing "Hello" or "Goodbye" in many languages.

### Quick start

1. Install prerequisites ; for Debian systems this will look like :
    ```
    sudo apt install python3 python3-pip
    git clone https://github.com/nicolabs/nicobot.git
    cd nicobot
    pip3 install -r requirements.txt
    ```
2. [Create a *Language Translator* service instance on IBM Cloud](https://cloud.ibm.com/catalog/services/language-translator) and [get the URL and API key from your console](https://cloud.ibm.com/resources?groups=resource-instance)
3. Fill them into `tests/transbot-sample-conf/config.yml` (`ibmcloud_url` and `ibmcloud_apikey`)
4. Run `python3 nicobot/transbot.py -C tests/transbot-sample-conf`
5. Input `Hello world` in the console : the bot will print a random translation of "Hello World"
6. Input `Bye nicobot` : the bot will terminate

If you want to send & receive messages through *Signal* instead of reading from the keyboard & printing to the console :

1. Install and configure `signal-cli` (see below for details)
2. Run `python3 nicobot/transbot.py -C tests/transbot-sample-conf -b signal -U '+33123456789' -r '+34987654321'` with `-U +33123456789` your *Signal* number and `-r +33987654321` the one of the person you want to make the bot chat with

See dedicated chapters below for more options...


### Main configuration options and files

Run `transbot.py -h` to get a description of all options.

Below are the most important configuration options for this bot (please also check the generic options below) :

- **--keyword** and **--keywords-file** will help you generate the list of keywords that will trigger the bot. To do this, run `transbot.py --keyword <a_keyword> --keyword <another_keyword> ...` a **first time with** : this will download all known translations for these keywords and save them into a `keywords.json` file. Next time you run the bot, **don't** use the `--keyword` option : it will reuse this saved keywords list. You can use `--keywords-file` to change the default name.
- **--languages-file** : The first time the bot runs, it will download the list of supported languages into `languages.<locale>.json` and reuse it afterwards but you can give it a specific file with the set of languages you want. You can use `--locale` to set the desired locale.
- **--locale** will select the locale to use for default translations (with no target language specified) and as the default parsing language for keywords.
- **--ibmcloud-url** and **--ibmcloud-apikey** can be obtained from your IBM Cloud account ([create a Language Translator instance](https://cloud.ibm.com/apidocs/language-translator) then go to [the resource list](https://cloud.ibm.com/resources?groups=resource-instance))

The **i18n.\<locale>.yml** file contains localization strings for your locale and fun :
- *Transbot* will say "Hello" when started and "Goodbye" before shutting down : you can configure those banners in this file.
- It also defines the pattern that terminates the bot.

A sample configuration is available in the `tests/transbot-sample-conf/` directory.



## Askbot

*Askbot* is a one-shot chatbot that will throw a question and wait for an answer.

**Again, this is NOT STABLE code, there is absolutely no warranty it will work or not harm butterflies on the other side of the world... Use it at your own risk !**

When run, it will send a message (if provided) and wait for an answer, in different ways (see options below).
Once the conditions are met, the bot will terminate and print the result in [JSON](https://www.json.org/) format.
This JSON structure will have to be parsed in order to retrieve the answer and determine what were the exit(s) condition(s).

### Main configuration options

Run `askbot.py -h` to get a description of all options.

Below are the most important configuration options for this bot (please also check the generic options below) :

- **--max-count <integer>** will define how many messages to read at maximum before exiting. This allows the recipient to send several messages in answer. However currently all of those messages are returned at once after they all have been read by the bot so they cannot be parsed on the fly. To give _x_ tries to the recipient, run _x_ times this bot instead.
- **--pattern <name> <pattern>** defines a pattern that will end the bot when matched. It takes 2 arguments : a symbolic name and a [regular expression pattern](https://docs.python.org/3/howto/regex.html#regex-howto) that will be tested against each message. It can be passed several times in the same command line, hence the `<name>` argument, which will allow identifying which pattern(s) matched.

Sample configuration can be found in `tests/askbot-sample-conf`.

### Example

The following command will :

- Send the message "Do you like me" to +34987654321 on Signal
- Wait for a maximum of 3 messages in answer and return
- Or return immediately if one message matches one of the given patterns labeled 'yes', 'no' or 'cancel'

    python3 askbot.py -m "Do you like me ?" -p yes '(?i)\b(yes|ok)\b' -p no '(?i)\bno\b' -p cancel '(?i)\b(cancel|abort)\b' --max-count 3 -b signal -U '+33123456789' --recipient '+34987654321'

If the user *+34987654321* would reply "I don't know" then "Ok then : NO !", the output would be :

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
- Note that a _search_ is done on the messages (not a _match_) so it is not required to specify a full expression with `^` and `$` (though you may if you want). This makes the pattern more readable.
- The pattern is labeled 'yes' so it can easily be identified in the JSON output and checked for a positive match

Also you can notice the importance to define patterns that don't overlap (here the message matched both 'yes' and 'no') or to handle unknow states.

You could parse the output with a script, or with a command-line client like [jq](https://stedolan.github.io/jq/).
For instance, to get the name of the matched patterns in Python :

```python
output = json.loads('{ "max_responses": false, "messages": [...] }')
matched = [ p['name'] for p in output['messages'][-1]['patterns'] if p['matched'] ]
```

It will return the list of the names of the patterns that matched the last message ; e.g. `['yes','no']` in our above example.


## Generic instructions


### Main generic options

The following options are common to both bots :

- **--config-file** and **--config-dir** let you change the default configuration directory and file. All configuration files will be looked up from this directory ; `--config-file` allows overriding the location of `config.yml`.
- **--backend** selects the *chatter* system to use : it currently supports "console" and "signal" (see below)
- **--stealth** will make the bot connect and listen to messages but print any answer instead of sending it ; useful to observe the bot's behavior in a real chatroom...


### Config.yml configuration file

Options can also be taken from a configuration file : by default it reads the `config.yml` file in the current directory but can be changed with the `--config-file` and `--config-dir` options.
This file is in YAML format with all options at root level. Keys have the same name as command line options, with middle dashes `-` replaced with underscores `_` and a `s` appended for lists (options `--ibmcloud-url https://api...` will become `ibmcloud_url: https://api...` and `--keywords-file 1.json --keywords-file 2.json` will become :
```yaml
keywords_files:
    - 1.json
    - 2.json
```

See also sample configurations in the `tests/` directory.

Please first review [YAML syntax](https://yaml.org/spec/1.1/#id857168) if you don't know about YAML.



## Using the Jabber/XMPP backend

By using `--backend jabber` you can make the bot chat with XMPP (a.k.a. Jabber) users.

### Jabber-specific options

- `--jabber-username` and `--jabber-password` are the JabberID (e.g. *myusername@myserver.im*) and password of the bot's account used to send and read messages. If `--jabber-username` missing, `--username` will be used.
- `--jabber-recipient` is the JabberID of the person to send the message to. If missing, `--recipient` will be used.



## Using the Signal backend

By using `--backend signal` you can make the bot chat with Signal users.

### Prerequistes

You must first [install and configure *signal-cli*](https://github.com/AsamK/signal-cli#installation).

Then you must [*register* or *link*](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) the computer when the bot will run ; e.g. :

    signal-cli link --name MyComputer

Please see the [man page](https://github.com/AsamK/signal-cli/blob/master/man/signal-cli.1.adoc) for more details.


### Signal-specific options

- `--signal-username` selects the account to use to send and read message : it is a phone number in international format (e.g. `+33123456789`). In `config.yml`, make sure to put quotes around it to prevent YAML thinking it's an integer (because of the 'plus' sign). If missing, `--username` will be used.
- `--signal-recipient` and `--signal-group` select the recipient (only one of them should be given). Make sure `--signal-recipient` is in international phone number format and `--signal-group` is a base 64 group ID (e.g. `--signal-group "mABCDNVoEFGz0YeZM1234Q=="`). If `--signal-recipient` is missing, `--recipient` will be used. Once registered with Signal, you can list the IDs of the groups you are in with `signal-cli -U +336123456789 listGroups`

Sample command line to run the bot with Signal :

    python3 nicobot/transbot.py -b signal -U +33612345678 -g "mABCDNVoEFGz0YeZM1234Q==" --ibmcloud-url https://api.eu-de.language-translator.watson.cloud.ibm.com/instances/a234567f-4321-abcd-efgh-1234abcd7890 --ibmcloud-apikey "f5sAznhrKQyvBFFaZbtF60m5tzLbqWhyALQawBg5TjRI"


## Development

To run unit tests :

    python -m unittest discover -v -s tests


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
