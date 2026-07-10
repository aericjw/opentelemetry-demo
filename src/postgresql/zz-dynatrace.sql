-- Copyright The OpenTelemetry Authors
-- SPDX-License-Identifier: Apache-2.0

-- Dynatrace PostgreSQL remote monitoring setup.
--
-- This file is intentionally named to sort AFTER init.sql so that the
-- application database and its objects already exist when the per-database
-- objects below are created. The deployed chart uses a single application
-- database ("otel"), so all per-database setup targets that database.
--
-- The monitoring user's password is read from the DYNATRACE_PASSWORD environment
-- variable (injected from a Kubernetes Secret) via psql backtick substitution, so
-- the plaintext password never appears in the postgresql-init ConfigMap.
\set dt_password `printf '%s' "$DYNATRACE_PASSWORD"`

-- ---------------------------------------------------------------------------
-- Cluster-wide objects (roles are global; run once from any database)
-- ---------------------------------------------------------------------------
CREATE USER dynatrace WITH PASSWORD :'dt_password' INHERIT;

-- Read-only monitoring access across all databases and schemas.
GRANT pg_monitor TO dynatrace;

-- Resolve the dynatrace schema (and the execution-plan helper) without a
-- schema-qualified name.
ALTER USER dynatrace SET search_path TO dynatrace, public;

-- ---------------------------------------------------------------------------
-- Per-database objects for the "otel" application database
-- ---------------------------------------------------------------------------
\connect otel

CREATE SCHEMA IF NOT EXISTS dynatrace;
GRANT USAGE ON SCHEMA dynatrace TO dynatrace;

CREATE OR REPLACE FUNCTION dynatrace.dynatrace_execution_plan(
   query text,
   OUT explain JSON
) RETURNS SETOF JSON
   LANGUAGE plpgsql
   VOLATILE
   RETURNS NULL ON NULL INPUT
   SECURITY DEFINER
   ROWS 1
   SET plan_cache_mode = force_generic_plan
AS
$$DECLARE
   arg_count integer;
   open_paren text;
   close_paren text;
   explain_cmd text;
   json_result json;
BEGIN

   /* reject statements containing a semicolon in the middle */
   IF pg_catalog.strpos(
         pg_catalog.rtrim(dynatrace_execution_plan.query, ';'),
         ';'
      ) OPERATOR(pg_catalog.>) 0 THEN
      RAISE EXCEPTION 'query string must not contain a semicolon';
   END IF;

   /* get the parameter count */
   SELECT count(*) INTO arg_count
   FROM pg_catalog.regexp_matches( /* extract the "$n" */
         pg_catalog.regexp_replace( /* remove single quoted strings */
            dynatrace_execution_plan.query,
            '''[^'']*''',
            '',
            'g'
         ),
         '\$\d{1,}',
         'g'
      );

   IF arg_count OPERATOR(pg_catalog.=) 0 THEN
      open_paren := '';
      close_paren := '';
   ELSE
      open_paren := '(';
      close_paren := ')';
   END IF;

   /* construct a prepared statement */
   EXECUTE
      pg_catalog.concat(
         'PREPARE _stmt_',
         open_paren,
         pg_catalog.rtrim(
            pg_catalog.repeat('unknown,', arg_count),
            ','
         ),
         close_paren,
         ' AS ',
         dynatrace_execution_plan.query
      );

   /* construct an EXPLAIN statement */
   explain_cmd :=
      pg_catalog.concat(
         'EXPLAIN (FORMAT JSON, ANALYZE FALSE) EXECUTE _stmt_',
         open_paren,
         pg_catalog.rtrim(
            pg_catalog.repeat('NULL,', arg_count),
            ','
         ),
         close_paren
      );

   /* get and return the plan */
   EXECUTE explain_cmd INTO json_result;
   RETURN QUERY SELECT json_result;

   /* delete the prepared statement */
   DEALLOCATE _stmt_;
END;$$;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements SCHEMA public;

-- ---------------------------------------------------------------------------
-- Per-database objects for the "postgres" maintenance database
-- (Dynatrace connects here for cluster-wide discovery, so it needs the same
-- schema, helper function, and extension.)
-- ---------------------------------------------------------------------------
\connect postgres

CREATE SCHEMA IF NOT EXISTS dynatrace;
GRANT USAGE ON SCHEMA dynatrace TO dynatrace;

CREATE OR REPLACE FUNCTION dynatrace.dynatrace_execution_plan(
   query text,
   OUT explain JSON
) RETURNS SETOF JSON
   LANGUAGE plpgsql
   VOLATILE
   RETURNS NULL ON NULL INPUT
   SECURITY DEFINER
   ROWS 1
   SET plan_cache_mode = force_generic_plan
AS
$$DECLARE
   arg_count integer;
   open_paren text;
   close_paren text;
   explain_cmd text;
   json_result json;
BEGIN

   /* reject statements containing a semicolon in the middle */
   IF pg_catalog.strpos(
         pg_catalog.rtrim(dynatrace_execution_plan.query, ';'),
         ';'
      ) OPERATOR(pg_catalog.>) 0 THEN
      RAISE EXCEPTION 'query string must not contain a semicolon';
   END IF;

   /* get the parameter count */
   SELECT count(*) INTO arg_count
   FROM pg_catalog.regexp_matches( /* extract the "$n" */
         pg_catalog.regexp_replace( /* remove single quoted strings */
            dynatrace_execution_plan.query,
            '''[^'']*''',
            '',
            'g'
         ),
         '\$\d{1,}',
         'g'
      );

   IF arg_count OPERATOR(pg_catalog.=) 0 THEN
      open_paren := '';
      close_paren := '';
   ELSE
      open_paren := '(';
      close_paren := ')';
   END IF;

   /* construct a prepared statement */
   EXECUTE
      pg_catalog.concat(
         'PREPARE _stmt_',
         open_paren,
         pg_catalog.rtrim(
            pg_catalog.repeat('unknown,', arg_count),
            ','
         ),
         close_paren,
         ' AS ',
         dynatrace_execution_plan.query
      );

   /* construct an EXPLAIN statement */
   explain_cmd :=
      pg_catalog.concat(
         'EXPLAIN (FORMAT JSON, ANALYZE FALSE) EXECUTE _stmt_',
         open_paren,
         pg_catalog.rtrim(
            pg_catalog.repeat('NULL,', arg_count),
            ','
         ),
         close_paren
      );

   /* get and return the plan */
   EXECUTE explain_cmd INTO json_result;
   RETURN QUERY SELECT json_result;

   /* delete the prepared statement */
   DEALLOCATE _stmt_;
END;$$;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements SCHEMA public;
