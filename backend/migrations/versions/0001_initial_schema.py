"""initial schema — full DDL per docs/BACKEND-SCHEMA.md

Revision ID: 0001
Revises:
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("create extension if not exists postgis")
    op.execute("create extension if not exists pgcrypto")

    op.execute(
        """
        create or replace function set_updated_at()
        returns trigger as $$
        begin
          new.updated_at = now();
          return new;
        end;
        $$ language plpgsql;
        """
    )

    op.execute(
        "create type user_role as enum ('sdma_official', 'field_officer', 'control_room')"
    )
    op.execute(
        "create type hazard_type as enum ('flood', 'landslide', 'cloudburst', 'coastal_erosion')"
    )
    op.execute(
        "create type data_confidence as enum ('baseline', 'field_verified', 'due_for_reverification')"
    )
    op.execute(
        "create type structural_condition as enum ('Kutcha', 'Semi-pucca', 'Pucca', 'unknown')"
    )
    op.execute(
        "create type priority_tier as enum ('immediate', 'short_term', 'medium_term')"
    )
    op.execute(
        "create type shelter_status as enum ('active', 'full', 'closed', 'damaged')"
    )
    op.execute(
        "create type review_status as enum ('unreviewed', 'approved', 'flagged')"
    )
    op.execute(
        "create type relocation_status as enum ('assigned', 'in_transit', 'arrived')"
    )
    op.execute(
        "create type vehicle_status as enum ('available', 'assigned', 'in_transit', 'unavailable')"
    )
    op.execute(
        "create type handoff_status as enum ('open', 'acknowledged', 'in_progress', 'resolved')"
    )

    op.execute(
        """
        create table districts (
          district_id uuid primary key default gen_random_uuid(),
          name text not null unique,
          state text not null,
          geom geometry(MultiPolygon, 4326),
          primary_hazards hazard_type[] not null default '{}',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_districts_geom on districts using gist (geom)")
    op.execute(
        "create trigger trg_districts_updated before update on districts "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table users (
          user_id uuid primary key default gen_random_uuid(),
          full_name text not null,
          email text not null unique,
          phone text,
          password_hash text not null,
          role user_role not null,
          district_id uuid references districts(district_id),
          is_active boolean not null default true,
          last_login_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_users_district on users(district_id)")
    op.execute("create index idx_users_role on users(role)")
    op.execute(
        "create trigger trg_users_updated before update on users "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table zones (
          zone_id uuid primary key default gen_random_uuid(),
          district_id uuid not null references districts(district_id),
          name text not null,
          geom geometry(Polygon, 4326) not null,
          hazard_types hazard_type[] not null,
          population integer not null default 0 check (population >= 0),
          incident_history jsonb not null default '[]',
          data_confidence data_confidence not null default 'baseline',
          last_verified_at timestamptz,
          last_verified_by uuid references users(user_id),
          susceptibility_score numeric(5,4) check (susceptibility_score between 0 and 1),
          susceptibility_factors jsonb,
          gsi_classification text,
          gsi_score numeric(5,2),
          risk_score_72h numeric(5,4) check (risk_score_72h between 0 and 1),
          risk_score_factors jsonb,
          risk_score_updated_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_zones_geom on zones using gist (geom)")
    op.execute("create index idx_zones_district on zones(district_id)")
    op.execute("create index idx_zones_confidence on zones(data_confidence)")
    op.execute("create index idx_zones_hazard_types on zones using gin (hazard_types)")
    op.execute(
        "create trigger trg_zones_updated before update on zones "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table households (
          household_id uuid primary key default gen_random_uuid(),
          zone_id uuid not null references zones(zone_id),
          geom geometry(Point, 4326) not null,
          population_count integer not null default 0 check (population_count >= 0),
          children_count integer not null default 0 check (children_count >= 0),
          elderly_count integer not null default 0 check (elderly_count >= 0),
          assistance_needs_count integer not null default 0 check (assistance_needs_count >= 0),
          structural_condition structural_condition not null default 'unknown',
          vulnerability_score numeric(5,4) check (vulnerability_score between 0 and 1),
          vulnerability_factors jsonb,
          priority_tier priority_tier,
          priority_factors jsonb,
          data_confidence data_confidence not null default 'baseline',
          last_surveyed_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_households_geom on households using gist (geom)")
    op.execute("create index idx_households_zone on households(zone_id)")
    op.execute("create index idx_households_priority on households(priority_tier)")
    op.execute("create index idx_households_confidence on households(data_confidence)")
    op.execute(
        "create trigger trg_households_updated before update on households "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table shelters (
          shelter_id uuid primary key default gen_random_uuid(),
          district_id uuid not null references districts(district_id),
          name text not null,
          geom geometry(Point, 4326) not null,
          max_capacity integer not null check (max_capacity > 0),
          current_occupancy integer not null default 0 check (current_occupancy >= 0),
          facilities jsonb not null default '{}',
          status shelter_status not null default 'active',
          last_updated_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint chk_occupancy_within_capacity check (current_occupancy <= max_capacity)
        )
        """
    )
    op.execute("create index idx_shelters_geom on shelters using gist (geom)")
    op.execute("create index idx_shelters_status on shelters(status)")
    op.execute(
        "create trigger trg_shelters_updated before update on shelters "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table surveys (
          survey_id uuid primary key,
          zone_id uuid not null references zones(zone_id),
          household_id uuid references households(household_id),
          officer_id uuid not null references users(user_id),
          submitted_at timestamptz not null,
          synced_at timestamptz,
          payload jsonb not null,
          photo_url text,
          geotag geometry(Point, 4326),
          review_status review_status not null default 'unreviewed',
          reviewed_by uuid references users(user_id),
          reviewed_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_surveys_zone on surveys(zone_id)")
    op.execute("create index idx_surveys_household on surveys(household_id)")
    op.execute("create index idx_surveys_review_status on surveys(review_status)")
    op.execute("create index idx_surveys_geotag on surveys using gist (geotag)")
    op.execute(
        "create trigger trg_surveys_updated before update on surveys "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table vehicles (
          vehicle_id uuid primary key default gen_random_uuid(),
          district_id uuid not null references districts(district_id),
          vehicle_type text not null,
          capacity integer not null check (capacity > 0),
          status vehicle_status not null default 'available',
          current_location geometry(Point, 4326),
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_vehicles_district on vehicles(district_id)")
    op.execute("create index idx_vehicles_status on vehicles(status)")
    op.execute(
        "create trigger trg_vehicles_updated before update on vehicles "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table escorts (
          escort_id uuid primary key default gen_random_uuid(),
          user_id uuid references users(user_id),
          full_name text not null,
          agency text,
          contact_phone text,
          status text not null default 'available',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_escorts_status on escorts(status)")
    op.execute(
        "create trigger trg_escorts_updated before update on escorts "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table routes (
          route_id uuid primary key default gen_random_uuid(),
          origin_geom geometry(Point, 4326) not null,
          dest_geom geometry(Point, 4326) not null,
          path geometry(LineString, 4326) not null,
          blocked_segments jsonb not null default '[]',
          distance_km numeric(8,2),
          estimated_duration_minutes integer,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_routes_path on routes using gist (path)")
    op.execute(
        "create trigger trg_routes_updated before update on routes "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table relocation_records (
          record_id uuid primary key default gen_random_uuid(),
          household_id uuid not null references households(household_id),
          shelter_id uuid not null references shelters(shelter_id),
          route_id uuid references routes(route_id),
          vehicle_id uuid references vehicles(vehicle_id),
          escort_id uuid references escorts(escort_id),
          priority_tier priority_tier not null,
          priority_factors jsonb,
          allocation_factors jsonb,
          status relocation_status not null default 'assigned',
          decided_by uuid not null references users(user_id),
          assigned_at timestamptz not null default now(),
          in_transit_at timestamptz,
          arrived_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint chk_status_timestamps check (
            (status = 'assigned') or
            (status = 'in_transit' and in_transit_at is not null) or
            (status = 'arrived' and in_transit_at is not null and arrived_at is not null)
          )
        )
        """
    )
    op.execute("create index idx_relocation_household on relocation_records(household_id)")
    op.execute("create index idx_relocation_shelter on relocation_records(shelter_id)")
    op.execute("create index idx_relocation_status on relocation_records(status)")
    op.execute(
        "create trigger trg_relocation_records_updated before update on relocation_records "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table risk_forecasts (
          forecast_id uuid primary key default gen_random_uuid(),
          zone_id uuid not null references zones(zone_id),
          horizon_hours integer not null default 72,
          score numeric(5,4) not null check (score between 0 and 1),
          factors jsonb not null,
          model_version text not null,
          generated_at timestamptz not null default now()
        )
        """
    )
    op.execute(
        "create index idx_risk_forecasts_zone_time on risk_forecasts(zone_id, generated_at desc)"
    )

    op.execute(
        """
        create table change_detections (
          detection_id uuid primary key default gen_random_uuid(),
          zone_id uuid not null references zones(zone_id),
          before_image_ref text not null,
          after_image_ref text not null,
          affected_area_geom geometry(MultiPolygon, 4326),
          confidence numeric(5,4) check (confidence between 0 and 1),
          cross_referenced_survey_ids uuid[] not null default '{}',
          cross_referenced_household_ids uuid[] not null default '{}',
          detected_at timestamptz not null default now(),
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_change_detections_zone on change_detections(zone_id)")
    op.execute(
        "create index idx_change_detections_geom on change_detections using gist (affected_area_geom)"
    )

    op.execute(
        """
        create table user_zone_assignments (
          user_id uuid not null references users(user_id),
          zone_id uuid not null references zones(zone_id),
          assigned_at timestamptz not null default now(),
          primary key (user_id, zone_id)
        )
        """
    )
    op.execute("create index idx_zone_assignments_zone on user_zone_assignments(zone_id)")

    op.execute(
        """
        create table handoff_logs (
          log_id uuid primary key default gen_random_uuid(),
          need_type text not null,
          agency text not null,
          status handoff_status not null default 'open',
          linked_record_id uuid references relocation_records(record_id),
          zone_id uuid references zones(zone_id),
          household_id uuid references households(household_id),
          description text,
          raised_at timestamptz not null default now(),
          acknowledged_at timestamptz,
          resolved_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint chk_handoff_has_context check (
            linked_record_id is not null or zone_id is not null or household_id is not null
          )
        )
        """
    )
    op.execute("create index idx_handoff_status on handoff_logs(status)")
    op.execute("create index idx_handoff_linked_record on handoff_logs(linked_record_id)")
    op.execute(
        "create trigger trg_handoff_logs_updated before update on handoff_logs "
        "for each row execute function set_updated_at()"
    )

    op.execute(
        """
        create table audit_log (
          entry_id uuid primary key default gen_random_uuid(),
          actor_id uuid not null references users(user_id),
          action_type text not null,
          entity_type text not null,
          entity_id uuid not null,
          factors_snapshot jsonb,
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_audit_entity on audit_log(entity_type, entity_id)")
    op.execute("create index idx_audit_actor on audit_log(actor_id)")
    op.execute("revoke update, delete on audit_log from public")

    op.execute(
        """
        create table incident_outcomes (
          outcome_id uuid primary key default gen_random_uuid(),
          zone_id uuid not null references zones(zone_id),
          relocation_record_id uuid references relocation_records(record_id),
          forecast_id uuid references risk_forecasts(forecast_id),
          detection_id uuid references change_detections(detection_id),
          occurred_at timestamptz not null,
          shelter_adequate boolean,
          route_held_up boolean,
          actual_impact jsonb,
          notes text,
          recorded_by uuid not null references users(user_id),
          recorded_at timestamptz not null default now(),
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index idx_incident_outcomes_zone on incident_outcomes(zone_id)")
    op.execute("create index idx_incident_outcomes_forecast on incident_outcomes(forecast_id)")
    op.execute("create index idx_incident_outcomes_record on incident_outcomes(relocation_record_id)")

    op.execute("alter table households enable row level security")
    op.execute(
        """
        create policy household_access on households
          using (
            current_setting('app.current_role', true) in ('sdma_official', 'control_room')
            or zone_id in (
              select zone_id from user_zone_assignments
              where user_id = current_setting('app.current_user_id', true)::uuid
            )
          )
        """
    )


def downgrade() -> None:
    op.execute("drop policy if exists household_access on households")
    op.execute("drop table if exists incident_outcomes")
    op.execute("drop table if exists audit_log")
    op.execute("drop table if exists handoff_logs")
    op.execute("drop table if exists user_zone_assignments")
    op.execute("drop table if exists change_detections")
    op.execute("drop table if exists risk_forecasts")
    op.execute("drop table if exists relocation_records")
    op.execute("drop table if exists routes")
    op.execute("drop table if exists escorts")
    op.execute("drop table if exists vehicles")
    op.execute("drop table if exists surveys")
    op.execute("drop table if exists shelters")
    op.execute("drop table if exists households")
    op.execute("drop table if exists zones")
    op.execute("drop table if exists users")
    op.execute("drop table if exists districts")

    op.execute("drop function if exists set_updated_at()")

    op.execute("drop type if exists handoff_status")
    op.execute("drop type if exists vehicle_status")
    op.execute("drop type if exists relocation_status")
    op.execute("drop type if exists review_status")
    op.execute("drop type if exists shelter_status")
    op.execute("drop type if exists priority_tier")
    op.execute("drop type if exists structural_condition")
    op.execute("drop type if exists data_confidence")
    op.execute("drop type if exists hazard_type")
    op.execute("drop type if exists user_role")
