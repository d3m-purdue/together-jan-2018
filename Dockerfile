FROM r-base:3.4.1

# for web
EXPOSE 80

# for connection with TA2
EXPOSE 45042


RUN apt-get update
RUN apt-get install -y git curl sudo python2.7 python2.7-dev python-pip libcairo2-dev  gnupg1 
# (gnupg1 not supported on python:2 base, but needed on r-base)

# add the 'ps' command back
RUN apt-get -y install procps

# needed for yarn installation
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils


# nvm environment variables
ENV NVM_DIR /usr/local/nvm
ENV NODE_VERSION 9.5.0

# install nvm  (Node version manager - )
# https://github.com/creationix/nvm#install-script
RUN curl --silent -o- https://raw.githubusercontent.com/creationix/nvm/v0.31.2/install.sh | bash

# install node and npm
RUN . "$NVM_DIR/nvm.sh" \
	&& nvm install $NODE_VERSION \
	&& nvm alias default $NODE_VERSION \
	&& nvm use default

# add node and npm to path so the commands are available
ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

RUN echo 'node version:'
RUN node --version

RUN mkdir /d3m-ta3
COPY . /d3m-ta3

WORKDIR /d3m-ta3

#RUN apt-get install -y npm
#RUN npm install -g npm 

# install for stop command in base interpreter
RUN pip install psutil

RUN pip install virtualenv
RUN npm install
RUN npm run pythonprep
RUN npm run protobuf
RUN npm run build

# make a directory to copy TA2 results to for reading & analysis. This
# has to be after the run build, so the build directory exists

RUN if [ ! -d "/d3m-ta3/build/pipelines" ]; then mkdir /d3m-ta3/build/pipelines; fi

#RUN useradd tangelo

WORKDIR /d3m-ta3/user_interface

# build the new interface

#install the yarn package manager
RUN echo 'installing yarn'
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
RUN sudo apt-get update && sudo apt-get install -y yarn
RUN yarn install
RUN yarn build


# now copy the resulting files from the yarn build into the main build directory
# after renaming the index.html 
RUN mv /d3m-ta3/build/index.html /d3m-ta3/build/index_orig.html
# merge node packages in with the first compile... 
RUN cp -r /d3m-ta3/user_interface/node_modules/* /d3m-ta3/node_modules
RUN cp -r /d3m-ta3/user_interface/build/static /d3m-ta3/build/static
RUN cp -r /d3m-ta3/user_interface/public /d3m-ta3/public
RUN cp -r /d3m-ta3/user_interface/build/*json /d3m-ta3/build/
RUN cp -r /d3m-ta3/user_interface/build/index.html /d3m-ta3/build/
RUN cp -r /d3m-ta3/user_interface/build/*js /d3m-ta3/build/

WORKDIR /d3m-ta3
ENTRYPOINT npm run serve

# from NIST - ta3_search for non-interactive shells
RUN echo '#!/bin/bash' > /usr/bin/ta3_search 
RUN echo 'cd /d3m-ta3' >> /usr/bin/ta3_search
RUN echo '/usr/local/bin/npm run serve'  >> /usr/bin/ta3_search
RUN chmod +x /usr/bin/ta3_search

# quit command
RUN echo '#!/usr/bin/python /d3m-ta3/build/ta3_quit.py'  > /usr/bin/ta3_quit
RUN chmod +x /usr/bin/ta3_quit

