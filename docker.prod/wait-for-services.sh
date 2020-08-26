#!/usr/bin/env bash
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

# Verify that all services are running before continuing
check_ready() {
    RETRIES=5
    while ! $2
    do
        echo "Waiting for $1, $((RETRIES--)) remaining attempts..."
        sleep 2
        if [ $RETRIES -eq 0 ]
        then
            echo "Couldn't reach $1"
            exit 1
        fi
    done
}
_db_check(){ docker-compose exec --user postgres db bash -c "pg_isready" &>/dev/null; }
check_ready "postgres" _db_check

_es_check(){ [[ $(curl -sL -w "%{http_code}\\n" "http://localhost:9200/" -o /dev/null)==200 ]]; }
check_ready "Elasticsearch" _es_check

_redis_check(){ [[ $(docker-compose exec cache sh -c "redis-cli ping")=="PONG" ]]; }
check_ready "redis" _redis_check

_rabbit_check(){ docker-compose exec mq bash -c "rabbitmqctl status" &>/dev/null; }
check_ready "RabbitMQ" _rabbit_check
