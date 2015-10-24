The latest code can be tested using a docker and docker-compose. The compose file requires a 
dashboard container to be available. This container can be created by checking out the 
dashboard source code and running the following command in the demo subdir:

docker build -t impera-dashboard .

Then 'docker-compose up' takes care of everything else.
