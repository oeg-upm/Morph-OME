docker image build -t omedev:latest  .
docker container run --interactive --env TADA_HOST=$TADA_HOST --tty --rm -p 5000:5000 --name ome omedev:latest
