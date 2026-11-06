# Postgres

*Both installs*

**Why I picked it.** The standard choice: it's Django's best-supported database.

**What it is.** The database. The permanent record of everything that happened.

**How we use it.** One write per completed set, not one per rep — the tablet holds
reps until the set ends, then posts the batch:

```
rack screen ──whole set──► django ──one transaction──► postgres
```

Django owns the schema; nobody writes SQL by hand.

**Where it lives.** **Local:** container `edgeathlete-postgres`, image `postgres:15`, data in the `postgres_data` volume, not exposed outside the Compose network. **Remote:** **one shared Postgres 15.18** in the `edge-athlete` namespace, with **a database per school** and a login that can open only that one ({doc}`../core/remote/databases`).

**Worth knowing.** ⚠️ `docker compose down -v` and `ea-reset-hard` delete that
volume. That is the only way to lose a season of training, and it takes the NFC
wristband assignments with it — the seeder does not set those.

**More:** {doc}`../../handbook/reference/database-tables` for what the tables mean and why, with a plain-English tour at the top · {doc}`../../handbook/guides/database-changes`
