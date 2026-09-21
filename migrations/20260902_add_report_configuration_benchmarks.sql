alter table report_configurations
  add column if not exists benchmarks json;
