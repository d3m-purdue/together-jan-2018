# d3m-ta3-modeling
A prototype TA3 application enabling a hypothetical modeling task. This repository includes the new React-based interface! 

## Docker Build instructions

1. Add the new interface as a git submodule:   git submodule add https://github.com/d3m-purdue/modsquad2.git user_interface

2. build using docker:  docker build -t together .

(this builds the orignal interface, builds the new interface, and copies the new interface over into the /buid directory, so it has access to the tangelo service calls. )

## for native build

1. Make sure `virtualenv`, `R`, and `npm` are installed on your system.

2. Install the Node dependencies: `npm i`.

3. Prepare the Python environment: `npm run pythonprep`.

4. Prepare the R environment: `npm run rprep`.

5. Generate the datasets: `npm run data`.

6. Build the application: `npm run build`.

7. Serve the application: `JSON_CONFIG_PATH=/path/to/NIST/config/file npm run
   serve`.

8. go into the user_interface submodule directory and type yarn install; yarn start

9. Run the application: http://localhost:3000

(The original interface and the new interface are both running.  They both share the same tangelo AJAX calls, This is not recommended in the long-term, but unifying the package management systems (npm and yarn) is unnecessary at this point since the docker container builds successfully. 
