# ================================== PYTHON BASE ===================================

FROM node:17-buster-slim AS node
FROM python:3.9-slim-buster AS poetry_base

WORKDIR /app

RUN useradd -m sid
RUN chown -R sid:sid /app
USER sid

COPY --chown=sid:sid chicagodir chicagodir
COPY --chown=sid:sid webpack.config.js autoapp.py ./

# python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME="/opt/poetry"

ENV PATH="$POETRY_HOME/bin:/home/sid/.local/bin/:$PATH"

COPY ["poetry.lock", "pyproject.toml", "./"]
RUN pip install poetry
RUN poetry install --no-dev

# ================================== BUILDER ===================================
FROM poetry_base as builder

USER sid

COPY --from=node /usr/local/bin/ /usr/local/bin/
COPY --from=node /usr/lib/ /usr/lib/
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

COPY package.json ./
RUN npm install

COPY --chown=sid:sid assets assets
#COPY .env.example .env
ENV FLASK_APP autoapp.py
RUN poetry run npm run-script build

# ================================== PRODUCTION ===================================

FROM poetry_base AS production
# copy the results of the build
COPY --from=builder /app/chicagodir/static /app/chicagodir/static

USER root
RUN apt-get update && apt-get install  -y imagemagick optipng curl
USER sid

COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY supervisord_programs /etc/supervisor/conf.d
COPY Procfile Procfile
COPY migrations migrations

RUN mkdir -p chicagodir/streets/data
RUN curl "https://chicitydir.us-east-1.linodeobjects.com/GIS/comm_areas.tgz" | \
    tar xvz -C chicagodir/streets/data

EXPOSE 5000
ENTRYPOINT ["/usr/bin/env", "poetry", "run"]
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
