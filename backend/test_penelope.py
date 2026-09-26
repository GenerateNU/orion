from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone

from penelope.client import PenelopeClient

client = PenelopeClient.from_env()

# Test 1: confirm get_by_time_bounds returns a numpy array now
start = datetime(2026, 8, 15, 21, 55, tzinfo=timezone.utc)
end = datetime(2026, 8, 15, 22, 55, tzinfo=timezone.utc)

result = client.get_by_time_bounds(start, end)
print(type(result))
print(result.shape)
print(result[0])

# Test 2: confirm pagination works without timing out
print("\n--- testing get_all_paginated ---")
total = 0
for i, batch in enumerate(client.get_all_paginated(batch_size=5000)):
    total += len(batch)
    if i == 0:
        print("first batch shape:", batch.shape)
        print("first row:", batch[0])
    if i >= 4:  # just check the first 5 batches, don't run all 656M rows
        print(f"stopped early after {i+1} batches, {total} rows so far")
        break