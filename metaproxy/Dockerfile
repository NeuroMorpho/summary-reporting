# our base image
FROM ubuntu:18.04

# Install python and pip
LABEL author="Bengt Ljungquist"

RUN apt-get update -y && \
     apt-get install -y python3-pip python3-dev


# install Python modules needed by the Python app
COPY requirements.txt /app/

WORKDIR /app

RUN pip3 install --no-cache-dir -r /app/requirements.txt

# copy files required for the app to run
COPY app.py /app/

ENTRYPOINT [ "flask" ]

ENV FLASK_APP=app.py
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8


# tell the port number the container should expose
EXPOSE 5000

# run the application
CMD ["run", "--host", "0.0.0.0"]
