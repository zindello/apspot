FROM python:3.10
ADD requirements.txt /usr/local/apspot/
ADD apspot.py /usr/local/apspot/
RUN pip3 install -r /usr/local/apspot/requirements.txt
ENTRYPOINT python3 /usr/local/apspot/apspot.py