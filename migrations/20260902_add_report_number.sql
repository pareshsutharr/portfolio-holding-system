create sequence if not exists portfolio_report_number_seq start 1;

alter table portfolio_runs
  add column if not exists report_number bigint;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'portfolio_runs_report_number_key'
  ) then
    alter table portfolio_runs
      add constraint portfolio_runs_report_number_key unique (report_number);
  end if;
end
$$;
