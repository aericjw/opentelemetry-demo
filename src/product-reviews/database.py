#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Python
import logging
import os
import random
import simplejson as json

# Postgres
import psycopg2

# Feature flags
from openfeature import api

logger = logging.getLogger('main')

def must_map_env(key: str):
    value = os.environ.get(key)
    if value is None:
        raise Exception(f'{key} environment variable must be set')
    return value

# Retrieve Postgres environment variables
db_connection_str = must_map_env('DB_CONNECTION_STRING')

def _flag_number(flag_name, default=0.0):
    """Evaluate a numeric feature flag, never failing the request path."""
    try:
        return api.get_client().get_float_value(flag_name, default)
    except Exception:
        return default

def _flag_bool(flag_name):
    try:
        return api.get_client().get_boolean_value(flag_name, False)
    except Exception:
        return False

# Connections deliberately opened and abandoned by the postgresConnectionLeak
# flag. Postgres caps concurrent connections at max_connections (100 by
# default), so the climbing postgresql.backends metric has a hard ceiling and
# a predictable time to saturation - a forecastable trajectory for predictive
# AI - followed by genuine "too many clients" connection failures.
_LEAKED_CONNECTIONS_CAP = 300
_leaked_connections = []

def _apply_connection_leak():
    """Honor the postgresConnectionLeak flag: with the configured per-request
    probability, open a real database connection and never close it. Turning
    the flag off releases all leaked connections so the scenario resets
    without a restart."""
    leak_probability = _flag_number("postgresConnectionLeak")
    if leak_probability <= 0:
        if _leaked_connections:
            logger.info(f"postgresConnectionLeak flag disabled: releasing {len(_leaked_connections)} leaked connections")
            while _leaked_connections:
                try:
                    _leaked_connections.pop().close()
                except Exception:
                    pass
        return
    if len(_leaked_connections) >= _LEAKED_CONNECTIONS_CAP:
        return
    if random.random() < leak_probability:
        try:
            connection = psycopg2.connect(db_connection_str, connect_timeout=5)
            _leaked_connections.append(connection)
            logger.warning(f"postgresConnectionLeak flag is enabled: abandoned connection #{len(_leaked_connections)}")
        except Exception as e:
            logger.error(f"postgresConnectionLeak: could not open connection to leak: {e}")

def get_connection():
    """Open a database connection, honoring the postgresConnectionFailure flag.

    When the flag is enabled, the given fraction of connection attempts is made
    with a stale password -- simulating a credential rotation gone wrong -- so
    Postgres itself rejects the connection with a genuine authentication error
    that also surfaces in the database server logs.
    """
    connection_str = db_connection_str
    failure_rate = _flag_number("postgresConnectionFailure")
    if failure_rate > 0 and random.random() < failure_rate:
        logger.warning("postgresConnectionFailure flag is enabled: connecting with stale credentials")
        # libpq uses the last occurrence of a repeated connection parameter
        connection_str = db_connection_str + " password=stale-rotated-credential"
    return psycopg2.connect(connection_str, connect_timeout=5)

def _apply_slow_queries(cursor):
    """Honor the postgresSlowQueries flag by burning real database-side time
    (pg_sleep) on the connection, so the slowdown is visible to database
    monitoring (pg_stat_statements, db spans), not just the client."""
    delay_seconds = _flag_number("postgresSlowQueries")
    if delay_seconds > 0:
        logger.warning(f"postgresSlowQueries flag is enabled: adding {delay_seconds}s of database latency")
        cursor.execute("SELECT pg_sleep(%s)", (delay_seconds,))

def fetch_product_reviews(product_id):
    try:
        return json.dumps(fetch_product_reviews_from_db(product_id), use_decimal=True)
    except Exception as e:
        return json.dumps({"error": str(e)})

def fetch_product_reviews_from_db(request_product_id):

    connection = None
    _apply_connection_leak()

    try:
        with get_connection() as connection:

            with connection.cursor() as cursor:
                _apply_slow_queries(cursor)

                # Define the SQL query
                query = "SELECT username, description, score FROM reviews.productreviews WHERE product_id= %s"
                if _flag_bool("postgresSchemaDrift"):
                    # The service expects the reviews schema v2, which adds a
                    # helpful_votes column. The migration was never applied, so
                    # Postgres rejects the query with an undefined-column error.
                    query = "SELECT username, description, score, helpful_votes FROM reviews.productreviews WHERE product_id= %s"

                # Execute the query
                cursor.execute(query, (request_product_id, ))

                # Fetch all the rows from the query result
                records = cursor.fetchall()
                return records

    except Exception as e:
        raise e
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception as e:
                pass

def fetch_avg_product_review_score_from_db(request_product_id):

    connection = None
    _apply_connection_leak()

    try:
        with get_connection() as connection:

            with connection.cursor() as cursor:
                _apply_slow_queries(cursor)

                # Define the SQL query
                query = "SELECT AVG(score) FROM reviews.productreviews WHERE product_id= %s"
                if _flag_bool("postgresSchemaDrift"):
                    # Schema v2 moves aggregated scores into a summary table
                    # that does not exist in this database, so Postgres
                    # rejects the query with an undefined-table error.
                    query = "SELECT avg_score FROM reviews.productreviews_summary WHERE product_id= %s"

                # Execute the query
                cursor.execute(query, (request_product_id, ))

                # Fetch all the rows from the query result
                records = cursor.fetchall()

                # Extract the average score
                if records:
                    # records will be a list like [(average_score,)]
                    average_score = records[0][0]
                else:
                    # Handle the case where no records are returned (e.g., no reviews for the product)
                    average_score = None

                # return the score as a string rounded to 1 decimal place
                return f"{average_score:.1f}"

    except Exception as e:
        raise e
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception as e:
                pass
