# odin-postgres

Source folder for the Odin PostgreSQL container.

## Structure

```
postgres/
├── init/           SQL files auto-run by Postgres on first boot (empty data dir)
│   └── 001_init.sql
└── README.md
```

## Notes
- Data lives in `../volumes/postgres/pgdata/` — survives rebuilds
- Schema DDL is in `../db/001_schema.sql` (odin) and `../auth_service/SCHEMA.sql` (auth_service)
- To apply schemas to a running container: `bash scripts/init_db.sh`
- Init scripts in `init/` only run when the data directory is empty (first boot)
