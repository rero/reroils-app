# -*- coding: utf-8 -*-
#
# RERO ILS
# Copyright (C) 2019 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

FROM python:3.6-slim-buster

# Displayed infos on frontpage
ARG GIT_HASH
ARG GIT_UI_HASH
ARG UI_TGZ=""
ENV INVENIO_RERO_ILS_APP_GIT_HASH ${GIT_HASH:-''}
ENV INVENIO_RERO_ILS_UI_GIT_HASH ${GIT_UI_HASH:-''}

# Install Invenio
ENV WORKING_DIR=/invenio
ENV INVENIO_ENV=production
ENV INVENIO_INSTANCE_PATH=${WORKING_DIR}/var/instance
ENV INVENIO_STATIC_FOLDER=${INVENIO_INSTANCE_PATH}/static
ENV INVENIO_COLLECT_STORAGE='flask_collect.storage.file'
# use static_folder as mkdir shortcut to create all directories
RUN mkdir -p ${INVENIO_STATIC_FOLDER}

# create user
RUN useradd invenio --uid 1000  --home ${WORKING_DIR}

# copy uwsgi config files
COPY --chown=invenio:invenio ./docker.prod/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY --chown=invenio:invenio ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}

# copy everything inside /src
RUN mkdir -p ${WORKING_DIR}/src
COPY --chown=invenio:invenio . ${WORKING_DIR}/src
WORKDIR ${WORKING_DIR}/src

# for some files to be written (example: egg-info)
RUN chown -R invenio:invenio ${WORKING_DIR} \
  && chmod -R go+w ${WORKING_DIR}

# require debian packages
# Set locales to C.UTF-8 to avoid some problem:
# Cf. https://click.palletsprojects.com/en/5.x/python3/#python-3-surrogate-handling
# Delete all forbidden directories/files in node_modules directory
# except some due to https://github.com/rero/rero-ils/issues/713
RUN set -ex \
  ; buildDeps=' \
    curl \
    gcc \
    libc6-dev \
  ' \
  ; apt-get update \
  ; apt-get upgrade -y \
  ; apt-get install --no-install-recommends -y \
    git \
    gnupg \
    $buildDeps \
  ; pip install --no-cache --upgrade setuptools wheel pip poetry \
  ; curl -sL https://deb.nodesource.com/setup_10.x | bash - \
  ; apt-get install --no-install-recommends -y nodejs \
  ; su -w INVENIO_STATIC_FOLDER,INVENIO_COLLECT_STORAGE,UI_TGZ,INVENIO_ENV \
    -c "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; \
    cd ${WORKING_DIR}/src && \
    $(which bash) poetry run bootstrap --deploy ${UI_TGZ} \
    && npm cache clean -f" - invenio \
  ; find "${INVENIO_STATIC_FOLDER}/node_modules" -maxdepth 1 -type d \
      -not -name bootstrap-sass \
      -not -name bootstrap \
      -not -name font-awesome \
      -not -name @rero \
      -not -wholename "${INVENIO_STATIC_FOLDER}/node_modules" \
      -exec rm -rf "{}" \; \
  ; rm -rf "${INVENIO_STATIC_FOLDER}/scss" \
  ; rm -rf "${INVENIO_STATIC_FOLDER}/templates" \
  ; rm -rf "${INVENIO_STATIC_FOLDER}/package-lock.json" \
  ; rm -rf "${INVENIO_STATIC_FOLDER}/package.json" \
  ; rm -rf "${INVENIO_STATIC_FOLDER}/Pipfile" \
  ; apt-get purge -y --autoremove $buildDeps \
  ; rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
  ; rm -rf ${WORKING_DIR}/.cache

USER 1000
