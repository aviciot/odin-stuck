# the-M Postgres

Source folder for the `them-postgres` container configuration.

## Structure

```
postgres/
├── init/
│   └── 001_init.sql    Runs on first boot (empty data dir) — creates them user/db
└── README.md
```

## Notes

- Data lives in `../data/them-postgres/pgdata/` — survives container rebuilds
- Schema DDL is in `../db/001_schema.sql` (them schema) and `../auth_service/SCHEMA.sql` (auth_service schema)
- `init/` scripts only run when the data directory is **empty** (first boot)
- After first boot, apply schemas manually — see `../db/README.md`
- Never put files directly in `../data/them-postgres/` — Postgres requires the `pgdata/` subdirectory to be clean
