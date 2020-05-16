
sudo apt install python3 python3-pip
git clone https://github.com/nicolabs/nicobot.git
cd nicobot
pip3 install -r requirements.txt

apk install py3-pip ...
apk install git => in a build stage only

# see also distroless :
# - github.com/GoogleContainerTools/distroless/blob/master/exampes/java/Dockerfile : uses openjdk:11-jdk-slim
#   Compare with openjdk:<version>-alpine ; in fact openjdk:jre ?
# - github.com/GoogleContainerTools/distroless/blob/master/exampes/python3/Dockerfile : uses python:3-slim

# Make the following a stage in a multi-stage dockerfile (only kee the extracted files and ln)

# Signal requirement
sudo apt install default-jre
# Make sure java >= 7
# Signal installation
export VERSION=0.6.7
wget https://github.com/AsamK/signal-cli/releases/download/v"${VERSION}"/signal-cli-"${VERSION}".tar.gz
sudo tar xf signal-cli-"${VERSION}".tar.gz -C /opt
sudo ln -sf /opt/signal-cli-"${VERSION}"/bin/signal-cli /usr/local/bin/
# Check
which signal-cli
# Configuration
# Do it locally then copy the files ?
signal-cli link --name MyComputer
