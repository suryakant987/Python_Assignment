-- Run once in pgAdmin Query Tool while connected as postgres
-- to the maintenance database named "postgres".
--
-- If a statement fails because the object already exists, continue with the rest.

CREATE USER asset_registry WITH PASSWORD 'assetreg123';

CREATE DATABASE asset_registry OWNER asset_registry;

CREATE DATABASE asset_registry_test OWNER asset_registry;

GRANT ALL PRIVILEGES ON DATABASE asset_registry TO asset_registry;
GRANT ALL PRIVILEGES ON DATABASE asset_registry_test TO asset_registry;
