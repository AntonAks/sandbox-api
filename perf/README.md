# Perf load-test scripts

`stress_trip_search.py` exercises `POST /trips/search` under increasing concurrency,
reports `time/avg/p95/min/max` per `(total, parallel)` pair.

## Usage

Local:
    just perf-trip-search

Against AWS (auto-resolves IP from terraform state):
    just perf-trip-search-aws

Or manually:
    STRESS_TARGET_URL=http://1.2.3.4 uv run --project app python -m perf.stress_trip_search --env aws

## Bodies

- `bodies/trip_search_heavy.py` — broad filters, matches ~5K trips. Default.
- `bodies/trip_search_light.py` — narrow filters, sanity check.

## Expected baseline (before Bug A fix)

p95 grows visibly with concurrency on a t3.small:

    total/parallel    time   avg   p95   min   max
    10/2              ~1.2s  ~0.4s ~0.8s ~0.3s ~1.1s
    110/22            ~15s   ~1.8s ~3.5s ~0.4s ~5.8s

After the fix (composite index + push filters + selectinload enrichment):

    110/22            ~3s    ~0.1s ~0.05s ~0.02s ~0.2s
