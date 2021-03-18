ARG NICOBOT_DEPLOY_BASE_IMAGE=nicolabs/nicobot:latest

FROM ${NICOBOT_DEPLOY_BASE_IMAGE}

# Overrides default configuration files with custom ones : i18n.*.yml, keywords.yml
# Loads referentials to prevent the image to download them everytime it starts : languages.*.json, likelySubtags.json
COPY i18n.*.yml \
     *.keywords.yml \
     languages.*.json \
     likelySubtags.json \
     /etc/nicobot/
