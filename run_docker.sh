docker image build -t omedev:latest  .
docker container run --interactive --tty --rm -p 5000:5000 --name ome omedev:latest