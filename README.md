# purdue-ta3-main

A prototype TA3 application enabling a hypothetical modeling task. This repository includes the new React-based interface! 

## Docker Build instructions

1. Note that the new interface as installed as a git submodule: `git submodule
add https://github.com/d3m-purdue/modsquad2.git user_interface`. A checkout
should automatically install the interface without hand installation.

2. Build using docker: `docker build -t together .` This builds the orignal
interface, builds the new interface, and copies the new interface over into the
`/build` directory, so it has access to the tangelo service calls.
http://localhost:8080 will show the new interface.

3. Unpack an evaluation problem statement directory into `eval` in the current
   directory.

4. Create an output directory:
   ```
   mkdir writable
   mkdir writable/temp
   mkdir writable/execs
   mkdir writable/logs
   ```

5. Log into the D3M docker registry: `docker login
register.datadrivendiscovery.org`

6. Run a TA2 container: `CONFIG_JSON_PATH=/eval/config.json docker run -p
45042:45042 -e CONFIG_JSON_PATH -v $PWD/eval:/eval -v $PWD/writable:/writable
-it --rm --entrypoint /bin/bash
registry.datadrivendiscovery.org/mit-featurelabs/btb-dockerimage:stable -c
ta2_grpc_server`

7. Run the TA3 container: `JSON_CONFIG_PATH=/eval/config.json
TA2_SERVER_CONN=172.17.0.2:45042 docker run -e JSON_CONFIG_PATH -e
TA2_SERVER_CONN -p 8080:8080 -v $PWD/eval:/eval -v $PWD/writable:/writable --rm
-t together`

8. Go to http://localhost:8080.

## for native build

1. Make sure `virtualenv`, `R`, and `npm` are installed on your system.

2. Install the Node dependencies: `npm i`.

3. Prepare the Python environment: `npm run pythonprep`.

4. Prepare the R environment: `npm run rprep`.

5. Generate the datasets: `npm run data`.

6. Build the application: `npm run build`.

7. Serve the application: `JSON_CONFIG_PATH=/path/to/NIST/config/file npm run
   serve`.

8. Go into the user_interface submodule directory and build the new interface:
`yarn install; yarn start`

9. View the application: http://localhost:3000. The original interface and the
new interface are both running. They both share the same tangelo AJAX calls,
This is not recommended in the long-term, but unifying the package management
systems (npm and yarn) is unnecessary at this point since the docker container
builds successfully.
