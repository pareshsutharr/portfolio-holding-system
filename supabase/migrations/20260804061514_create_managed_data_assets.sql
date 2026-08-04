insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'portfolio-reference-data',
  'portfolio-reference-data',
  false,
  26214400,
  array[
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/json'
  ]
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create table if not exists public.managed_data_assets (
  object_path text primary key,
  category_key text not null,
  bucket_id text not null references storage.buckets(id),
  original_name text not null,
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 varchar(64) not null check (length(sha256) = 64),
  updated_at timestamptz not null default now()
);

create index if not exists ix_managed_data_assets_category_key
  on public.managed_data_assets (category_key);

alter table public.managed_data_assets enable row level security;

-- No anon/authenticated policy is intentional. Reference assets are managed
-- exclusively by the server's secret key and are never public.
revoke all on table public.managed_data_assets from anon, authenticated;
