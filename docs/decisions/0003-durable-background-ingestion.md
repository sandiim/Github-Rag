# Durable background ingestion

## Decision

Repository imports and rebuilds are PostgreSQL-backed jobs processed by a separate single-concurrency Python worker. HTTP returns 202 after enqueueing. A partial unique index prevents multiple active jobs per repository; leases and one automatic recovery attempt handle worker termination. The UI polls for progress and exposes manual retry after failure.

## Rationale and tradeoffs

Real repositories can require many GitHub blob requests and Ollama embedding calls, so synchronous HTTP made the form appear frozen or time out. PostgreSQL is already required and avoids adding Redis/Celery for this single-user app. A separate worker terminal is now mandatory; without it jobs remain queued. Polling is simple but adds periodic reads. The worker still uses one GitHub REST request per selected blob, so API quotas remain a limit. Full replacement indexes require more time and storage but preserve the previous active index on failure.
