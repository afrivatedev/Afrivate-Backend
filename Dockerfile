# this tells docker what version of python to use in our build
#  this also tells docker what version of the linux operating system to use
#the name or website of the person intending to manage this project
FROM python:3.13-alpine3.22
LABEL maintainer="Martins John" 

#this tells the docker to not allow any delay in output
ENV PYTHONUNBUFFERED=1


#this copies the requirement text and some other files into our container
#also it choses the port to expose
COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
COPY ./app /app
WORKDIR /app
EXPOSE 8000



ARG DEV=false

# zlib, jpeg are dependency for pillow
# and the rest are for Psycopg2
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client jpeg-dev && \
    apk add --update --no-cache --virtual .tmp-build-deps \
        build-base postgresql-dev musl-dev zlib zlib-dev linux-headers && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ "$DEV" = "true" ]; \
        then /py/bin/pip install -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp && \
    apk del .tmp-build-deps && \
    adduser \
     --disabled-password\
     --no-create-home\
      django-user &&\
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    chown -R django-user:django-user /vol && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts
#this block helps us define our path to our user defined variables, executables
ENV PATH="/scripts:/py/bin:$PATH"

#this tells the docker container the user to switch to. all of the commands 
#ran prior to this are actually run using the root user privilege.
USER django-user

CMD ["run.sh"]