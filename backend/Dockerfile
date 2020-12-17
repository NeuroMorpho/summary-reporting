# our base image
FROM ubuntu

# Install python and pip
MAINTAINER Navy Merianda "navymerianda@gmail.com"

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev libopenblas-base libomp-dev


# install Python modules needed by the Python app
COPY requirements.txt /app/

WORKDIR /app

RUN pip3 install --no-cache-dir -r /app/requirements.txt

# copy files required for the app to run
COPY flask_reporting.py /app/
COPY config.py /app/
COPY logger.py /app/
COPY classNeuron.py /app/
COPY groupsCol.xml /app/
COPY flaskreporting.log /app/
COPY reports /app/reports/

ENTRYPOINT [ "flask" ]

ENV FLASK_APP=flask_reporting.py
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8


# tell the port number the container should expose
EXPOSE 5000

# run the application
CMD ["run", "--host", "0.0.0.0"]
