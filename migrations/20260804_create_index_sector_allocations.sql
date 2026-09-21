create table if not exists index_sector_allocations (
  id bigserial primary key,
  index_name varchar(32) not null check (index_name in ('NIFTY50', 'NIFTYMIDCAP150', 'NIFTY500')),
  sector varchar(200) not null,
  weight_percent numeric(7,4) not null check (weight_percent between 0 and 100),
  factsheet_date date not null,
  source_url text not null,
  source_file varchar(255) not null,
  row_hash varchar(64) not null,
  ingested_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_index_sector_allocation_snapshot unique (index_name, sector, factsheet_date)
);

create index if not exists ix_index_sector_allocations_latest
  on index_sector_allocations (index_name, factsheet_date);

create table if not exists ingestion_runs (
  id bigserial primary key,
  source varchar(100) not null,
  status varchar(24) not null,
  method_used varchar(32),
  records_fetched integer not null default 0,
  inserted integer not null default 0,
  updated integer not null default 0,
  duplicates_skipped integer not null default 0,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  error_message text
);

create index if not exists ix_ingestion_runs_source on ingestion_runs (source);
create index if not exists ix_ingestion_runs_status on ingestion_runs (status);
