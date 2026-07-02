# odin-redis

Source folder for the Odin Redis container.

## Structure

```
redis/
├── config/
│   └── redis.conf      Redis configuration (AOF persistence, memory limits)
└── README.md
```

## Notes
- Data lives in `../volumes/redis/` — survives rebuilds
- DB index 0 (Odin owns this Redis entirely)
- Key prefix rules: all keys start with `odin:` or `rl:odin:`
- See `../docs/REDIS.md` for full key space reference
