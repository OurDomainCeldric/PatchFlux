# Microsoft 365 Roadmap

The DE/EN `/roadmap` pages use `GET /api/roadmap`. The official RSS adapter
retains only headline, link, date, derived products and the three allowed
development-status categories. Feature descriptions are never persisted.

`RoadmapItems` stores the current snapshot in partition `features`, keyed by a
hash of the canonical feature URL. A metadata fingerprint prevents unchanged
fetches from resetting `ChangedAt`. `FirstSeenAt` survives subsequent changes.
This is a current index, not a full historical event log. Features missing from
a later RSS response remain indexed; absence does not prove cancellation.

Ingestion runs every six hours. An empty index forces a first full fetch rather
than reusing conditional validators from the pre-existing news feed. Subsequent
requests use the existing ETag/Last-Modified logic. Writes use batches of up to
100 entities in the same partition.

Product preference and last successful visit are stored only in browser
localStorage. Changes can only be detected from the creation of this index.
Release-month filtering is not offered because this adapter has no verified
structured release-date field. Unknown statuses remain explicitly unknown.

The public endpoint currently returns the complete metadata index (about 1,900
features at launch); the browser filters it and displays 30 rows at a time.
Consider server pagination if the feed or payload grows substantially.
