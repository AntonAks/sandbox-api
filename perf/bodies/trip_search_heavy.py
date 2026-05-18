"""Heavy body: matches ~5K trips, exercises filter + N+1 paths."""

TRIP_SEARCH_HEAVY = {
    "date_from": "2024-01-01",
    "date_to": "2024-06-30",
    "destination_state": "TX",
    "load_status": "DELIVERED",
    "min_distance": 200,
    "max_distance": 1500,
    "limit": 20,
    "offset": 0,
}
