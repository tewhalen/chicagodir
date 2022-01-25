# ================================== BUILDER ===================================
ARG INSTALL_PYTHON_VERSION=3.9
ARG INSTALL_NODE_VERSION=16

FROM node:16-buster-slim AS node
FROM python:${INSTALL_PYTHON_VERSION}-slim-buster AS builder

WORKDIR /app

COPY --from=node /usr/local/bin/ /usr/local/bin/
COPY --from=node /usr/lib/ /usr/lib/
# See https://github.com/moby/moby/issues/37965
RUN true
#RUN apt-get update && apt-get install  -y gcc g++ git

COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY ["Pipfile", "Pipfile.lock", "shell_scripts/auto_pipenv.sh", "./"]
RUN python -m pip install --upgrade pip
RUN pip install --no-cache pipenv
RUN bash -c 'PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy'

COPY package.json ./
RUN npm install

COPY webpack.config.js autoapp.py ./
COPY chicagodir chicagodir
COPY assets assets
COPY .env.example .env
RUN npm run-script build

# ================================= PRODUCTION =================================
FROM python:${INSTALL_PYTHON_VERSION}-slim-buster as production

WORKDIR /app

RUN useradd -m sid
RUN chown -R sid:sid /app
USER sid
ENV PATH="/home/sid/.local/bin:${PATH}"

COPY --from=builder --chown=sid:sid /app/chicagodir/static /app/chicagodir/static
COPY --from=builder --chown=sid:sid  /app/.venv /app/.venv
COPY ["Pipfile", "Pipfile.lock", "shell_scripts/auto_pipenv.sh", "./"]
RUN pip install --no-cache pipenv
RUN pipenv install --deploy

COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY supervisord_programs /etc/supervisor/conf.d

COPY . .

EXPOSE 5000
ENTRYPOINT ["/bin/bash", "shell_scripts/supervisord_entrypoint.sh"]
CMD ["-c", "/etc/supervisor/supervisord.conf"]


# ================================= DEVELOPMENT ================================
FROM builder AS development
RUN rm -rf .venv
RUN pipenv install --dev
EXPOSE 2992
EXPOSE 5000
CMD [ "pipenv", "run", "npm", "start" ]
