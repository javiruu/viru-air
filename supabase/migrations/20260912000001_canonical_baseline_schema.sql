-- Canonical Baseline Schema for Supabase PostgreSQL
-- Generated from SQLAlchemy metadata (Base.metadata)
-- Tables: 62

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE airport (
	id VARCHAR(36) NOT NULL, 
	iata VARCHAR(3) NOT NULL, 
	icao VARCHAR(4), 
	name VARCHAR(200) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	country VARCHAR(100) NOT NULL, 
	region VARCHAR(50), 
	latitude NUMERIC(10, 6) NOT NULL, 
	longitude NUMERIC(10, 6) NOT NULL, 
	timezone VARCHAR(64), 
	airport_type VARCHAR(50), 
	is_primary BOOLEAN NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_airport_icao ON airport (icao);
CREATE UNIQUE INDEX ix_airport_iata ON airport (iata);

CREATE TABLE calendar_price_observation (
	id VARCHAR(36) NOT NULL, 
	query_fingerprint VARCHAR(64) NOT NULL, 
	reference_fingerprint VARCHAR(64) NOT NULL, 
	route_signature VARCHAR(255) NOT NULL, 
	travel_date DATE NOT NULL, 
	leg VARCHAR(16) NOT NULL, 
	adults INTEGER NOT NULL, 
	cabin VARCHAR(32) NOT NULL, 
	aggregation_mode VARCHAR(16) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	provider VARCHAR(80) NOT NULL, 
	raw_price_amount NUMERIC(10, 2), 
	raw_currency VARCHAR(3), 
	normalized_price_amount NUMERIC(10, 2) NOT NULL, 
	observed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	freshness_status VARCHAR(32) NOT NULL, 
	coverage_status VARCHAR(32) NOT NULL, 
	validation_status VARCHAR(32) NOT NULL, 
	source_kind VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_calendar_price_observation_sample UNIQUE (query_fingerprint, route_signature, provider, observed_at)
);

CREATE INDEX ix_calendar_price_observation_day ON calendar_price_observation (query_fingerprint, travel_date, observed_at);
CREATE INDEX ix_calendar_price_observation_reference ON calendar_price_observation (reference_fingerprint, observed_at);
CREATE INDEX ix_calendar_price_observation_expires ON calendar_price_observation (expires_at);

CREATE TABLE community_trending_snapshot (
	id VARCHAR(36) NOT NULL, 
	reporting_date DATE NOT NULL, 
	window_start_date DATE NOT NULL, 
	window_end_date DATE NOT NULL, 
	calculated_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	published_at_utc TIMESTAMP WITHOUT TIME ZONE, 
	expires_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	route_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_community_trending_snapshot_status CHECK (status IN ('building', 'published')), 
	CONSTRAINT ck_community_trending_snapshot_route_count CHECK (route_count >= 0)
);

CREATE INDEX ix_community_trending_snapshot_status_expires ON community_trending_snapshot (status, expires_at_utc);
CREATE INDEX ix_community_trending_snapshot_reporting_date ON community_trending_snapshot (reporting_date);
CREATE INDEX ix_community_trending_snapshot_status_calculated ON community_trending_snapshot (status, calculated_at_utc);

CREATE TABLE flight_offer_cache_entry (
	id VARCHAR(36) NOT NULL, 
	offer_fingerprint VARCHAR(64) NOT NULL, 
	flight_instance_fingerprint VARCHAR(64), 
	provider VARCHAR(40) NOT NULL, 
	carrier VARCHAR(16), 
	carrier_code VARCHAR(16), 
	flight_number VARCHAR(32), 
	origin_airport VARCHAR(3) NOT NULL, 
	destination_airport VARCHAR(3) NOT NULL, 
	departure_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	arrival_at TIMESTAMP WITHOUT TIME ZONE, 
	departure_time_local VARCHAR(16), 
	arrival_time_local VARCHAR(16), 
	duration_minutes INTEGER, 
	stops_count INTEGER NOT NULL, 
	booking_url_hash VARCHAR(128), 
	deeplink_signature VARCHAR(128), 
	source_kind VARCHAR(24) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_flight_offer_cache_fingerprint UNIQUE (offer_fingerprint)
);

CREATE INDEX ix_flight_offer_cache_route ON flight_offer_cache_entry (origin_airport, destination_airport, departure_at);
CREATE INDEX ix_flight_offer_cache_entry_departure_at ON flight_offer_cache_entry (departure_at);
CREATE INDEX ix_flight_offer_cache_provider ON flight_offer_cache_entry (provider, departure_at);
CREATE INDEX ix_flight_offer_cache_instance ON flight_offer_cache_entry (flight_instance_fingerprint);
CREATE INDEX ix_flight_offer_cache_entry_provider ON flight_offer_cache_entry (provider);

CREATE TABLE flight_operational_refresh_lock (
	flight_instance_fingerprint VARCHAR(64) NOT NULL, 
	lock_token VARCHAR(64) NOT NULL, 
	acquired_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	outcome VARCHAR(24), 
	PRIMARY KEY (flight_instance_fingerprint)
);

CREATE UNIQUE INDEX ix_flight_operational_refresh_lock_token ON flight_operational_refresh_lock (lock_token);
CREATE INDEX ix_flight_operational_refresh_lock_expires ON flight_operational_refresh_lock (expires_at);

CREATE TABLE flight_operational_snapshot (
	id VARCHAR(36) NOT NULL, 
	flight_instance_fingerprint VARCHAR(64) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	provider_flight_id VARCHAR(80), 
	flight_number VARCHAR(32), 
	callsign VARCHAR(32), 
	icao24 VARCHAR(16), 
	status VARCHAR(24) NOT NULL, 
	status_raw VARCHAR(64), 
	observed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	scheduled_departure_at TIMESTAMP WITHOUT TIME ZONE, 
	estimated_departure_at TIMESTAMP WITHOUT TIME ZONE, 
	actual_departure_at TIMESTAMP WITHOUT TIME ZONE, 
	scheduled_arrival_at TIMESTAMP WITHOUT TIME ZONE, 
	estimated_arrival_at TIMESTAMP WITHOUT TIME ZONE, 
	actual_arrival_at TIMESTAMP WITHOUT TIME ZONE, 
	departure_terminal VARCHAR(32), 
	departure_gate VARCHAR(32), 
	arrival_terminal VARCHAR(32), 
	arrival_gate VARCHAR(32), 
	departure_delay_minutes INTEGER, 
	arrival_delay_minutes INTEGER, 
	latitude NUMERIC(9, 6), 
	longitude NUMERIC(9, 6), 
	altitude_m NUMERIC(10, 2), 
	speed_mps NUMERIC(10, 2), 
	heading_deg NUMERIC(6, 2), 
	on_ground BOOLEAN, 
	registration VARCHAR(32), 
	aircraft_iata VARCHAR(16), 
	aircraft_icao VARCHAR(16), 
	data_quality VARCHAR(24) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_flight_operational_snapshot_observation UNIQUE (flight_instance_fingerprint, provider, observed_at)
);

CREATE INDEX ix_flight_operational_snapshot_observed_at ON flight_operational_snapshot (observed_at);
CREATE INDEX ix_flight_operational_snapshot_expires ON flight_operational_snapshot (expires_at);
CREATE INDEX ix_flight_operational_snapshot_instance_observed ON flight_operational_snapshot (flight_instance_fingerprint, observed_at);
CREATE INDEX ix_flight_operational_snapshot_provider_flight ON flight_operational_snapshot (provider, provider_flight_id);

CREATE TABLE flight_provider_quota (
	provider VARCHAR(40) NOT NULL, 
	window_key VARCHAR(10) NOT NULL, 
	units_used INTEGER NOT NULL, 
	blocked_until TIMESTAMP WITHOUT TIME ZONE, 
	block_reason VARCHAR(32), 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (provider)
);

CREATE INDEX ix_flight_provider_quota_blocked_until ON flight_provider_quota (blocked_until);

CREATE TABLE hotel_daily_metric (
	id VARCHAR(36) NOT NULL, 
	metric_date DATE NOT NULL, 
	metric_name VARCHAR(32) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	outcome VARCHAR(24) NOT NULL, 
	count INTEGER NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_daily_metric_key UNIQUE (metric_date, metric_name, provider, outcome)
);

CREATE INDEX ix_hotel_daily_metric_date ON hotel_daily_metric (metric_date);
CREATE INDEX ix_hotel_daily_metric_name_date ON hotel_daily_metric (metric_name, metric_date);

CREATE TABLE hotel_property (
	id VARCHAR(36) NOT NULL, 
	canonical_name VARCHAR(200) NOT NULL, 
	normalized_name VARCHAR(200) NOT NULL, 
	address VARCHAR(255), 
	city VARCHAR(100) NOT NULL, 
	normalized_city VARCHAR(100) NOT NULL, 
	country_code VARCHAR(2) NOT NULL, 
	latitude NUMERIC(10, 6), 
	longitude NUMERIC(10, 6), 
	stars INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_hotel_property_city ON hotel_property (city);
CREATE INDEX ix_hotel_property_normalized_city ON hotel_property (normalized_city);
CREATE INDEX ix_hotel_property_normalized_name ON hotel_property (normalized_name);
CREATE INDEX ix_hotel_property_country_code ON hotel_property (country_code);

CREATE TABLE hotel_provider_budget (
	id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	operation VARCHAR(40) NOT NULL, 
	window_key VARCHAR(20) NOT NULL, 
	hard_limit INTEGER NOT NULL, 
	units_reserved INTEGER NOT NULL, 
	units_used INTEGER NOT NULL, 
	units_released INTEGER NOT NULL, 
	window_expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	source VARCHAR(24) NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_provider_budget_window UNIQUE (provider, operation, window_key)
);

CREATE INDEX ix_hotel_provider_budget_window_expires_at ON hotel_provider_budget (window_expires_at);
CREATE INDEX ix_hotel_provider_budget_operation ON hotel_provider_budget (operation);
CREATE INDEX ix_hotel_provider_budget_provider ON hotel_provider_budget (provider);
CREATE INDEX ix_hotel_provider_budget_provider_operation ON hotel_provider_budget (provider, operation);

CREATE TABLE hotel_provider_circuit (
	id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	operation VARCHAR(40) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	failure_threshold INTEGER NOT NULL, 
	cooldown_seconds INTEGER NOT NULL, 
	consecutive_failures INTEGER NOT NULL, 
	state_version INTEGER NOT NULL, 
	opened_at TIMESTAMP WITHOUT TIME ZONE, 
	next_probe_at TIMESTAMP WITHOUT TIME ZONE, 
	probe_token VARCHAR(64), 
	probe_expires_at TIMESTAMP WITHOUT TIME ZONE, 
	last_error_code VARCHAR(64), 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_provider_circuit_provider_operation UNIQUE (provider, operation)
);

CREATE INDEX ix_hotel_provider_circuit_status_probe ON hotel_provider_circuit (status, next_probe_at);
CREATE INDEX ix_hotel_provider_circuit_next_probe_at ON hotel_provider_circuit (next_probe_at);
CREATE INDEX ix_hotel_provider_circuit_provider ON hotel_provider_circuit (provider);

CREATE TABLE hotel_provider_run (
	id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	correlation_id VARCHAR(64), 
	client_event_id VARCHAR(64), 
	execution_id VARCHAR(64), 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	status VARCHAR(20) NOT NULL, 
	items_processed INTEGER NOT NULL, 
	error_message VARCHAR(500), 
	tracked_outcomes JSON, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_hotel_provider_run_correlation_id ON hotel_provider_run (correlation_id);
CREATE INDEX ix_hotel_provider_run_provider ON hotel_provider_run (provider);
CREATE INDEX ix_hotel_provider_run_execution_id ON hotel_provider_run (execution_id);
CREATE INDEX ix_hotel_provider_run_client_event_id ON hotel_provider_run (client_event_id);

CREATE TABLE hotel_sweep_lease (
	fingerprint VARCHAR(64) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	lock_token VARCHAR(64), 
	lock_acquired_at TIMESTAMP WITHOUT TIME ZONE, 
	lease_expires_at TIMESTAMP WITHOUT TIME ZONE, 
	attempt_count INTEGER NOT NULL, 
	last_provider_run_id VARCHAR(36), 
	last_error_code VARCHAR(64), 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (fingerprint)
);

CREATE INDEX ix_hotel_sweep_lease_last_provider_run_id ON hotel_sweep_lease (last_provider_run_id);
CREATE INDEX ix_hotel_sweep_lease_status_expires ON hotel_sweep_lease (status, lease_expires_at);
CREATE UNIQUE INDEX ix_hotel_sweep_lease_token ON hotel_sweep_lease (lock_token);

CREATE TABLE quick_search_cache_entry (
	id VARCHAR(36) NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	travel_date DATE NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	search_fingerprint VARCHAR(64), 
	canonical_request_json TEXT, 
	provider_set_json TEXT, 
	status VARCHAR(20) NOT NULL, 
	freshness_status VARCHAR(32) NOT NULL, 
	ttl_seconds INTEGER NOT NULL, 
	expires_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	captured_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_accessed_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	payload_json TEXT NOT NULL, 
	warnings_json TEXT NOT NULL, 
	source_hash VARCHAR(64) NOT NULL, 
	provider_latency_ms INTEGER, 
	result_count INTEGER NOT NULL, 
	confidence_score NUMERIC(5, 2), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_quick_search_cache_unit UNIQUE (origin_iata, destination_iata, travel_date, provider, source_hash)
);

CREATE INDEX ix_qs_cache_status ON quick_search_cache_entry (status);
CREATE INDEX ix_quick_search_cache_entry_freshness_status ON quick_search_cache_entry (freshness_status);
CREATE INDEX ix_quick_search_cache_entry_expires_at_utc ON quick_search_cache_entry (expires_at_utc);
CREATE INDEX ix_qs_cache_lookup ON quick_search_cache_entry (origin_iata, destination_iata, travel_date, provider);
CREATE INDEX ix_quick_search_cache_entry_search_fingerprint ON quick_search_cache_entry (search_fingerprint);
CREATE INDEX ix_qs_cache_expires ON quick_search_cache_entry (expires_at_utc);

CREATE TABLE quick_search_negative_cache_entry (
	id VARCHAR(36) NOT NULL, 
	negative_fingerprint VARCHAR(64) NOT NULL, 
	scope VARCHAR(32) NOT NULL, 
	reason VARCHAR(64) NOT NULL, 
	provider VARCHAR(40), 
	canonical_request_json TEXT NOT NULL, 
	observed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	freshness_status VARCHAR(32) NOT NULL, 
	retry_after_at TIMESTAMP WITHOUT TIME ZONE, 
	hit_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_qs_negative_cache_fingerprint UNIQUE (negative_fingerprint)
);

CREATE INDEX ix_qs_negative_cache_freshness ON quick_search_negative_cache_entry (freshness_status);
CREATE INDEX ix_quick_search_negative_cache_entry_observed_at ON quick_search_negative_cache_entry (observed_at);
CREATE INDEX ix_qs_negative_cache_expires ON quick_search_negative_cache_entry (expires_at);
CREATE INDEX ix_qs_negative_cache_provider ON quick_search_negative_cache_entry (provider, expires_at);

CREATE TABLE quick_search_popularity_counter (
	id VARCHAR(36) NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	travel_date DATE NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	search_count INTEGER NOT NULL, 
	first_searched_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_searched_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_qs_popularity_route_day_currency UNIQUE (origin_iata, destination_iata, travel_date, currency)
);

CREATE INDEX ix_qs_popularity_route ON quick_search_popularity_counter (origin_iata, destination_iata, travel_date);
CREATE INDEX ix_qs_popularity_count ON quick_search_popularity_counter (search_count);
CREATE INDEX ix_qs_popularity_last_seen ON quick_search_popularity_counter (last_searched_at);

CREATE TABLE quick_search_popularity_daily (
	id VARCHAR(36) NOT NULL, 
	search_date DATE NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	search_count INTEGER NOT NULL, 
	first_searched_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_searched_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_qs_popularity_daily_route_currency UNIQUE (search_date, origin_iata, destination_iata, currency)
);

CREATE INDEX ix_qs_popularity_daily_date_count ON quick_search_popularity_daily (search_date, search_count);
CREATE INDEX ix_qs_popularity_daily_route ON quick_search_popularity_daily (origin_iata, destination_iata, search_date);

CREATE TABLE quick_search_provider_lock (
	lock_key VARCHAR(64) NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	travel_date DATE NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	lock_token VARCHAR(64) NOT NULL, 
	acquired_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (lock_key)
);

CREATE INDEX ix_qs_provider_lock_expires ON quick_search_provider_lock (expires_at);
CREATE INDEX ix_qs_provider_lock_route ON quick_search_provider_lock (origin_iata, destination_iata, travel_date, provider);
CREATE INDEX ix_quick_search_provider_lock_lock_token ON quick_search_provider_lock (lock_token);

CREATE TABLE revalidation_job (
	id VARCHAR(36) NOT NULL, 
	job_type VARCHAR(32) NOT NULL, 
	target_type VARCHAR(16) NOT NULL, 
	target_fingerprint VARCHAR(64) NOT NULL, 
	provider VARCHAR(40), 
	priority INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	scheduled_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	lock_token VARCHAR(64), 
	lock_acquired_at TIMESTAMP WITHOUT TIME ZONE, 
	attempt_count INTEGER NOT NULL, 
	last_error_code VARCHAR(64), 
	payload_json TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_revalidation_job_active_target ON revalidation_job (job_type, target_type, target_fingerprint, coalesce(provider, '')) WHERE status IN ('queued', 'running');
CREATE INDEX ix_revalidation_job_target_type ON revalidation_job (target_type);
CREATE INDEX ix_revalidation_job_target_fingerprint ON revalidation_job (target_fingerprint);
CREATE INDEX ix_revalidation_job_due ON revalidation_job (status, scheduled_at, priority);
CREATE INDEX ix_revalidation_job_job_type ON revalidation_job (job_type);
CREATE INDEX ix_revalidation_job_target ON revalidation_job (target_type, target_fingerprint, provider, status);
CREATE INDEX ix_revalidation_job_status ON revalidation_job (status);
CREATE INDEX ix_revalidation_job_scheduled_at ON revalidation_job (scheduled_at);
CREATE INDEX ix_revalidation_job_lock_token ON revalidation_job (lock_token);

CREATE TABLE suggestion (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	text TEXT NOT NULL, 
	locale VARCHAR(8) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE support_feedback (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	feedback_type VARCHAR(20) NOT NULL, 
	message TEXT NOT NULL, 
	attachment_url VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	is_admin BOOLEAN NOT NULL, 
	locale VARCHAR(8) NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);


CREATE TABLE client_error_event (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	section VARCHAR(64) NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	stack TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_client_error_event_created_at ON client_error_event (created_at);
CREATE INDEX ix_client_error_event_section ON client_error_event (section);
CREATE INDEX ix_client_error_event_user_id ON client_error_event (user_id);

CREATE TABLE community_trending_snapshot_route (
	id VARCHAR(36) NOT NULL, 
	snapshot_id VARCHAR(36) NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	rank INTEGER NOT NULL, 
	search_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_community_trending_snapshot_route UNIQUE (snapshot_id, origin_iata, destination_iata), 
	CONSTRAINT ck_community_trending_snapshot_route_rank CHECK (rank >= 1), 
	CONSTRAINT ck_community_trending_snapshot_route_search_count CHECK (search_count >= 0), 
	FOREIGN KEY(snapshot_id) REFERENCES community_trending_snapshot (id) ON DELETE CASCADE
);

CREATE INDEX ix_community_trending_snapshot_route_snapshot_rank ON community_trending_snapshot_route (snapshot_id, rank);
CREATE INDEX ix_community_trending_snapshot_route_snapshot_route ON community_trending_snapshot_route (snapshot_id, origin_iata, destination_iata);

CREATE TABLE door_to_door_saved_location (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	location_type VARCHAR(32) NOT NULL, 
	label VARCHAR(180) NOT NULL, 
	lat NUMERIC(10, 6), 
	lng NUMERIC(10, 6), 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_door_to_door_saved_location_user_id ON door_to_door_saved_location (user_id);

CREATE TABLE flight_price_observation (
	id VARCHAR(36) NOT NULL, 
	offer_id VARCHAR(36) NOT NULL, 
	search_cache_entry_id VARCHAR(36), 
	provider VARCHAR(40) NOT NULL, 
	price_amount NUMERIC(10, 2), 
	currency VARCHAR(3) NOT NULL, 
	fare_family VARCHAR(64), 
	baggage_included BOOLEAN, 
	seats_left INTEGER, 
	observed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	freshness_status VARCHAR(32) NOT NULL, 
	confidence_score NUMERIC(5, 2), 
	validation_status VARCHAR(32) NOT NULL, 
	price_changed_since_last_seen BOOLEAN NOT NULL, 
	delta_abs NUMERIC(10, 2), 
	delta_pct NUMERIC(8, 4), 
	PRIMARY KEY (id), 
	FOREIGN KEY(offer_id) REFERENCES flight_offer_cache_entry (id), 
	FOREIGN KEY(search_cache_entry_id) REFERENCES quick_search_cache_entry (id)
);

CREATE INDEX ix_flight_price_observation_expires ON flight_price_observation (expires_at);
CREATE INDEX ix_flight_price_observation_observed_at ON flight_price_observation (observed_at);
CREATE INDEX ix_flight_price_observation_search_cache_entry_id ON flight_price_observation (search_cache_entry_id);
CREATE INDEX ix_flight_price_observation_freshness ON flight_price_observation (freshness_status);
CREATE INDEX ix_flight_price_observation_offer_id ON flight_price_observation (offer_id);
CREATE INDEX ix_flight_price_observation_offer_observed ON flight_price_observation (offer_id, observed_at);
CREATE INDEX ix_flight_price_observation_provider ON flight_price_observation (provider);

CREATE TABLE flight_watch (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	travel_date_local DATE NOT NULL, 
	target_price NUMERIC(10, 2), 
	group_id VARCHAR(36), 
	fare_profile JSON, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_flight_watch_group_id ON flight_watch (group_id);
CREATE UNIQUE INDEX uq_flight_watch_user_route_date ON flight_watch (user_id, origin_iata, destination_iata, travel_date_local);
CREATE INDEX ix_flight_watch_user_id ON flight_watch (user_id);

CREATE TABLE hotel_comp_set (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	anchor_hotel_id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(anchor_hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_comp_set_user_id ON hotel_comp_set (user_id);
CREATE INDEX ix_hotel_comp_set_anchor_hotel_id ON hotel_comp_set (anchor_hotel_id);

CREATE TABLE hotel_provider_alias (
	id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	provider_hotel_id VARCHAR(120) NOT NULL, 
	raw_name VARCHAR(255), 
	raw_address VARCHAR(255), 
	raw_payload TEXT, 
	confidence_score NUMERIC(5, 2), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_provider_alias_provider_hotel_id UNIQUE (provider, provider_hotel_id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_provider_alias_provider ON hotel_provider_alias (provider);
CREATE INDEX ix_hotel_provider_alias_hotel_id ON hotel_provider_alias (hotel_id);

CREATE TABLE hotel_provider_budget_reservation (
	id VARCHAR(36) NOT NULL, 
	budget_id VARCHAR(36) NOT NULL, 
	units INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(budget_id) REFERENCES hotel_provider_budget (id) ON DELETE CASCADE
);

CREATE INDEX ix_hotel_provider_budget_reservation_budget ON hotel_provider_budget_reservation (budget_id);
CREATE INDEX ix_hotel_provider_budget_reservation_status ON hotel_provider_budget_reservation (status);

CREATE TABLE hotel_provider_latency_aggregate (
	id VARCHAR(36) NOT NULL, 
	provider_run_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	operation VARCHAR(40) NOT NULL, 
	outcome VARCHAR(24) NOT NULL, 
	error_code VARCHAR(32) NOT NULL, 
	sample_count INTEGER NOT NULL, 
	total_duration_ms BIGINT NOT NULL, 
	min_duration_ms INTEGER NOT NULL, 
	max_duration_ms INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_provider_latency_aggregate_key UNIQUE (provider_run_id, provider, operation, outcome, error_code), 
	CONSTRAINT ck_hotel_provider_latency_sample_count_nonnegative CHECK (sample_count >= 0), 
	CONSTRAINT ck_hotel_provider_latency_total_duration_nonnegative CHECK (total_duration_ms >= 0), 
	CONSTRAINT ck_hotel_provider_latency_min_duration_nonnegative CHECK (min_duration_ms >= 0), 
	CONSTRAINT ck_hotel_provider_latency_max_duration_nonnegative CHECK (max_duration_ms >= 0), 
	FOREIGN KEY(provider_run_id) REFERENCES hotel_provider_run (id) ON DELETE CASCADE
);

CREATE INDEX ix_hotel_provider_latency_aggregate_run ON hotel_provider_latency_aggregate (provider_run_id);
CREATE INDEX ix_hotel_provider_latency_aggregate_provider_operation_created ON hotel_provider_latency_aggregate (provider, operation, created_at);

CREATE TABLE hotel_saved_search (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	schema_version VARCHAR(32) NOT NULL, 
	fingerprint VARCHAR(64) NOT NULL, 
	canonical_query_json TEXT NOT NULL, 
	label VARCHAR(120), 
	status VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_saved_search_user_fingerprint UNIQUE (user_id, fingerprint), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_hotel_saved_search_user_id ON hotel_saved_search (user_id);
CREATE INDEX ix_hotel_saved_search_user_status_updated ON hotel_saved_search (user_id, status, updated_at);
CREATE INDEX ix_hotel_saved_search_status ON hotel_saved_search (status);

CREATE TABLE hotel_stay_offer (
	id VARCHAR(36) NOT NULL, 
	canonical_hotel_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	provider_hotel_id VARCHAR(120) NOT NULL, 
	fingerprint_version VARCHAR(24) NOT NULL, 
	stay_query_fingerprint VARCHAR(64) NOT NULL, 
	offer_fingerprint VARCHAR(64) NOT NULL, 
	canonical_query_json TEXT NOT NULL, 
	conditions_completeness VARCHAR(16) NOT NULL, 
	fee_semantics VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_stay_offer_identity UNIQUE (provider, provider_hotel_id, stay_query_fingerprint, offer_fingerprint), 
	FOREIGN KEY(canonical_hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_stay_offer_canonical_hotel_id ON hotel_stay_offer (canonical_hotel_id);
CREATE INDEX ix_hotel_stay_offer_stay_query_fingerprint ON hotel_stay_offer (stay_query_fingerprint);
CREATE INDEX ix_hotel_stay_offer_hotel_provider ON hotel_stay_offer (canonical_hotel_id, provider);
CREATE INDEX ix_hotel_stay_offer_provider ON hotel_stay_offer (provider);
CREATE INDEX ix_hotel_stay_offer_offer_fingerprint ON hotel_stay_offer (offer_fingerprint);

CREATE TABLE hotel_tracked_offer (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	area_label VARCHAR(200), 
	origin_query VARCHAR(200), 
	latitude NUMERIC(10, 6), 
	longitude NUMERIC(10, 6), 
	radius_km INTEGER, 
	check_in DATE, 
	check_out DATE, 
	guests INTEGER NOT NULL, 
	room_label VARCHAR(160), 
	meal_plan VARCHAR(80), 
	cancellation_policy VARCHAR(120), 
	provider VARCHAR(40) NOT NULL, 
	offer_fingerprint VARCHAR(64), 
	initial_price NUMERIC(10, 2), 
	current_price NUMERIC(10, 2), 
	target_price NUMERIC(10, 2), 
	currency VARCHAR(3) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	lifecycle_state VARCHAR(24) NOT NULL, 
	lifecycle_version INTEGER NOT NULL, 
	lifecycle_changed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_tracked_offer_identity UNIQUE (user_id, hotel_id, check_in, check_out, guests, provider, room_label, meal_plan, cancellation_policy, currency, offer_fingerprint), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_tracked_offer_lifecycle_state ON hotel_tracked_offer (lifecycle_state);
CREATE INDEX ix_hotel_tracked_offer_hotel_id ON hotel_tracked_offer (hotel_id);
CREATE UNIQUE INDEX uq_hotel_tracked_offer_legacy_identity ON hotel_tracked_offer (user_id, hotel_id, check_in, check_out, guests, provider) WHERE offer_fingerprint IS NULL AND check_in IS NOT NULL AND check_out IS NOT NULL;
CREATE INDEX ix_hotel_tracked_offer_user_id ON hotel_tracked_offer (user_id);
CREATE INDEX ix_hotel_tracked_offer_offer_fingerprint ON hotel_tracked_offer (offer_fingerprint);

CREATE TABLE hotel_watchlist_item (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	label VARCHAR(80), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_watchlist_item_user_hotel UNIQUE (user_id, hotel_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_watchlist_item_hotel_id ON hotel_watchlist_item (hotel_id);
CREATE INDEX ix_hotel_watchlist_item_user_id ON hotel_watchlist_item (user_id);

CREATE TABLE idempotency_record (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	endpoint VARCHAR(200) NOT NULL, 
	idempotency_key VARCHAR(128) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	response_status INTEGER NOT NULL, 
	response_body TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_user_endpoint_key UNIQUE (user_id, endpoint, idempotency_key), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_idempotency_record_user_id ON idempotency_record (user_id);
CREATE INDEX ix_idempotency_record_created_at ON idempotency_record (created_at);
CREATE INDEX ix_idempotency_record_idempotency_key ON idempotency_record (idempotency_key);
CREATE INDEX ix_idempotency_record_endpoint ON idempotency_record (endpoint);

CREATE TABLE password_reset_token (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (token_hash)
);

CREATE INDEX ix_password_reset_token_token_hash ON password_reset_token (token_hash);
CREATE INDEX ix_password_reset_token_used_at ON password_reset_token (used_at);
CREATE INDEX ix_password_reset_token_expires_at ON password_reset_token (expires_at);
CREATE INDEX ix_password_reset_token_user_id ON password_reset_token (user_id);

CREATE TABLE refresh_token (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	replaced_by_token_id VARCHAR(36), 
	user_agent VARCHAR(255), 
	ip_hash VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (token_hash), 
	FOREIGN KEY(replaced_by_token_id) REFERENCES refresh_token (id)
);

CREATE INDEX ix_refresh_token_token_hash ON refresh_token (token_hash);
CREATE INDEX ix_refresh_token_revoked_at ON refresh_token (revoked_at);
CREATE INDEX ix_refresh_token_expires_at ON refresh_token (expires_at);
CREATE INDEX ix_refresh_token_user_id ON refresh_token (user_id);

CREATE TABLE security_activity (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(40) NOT NULL, 
	ip VARCHAR(45), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_security_activity_user_id ON security_activity (user_id);
CREATE INDEX ix_security_activity_user_created ON security_activity (user_id, created_at);

CREATE TABLE user_note (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	body TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_note_user_id ON user_note (user_id);

CREATE TABLE user_notification_state (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	source_type VARCHAR(40) NOT NULL, 
	source_id VARCHAR(36) NOT NULL, 
	read_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_notification_state_source UNIQUE (user_id, source_type, source_id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_notification_state_source_id ON user_notification_state (source_id);
CREATE INDEX ix_user_notification_state_user_id ON user_notification_state (user_id);
CREATE INDEX ix_user_notification_state_user_read ON user_notification_state (user_id, read_at);

CREATE TABLE user_preference (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	default_radius_km INTEGER NOT NULL, 
	include_stops_default BOOLEAN NOT NULL, 
	include_nearby_origins_default BOOLEAN NOT NULL, 
	include_nearby_destinations_default BOOLEAN NOT NULL, 
	country_price_hint_mode_default VARCHAR(16) NOT NULL, 
	calendar_hint_bucket_mode_default VARCHAR(24) NOT NULL, 
	calendar_hint_guideline_low_max_default NUMERIC(10, 2) NOT NULL, 
	calendar_hint_guideline_mid_max_default NUMERIC(10, 2) NOT NULL, 
	avoid_departure_before VARCHAR(5), 
	depart_before_default VARCHAR(5), 
	strict_filters_default BOOLEAN NOT NULL, 
	preferred_currency VARCHAR(3) NOT NULL, 
	language VARCHAR(8) NOT NULL, 
	quiet_hours_enabled BOOLEAN NOT NULL, 
	quiet_hours_start VARCHAR(5), 
	quiet_hours_end VARCHAR(5), 
	quiet_hours_timezone VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_user_preference_user_id ON user_preference (user_id);

CREATE TABLE user_preference_appearance (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	theme VARCHAR(16) NOT NULL, 
	density VARCHAR(16) NOT NULL, 
	reduce_motion BOOLEAN NOT NULL, 
	high_contrast BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_user_preference_appearance_user_id ON user_preference_appearance (user_id);

CREATE TABLE user_preference_region (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	language VARCHAR(8) NOT NULL, 
	region VARCHAR(8) NOT NULL, 
	time_format VARCHAR(8) NOT NULL, 
	decimal_separator VARCHAR(2) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_user_preference_region_user_id ON user_preference_region (user_id);

CREATE TABLE user_profile (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	display_name VARCHAR(120) NOT NULL, 
	avatar_url VARCHAR(500), 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_user_profile_user_id ON user_profile (user_id);

CREATE TABLE user_session (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	device VARCHAR(200) NOT NULL, 
	ip VARCHAR(45), 
	last_seen TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_session_user_active_last_seen ON user_session (user_id, is_active, last_seen);
CREATE INDEX ix_user_session_user_id ON user_session (user_id);

CREATE TABLE ux_event (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	event_name VARCHAR(64) NOT NULL, 
	duration_ms INTEGER, 
	metadata_json TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_ux_event_created_at ON ux_event (created_at);
CREATE INDEX ix_ux_event_event_name ON ux_event (event_name);
CREATE INDEX ix_ux_event_user_id ON ux_event (user_id);

CREATE TABLE alert_rule (
	id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	rule_type VARCHAR(30) NOT NULL, 
	threshold_value NUMERIC(10, 2), 
	min_change_pct NUMERIC(5, 2), 
	notify_on_every_change BOOLEAN NOT NULL, 
	cooldown_minutes INTEGER NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id)
);

CREATE INDEX ix_alert_rule_watch_enabled ON alert_rule (watch_id, enabled);
CREATE INDEX ix_alert_rule_watch_id ON alert_rule (watch_id);

CREATE TABLE community_price_report (
	id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	trigger_reason VARCHAR(20) NOT NULL, 
	flew BOOLEAN NOT NULL, 
	price_per_traveler NUMERIC(10, 2), 
	currency VARCHAR(3) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_community_price_report_watch UNIQUE (watch_id), 
	CONSTRAINT ck_community_price_report_flew_price CHECK ((flew = false AND price_per_traveler IS NULL) OR (flew = true AND price_per_traveler > 0)), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_community_price_report_user ON community_price_report (user_id);

CREATE TABLE door_to_door_saved_place (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	label VARCHAR(180) NOT NULL, 
	note VARCHAR(280) NOT NULL, 
	watch_id VARCHAR(36), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id)
);

CREATE INDEX ix_door_to_door_saved_place_watch_id ON door_to_door_saved_place (watch_id);
CREATE INDEX ix_door_to_door_saved_place_user_id ON door_to_door_saved_place (user_id);

CREATE TABLE door_to_door_search_history (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	origin_json TEXT NOT NULL, 
	final_destination_json TEXT NOT NULL, 
	preferences_json TEXT NOT NULL, 
	summary_json TEXT NOT NULL, 
	warnings_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_saved BOOLEAN NOT NULL, 
	label VARCHAR(120), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id)
);

CREATE INDEX ix_door_to_door_search_history_user_id ON door_to_door_search_history (user_id);
CREATE INDEX ix_door_to_door_search_history_created_at ON door_to_door_search_history (created_at);
CREATE INDEX ix_door_to_door_search_history_is_saved ON door_to_door_search_history (is_saved);
CREATE INDEX ix_door_to_door_search_history_watch_id ON door_to_door_search_history (watch_id);

CREATE TABLE hotel_alert_rule (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	tracked_offer_id VARCHAR(36), 
	rule_type VARCHAR(40) NOT NULL, 
	threshold_amount NUMERIC(10, 2), 
	threshold_percent NUMERIC(5, 2), 
	compare_against VARCHAR(20) NOT NULL, 
	cooldown_minutes INTEGER NOT NULL, 
	evaluation_state VARCHAR(16) NOT NULL, 
	last_fired_at TIMESTAMP WITHOUT TIME ZONE, 
	last_event_fingerprint VARCHAR(64), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id), 
	FOREIGN KEY(tracked_offer_id) REFERENCES hotel_tracked_offer (id)
);

CREATE INDEX ix_hotel_alert_rule_hotel_id ON hotel_alert_rule (hotel_id);
CREATE INDEX ix_hotel_alert_rule_user_id ON hotel_alert_rule (user_id);
CREATE INDEX ix_hotel_alert_rule_tracked_offer_id ON hotel_alert_rule (tracked_offer_id);
CREATE INDEX ix_hotel_alert_rule_last_event_fingerprint ON hotel_alert_rule (last_event_fingerprint);

CREATE TABLE hotel_comp_set_member (
	id VARCHAR(36) NOT NULL, 
	comp_set_id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_comp_set_member_comp_hotel UNIQUE (comp_set_id, hotel_id), 
	FOREIGN KEY(comp_set_id) REFERENCES hotel_comp_set (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id)
);

CREATE INDEX ix_hotel_comp_set_member_hotel_id ON hotel_comp_set_member (hotel_id);
CREATE INDEX ix_hotel_comp_set_member_comp_set_id ON hotel_comp_set_member (comp_set_id);

CREATE TABLE hotel_rate_snapshot (
	id VARCHAR(36) NOT NULL, 
	hotel_id VARCHAR(36) NOT NULL, 
	stay_offer_id VARCHAR(36), 
	tracked_offer_id VARCHAR(36), 
	provider_run_id VARCHAR(36), 
	provider VARCHAR(40) NOT NULL, 
	check_in DATE NOT NULL, 
	check_out DATE NOT NULL, 
	guests INTEGER NOT NULL, 
	room_label VARCHAR(160), 
	meal_plan VARCHAR(80), 
	cancellation_policy VARCHAR(120), 
	currency VARCHAR(3) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	availability_status VARCHAR(20) NOT NULL, 
	deep_link VARCHAR(500), 
	collected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	observed_at TIMESTAMP WITHOUT TIME ZONE, 
	stay_query_fingerprint VARCHAR(64), 
	offer_fingerprint VARCHAR(64), 
	snapshot_outcome VARCHAR(24), 
	price_semantics VARCHAR(16), 
	amount_base NUMERIC(10, 2), 
	amount_total NUMERIC(10, 2), 
	fees_json TEXT, 
	conditions_completeness VARCHAR(16), 
	PRIMARY KEY (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id), 
	FOREIGN KEY(stay_offer_id) REFERENCES hotel_stay_offer (id), 
	FOREIGN KEY(tracked_offer_id) REFERENCES hotel_tracked_offer (id), 
	FOREIGN KEY(provider_run_id) REFERENCES hotel_provider_run (id)
);

CREATE INDEX ix_hotel_rate_snapshot_hotel_id ON hotel_rate_snapshot (hotel_id);
CREATE INDEX ix_hotel_rate_snapshot_check_in ON hotel_rate_snapshot (check_in);
CREATE INDEX ix_hotel_rate_snapshot_check_out ON hotel_rate_snapshot (check_out);
CREATE INDEX ix_hotel_rate_snapshot_offer_fingerprint ON hotel_rate_snapshot (offer_fingerprint);
CREATE INDEX ix_hotel_rate_snapshot_tracked_offer_id ON hotel_rate_snapshot (tracked_offer_id);
CREATE INDEX ix_hotel_rate_snapshot_provider ON hotel_rate_snapshot (provider);
CREATE INDEX ix_hotel_rate_snapshot_stay_query_fingerprint ON hotel_rate_snapshot (stay_query_fingerprint);
CREATE INDEX ix_hotel_rate_snapshot_provider_run_id ON hotel_rate_snapshot (provider_run_id);
CREATE INDEX ix_hotel_rate_snapshot_stay_offer_id ON hotel_rate_snapshot (stay_offer_id);
CREATE INDEX ix_hotel_rate_snapshot_collected_at ON hotel_rate_snapshot (collected_at);
CREATE INDEX ix_hotel_rate_snapshot_observed_at ON hotel_rate_snapshot (observed_at);

CREATE TABLE hotel_tracked_offer_lifecycle_event (
	id VARCHAR(36) NOT NULL, 
	tracked_offer_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	from_state VARCHAR(24) NOT NULL, 
	to_state VARCHAR(24) NOT NULL, 
	action VARCHAR(24) NOT NULL, 
	source VARCHAR(32) NOT NULL, 
	state_version INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_tracking_lifecycle_version UNIQUE (tracked_offer_id, state_version), 
	FOREIGN KEY(tracked_offer_id) REFERENCES hotel_tracked_offer (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_hotel_tracking_lifecycle_user_created ON hotel_tracked_offer_lifecycle_event (user_id, created_at);
CREATE INDEX ix_hotel_tracking_lifecycle_offer_created ON hotel_tracked_offer_lifecycle_event (tracked_offer_id, created_at);

CREATE TABLE hotel_user_stay_watch (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	stay_offer_id VARCHAR(36) NOT NULL, 
	legacy_tracked_offer_id VARCHAR(36), 
	status VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_user_stay_watch_identity UNIQUE (user_id, stay_offer_id), 
	CONSTRAINT uq_hotel_user_stay_watch_legacy UNIQUE (legacy_tracked_offer_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(stay_offer_id) REFERENCES hotel_stay_offer (id), 
	FOREIGN KEY(legacy_tracked_offer_id) REFERENCES hotel_tracked_offer (id) ON DELETE SET NULL
);

CREATE INDEX ix_hotel_user_stay_watch_stay_offer_id ON hotel_user_stay_watch (stay_offer_id);
CREATE INDEX ix_hotel_user_stay_watch_user_id ON hotel_user_stay_watch (user_id);
CREATE INDEX ix_hotel_user_stay_watch_user_status_updated ON hotel_user_stay_watch (user_id, status, updated_at);
CREATE INDEX ix_hotel_user_stay_watch_legacy_tracked_offer_id ON hotel_user_stay_watch (legacy_tracked_offer_id);
CREATE INDEX ix_hotel_user_stay_watch_status ON hotel_user_stay_watch (status);

CREATE TABLE price_snapshot (
	id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	captured_at_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	departure_time_local VARCHAR(5), 
	raw_price NUMERIC(10, 2) NOT NULL, 
	raw_currency VARCHAR(3) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	is_stale BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id)
);

CREATE INDEX ix_price_snapshot_watch_captured ON price_snapshot (watch_id, captured_at_utc);
CREATE INDEX ix_price_snapshot_watch_id ON price_snapshot (watch_id);

CREATE TABLE watch_tracked_flight_leg (
	id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	sequence INTEGER NOT NULL, 
	flight_instance_fingerprint VARCHAR(64) NOT NULL, 
	carrier_code VARCHAR(16), 
	flight_number VARCHAR(32), 
	origin_iata VARCHAR(3) NOT NULL, 
	destination_iata VARCHAR(3) NOT NULL, 
	departure_date_local DATE, 
	scheduled_departure_at TIMESTAMP WITHOUT TIME ZONE, 
	scheduled_arrival_at TIMESTAMP WITHOUT TIME ZONE, 
	identity_source VARCHAR(24) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_watch_tracked_flight_leg_sequence UNIQUE (watch_id, sequence), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id) ON DELETE CASCADE
);

CREATE INDEX ix_watch_tracked_flight_leg_instance ON watch_tracked_flight_leg (flight_instance_fingerprint);
CREATE INDEX ix_watch_tracked_flight_leg_watch_id ON watch_tracked_flight_leg (watch_id);

CREATE TABLE door_to_door_chosen_option (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	watch_id VARCHAR(36) NOT NULL, 
	history_id VARCHAR(36), 
	option_id VARCHAR(80) NOT NULL, 
	option_label VARCHAR(120) NOT NULL, 
	option_summary_json TEXT NOT NULL, 
	chosen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(watch_id) REFERENCES flight_watch (id), 
	FOREIGN KEY(history_id) REFERENCES door_to_door_search_history (id)
);

CREATE INDEX ix_door_to_door_chosen_option_chosen_at ON door_to_door_chosen_option (chosen_at);
CREATE INDEX ix_door_to_door_chosen_option_watch_id ON door_to_door_chosen_option (watch_id);
CREATE INDEX ix_door_to_door_chosen_option_user_id ON door_to_door_chosen_option (user_id);

CREATE TABLE hotel_alert_event (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	rule_id VARCHAR(36), 
	hotel_id VARCHAR(36) NOT NULL, 
	provider_run_id VARCHAR(36), 
	event_type VARCHAR(30) NOT NULL, 
	message TEXT NOT NULL, 
	trigger_value NUMERIC(10, 2), 
	event_fingerprint VARCHAR(64), 
	snapshot_before_id VARCHAR(36), 
	snapshot_after_id VARCHAR(36), 
	baseline_snapshot_id VARCHAR(36), 
	baseline_source VARCHAR(24), 
	baseline_amount NUMERIC(10, 2), 
	baseline_currency VARCHAR(3), 
	comparability_key VARCHAR(180), 
	reason_code VARCHAR(64), 
	eligibility_status VARCHAR(24), 
	rule_version VARCHAR(32), 
	evaluation_state VARCHAR(16), 
	cooldown_until TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(rule_id) REFERENCES hotel_alert_rule (id), 
	FOREIGN KEY(hotel_id) REFERENCES hotel_property (id), 
	FOREIGN KEY(provider_run_id) REFERENCES hotel_provider_run (id)
);

CREATE INDEX ix_hotel_alert_event_user_id ON hotel_alert_event (user_id);
CREATE INDEX ix_hotel_alert_event_provider_run_id ON hotel_alert_event (provider_run_id);
CREATE INDEX ix_hotel_alert_event_created_at ON hotel_alert_event (created_at);
CREATE INDEX ix_hotel_alert_event_rule_created ON hotel_alert_event (rule_id, created_at);
CREATE INDEX ix_hotel_alert_event_hotel_id ON hotel_alert_event (hotel_id);
CREATE INDEX ix_hotel_alert_event_rule_id ON hotel_alert_event (rule_id);
CREATE UNIQUE INDEX uq_hotel_alert_event_fingerprint ON hotel_alert_event (event_fingerprint);

CREATE TABLE notification_event (
	id VARCHAR(36) NOT NULL, 
	rule_id VARCHAR(36) NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	delivery_status VARCHAR(20) NOT NULL, 
	message TEXT NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at TIMESTAMP WITHOUT TIME ZONE, 
	last_error VARCHAR(500), 
	delivered_at TIMESTAMP WITHOUT TIME ZONE, 
	dedupe_key VARCHAR(120), 
	group_key VARCHAR(180), 
	group_reason VARCHAR(64), 
	is_digest BOOLEAN NOT NULL, 
	grouped_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(rule_id) REFERENCES alert_rule (id)
);

CREATE INDEX ix_notification_event_rule_id ON notification_event (rule_id);
CREATE INDEX ix_notification_event_dedupe_key ON notification_event (dedupe_key);
CREATE INDEX ix_notification_event_group_key ON notification_event (group_key);
CREATE INDEX ix_notification_event_rule_created ON notification_event (rule_id, created_at);
CREATE INDEX ix_notification_event_delivered_at ON notification_event (delivered_at);
CREATE INDEX ix_notification_event_next_attempt_at ON notification_event (next_attempt_at);

CREATE TABLE hotel_notification_delivery (
	id VARCHAR(36) NOT NULL, 
	source_event_id VARCHAR(36) NOT NULL, 
	recipient_user_id VARCHAR(36) NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	template_version VARCHAR(32) NOT NULL, 
	idempotency_key VARCHAR(64) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	attempts INTEGER NOT NULL, 
	next_attempt_at TIMESTAMP WITHOUT TIME ZONE, 
	last_error VARCHAR(500), 
	error_class VARCHAR(24), 
	delivered_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_hotel_notification_delivery_idempotency UNIQUE (idempotency_key), 
	FOREIGN KEY(source_event_id) REFERENCES hotel_alert_event (id) ON DELETE CASCADE, 
	FOREIGN KEY(recipient_user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_hotel_notification_delivery_recipient ON hotel_notification_delivery (recipient_user_id, created_at);
CREATE INDEX ix_hotel_notification_delivery_source ON hotel_notification_delivery (source_event_id);
CREATE INDEX ix_hotel_notification_delivery_queue ON hotel_notification_delivery (status, next_attempt_at, created_at);
