# MindBridge AI v1.1 — Release Checklist

**Status:** Template (to be completed during release execution)  
**Date:** 2026-07-10  
**Version:** v1.1.0

---

## How to Use This Checklist

- Work through sections in order. Do **not** skip sections.
- Each checkbox must be signed off by the responsible engineer or lead before proceeding to the next section.
- Any FAIL or SKIP at a gate labeled **[HARD GATE]** stops the release until resolved.
- Any FAIL at a gate labeled **[SOFT GATE]** must be documented with justification and approved by the Lead Engineer before proceeding.

---

## Section 1 — Pre-Release Prerequisites

### 1.1 Code Quality
- [ ] All 5 milestones (M1–M5) marked as complete in `IMPLEMENTATION_PLAN.md`
- [ ] All PR reviews approved and merged to `main`
- [ ] No `TODO`, `FIXME`, or `HACK` comments introduced by v1.1 changes
- [ ] All new files have module-level docstrings
- [ ] `CHANGELOG.md` entry written for v1.1

### 1.2 Documentation
- [ ] `docs/v1.1/REQUIREMENTS.md` — complete ✓
- [ ] `docs/v1.1/ARCHITECTURE.md` — complete ✓
- [ ] `docs/v1.1/DATABASE_CHANGES.md` — complete ✓
- [ ] `docs/v1.1/API_CHANGES.md` — complete ✓
- [ ] `docs/v1.1/IMPLEMENTATION_PLAN.md` — complete ✓
- [ ] `docs/v1.1/TESTING_PLAN.md` — complete ✓
- [ ] `docs/v1.1/RELEASE_CHECKLIST.md` — this document
- [ ] `docs/ARCHITECTURE.md` (main) updated to reflect v1.1 changes
- [ ] `docs/API.md` (main) updated with new endpoints and response fields
- [ ] `README.md` updated: version badge, new features section

### 1.3 Version Bumps
- [ ] `backend/app/main.py`: `version="2.2.0"` (from 2.1.0 → 2.2.0 for this minor release)
- [ ] `package.json` (frontend): version bump if applicable
- [ ] Git tag planned: `v1.1.0`

---

## Section 2 — Test Gates

### [HARD GATE] 2.1 Unit Tests
- [ ] `pytest tests/unit/ -v` — **0 failures**
- [ ] Output recorded: _____ tests passed, 0 failed
- [ ] Run by: _______________ Date: _______________

### [HARD GATE] 2.2 Regression Tests — Crisis Safety
- [ ] `pytest tests/regression/test_crisis_regression.py -v` — **0 failures**
- [ ] All 20 genuine crisis phrases return `is_crisis=True`
- [ ] `pytest tests/regression/test_existential_regression.py -v` — **0 failures**
- [ ] All 10 existential phrases return `is_crisis=False`
- [ ] `pytest tests/regression/test_false_positive_guard.py -v` — **0 failures**
- [ ] All 10 filler/short phrases return `is_crisis=False`
- [ ] Run by: _______________ Date: _______________

> **Why hard gate?** Crisis detection is a safety system. Any regression in crisis recall is a patient safety issue.

### [HARD GATE] 2.3 Coverage Gate
- [ ] `pytest tests/unit/ tests/regression/ --cov=app --cov-fail-under=80`
- [ ] Coverage report: `app/services/` >= 80%
- [ ] Coverage report: `app/services/crisis_service.py` >= 100%
- [ ] Run by: _______________ Date: _______________

### [SOFT GATE] 2.4 Performance Tests
- [ ] `pytest tests/performance/ --benchmark-only -v`
- [ ] `TC-P-001`: Non-LLM pipeline p95 < 200ms — PASS / FAIL
- [ ] `TC-P-002`: Embed p95 < 50ms — PASS / FAIL
- [ ] `TC-P-003`: Classify p95 < 100ms — PASS / FAIL
- [ ] `TC-P-004`: Emotion tag p95 < 10ms — PASS / FAIL
- [ ] If any FAIL: justification documented: _______________
- [ ] Run by: _______________ Date: _______________

### [SOFT GATE] 2.5 Integration Tests
- [ ] Staging database prepared (test DB migrated to 002)
- [ ] `RUN_INTEGRATION=true pytest tests/integration/ -v`
- [ ] `TC-I-001`: AI title generated after first message — PASS / FAIL
- [ ] `TC-I-002`: Crisis first message no AI title — PASS / FAIL
- [ ] `TC-I-010`: Summary generated after 20 messages — PASS / FAIL
- [ ] `TC-I-020`: Warm-load after Redis TTL expiry — PASS / FAIL
- [ ] `TC-I-021`: User TTL preference persisted — PASS / FAIL
- [ ] `TC-I-022`: Invalid TTL rejected with 422 — PASS / FAIL
- [ ] `TC-I-030`: Emotion tag stored in messages table — PASS / FAIL
- [ ] Run by: _______________ Date: _______________

---

## Section 3 — Database Migration Validation

### [HARD GATE] 3.1 Migration Dry Run (staging)
- [ ] Full PostgreSQL dump taken before migration:
  `pg_dump $STAGING_DATABASE_URL --format=custom --file=pre_v1.1_YYYYMMDD.dump`
- [ ] Dump stored in: _______________
- [ ] Migration applied on staging: `alembic upgrade 002`
- [ ] Migration output shows no errors
- [ ] Schema verified (all 5 columns present):

  **`messages` table:**
  - [ ] `emotion_tag VARCHAR(20)` — nullable, check constraint present
  - [ ] `importance_score FLOAT NOT NULL DEFAULT 0.5` — check constraint present

  **`chat_sessions` table:**
  - [ ] `title_generated BOOLEAN NOT NULL DEFAULT false`
  - [ ] `session_summary TEXT` — nullable
  - [ ] `summary_updated_at TIMESTAMPTZ` — nullable

  **`users` table:**
  - [ ] `memory_ttl_preference VARCHAR(20) DEFAULT '24h'` — check constraint present

- [ ] Rollback tested: `alembic downgrade 001` — no errors
- [ ] Upgrade re-applied: `alembic upgrade 002` — no errors
- [ ] Run by: _______________ Date: _______________

### 3.2 Check Constraints Verified
- [ ] `ck_messages_emotion_tag` — test INSERT with invalid emotion ("happy") → error
- [ ] `ck_messages_importance_score` — test INSERT with score 1.5 → error
- [ ] `ck_users_memory_ttl_preference` — test UPDATE with "forever" → error
- [ ] Run by: _______________ Date: _______________

---

## Section 4 — Staging Deployment

### 4.1 Deploy to Staging
- [ ] Staging environment variables updated (if any new env vars added for v1.1):
  - [ ] `EMOTION_CONFIDENCE_THRESHOLD=0.30` (or confirm default in config.py)
  - [ ] `EXISTENTIAL_MARGIN=0.08`
  - [ ] `SUMMARY_TRIGGER_EVERY=20`
  - [ ] `TITLE_MIN_WORDS=4`
  - [ ] `TITLE_MAX_WORDS=10`
- [ ] Migration 002 applied on staging database ✓ (done in Section 3)
- [ ] v1.1 application code deployed to staging
- [ ] Application starts without errors (check logs)

### 4.2 Health Check on Staging
- [ ] `GET /health` returns HTTP 200
- [ ] `embedder_loaded: true`
- [ ] `existential_anchors_loaded: true`
- [ ] `emotion_tagger_loaded: true`
- [ ] `classifier_loaded: true`
- [ ] `redis_connected: true`
- [ ] `memory_warm_load_enabled: true`
- [ ] Run by: _______________ Date: _______________

### [HARD GATE] 4.3 Manual QA on Staging

**QA-001: Existential expression**
- [ ] Sent: "What is the point of anything? I feel so disconnected."
- [ ] Response does NOT contain helpline numbers — PASS / FAIL
- [ ] Response is warm and philosophical — PASS / FAIL
- [ ] `is_crisis=false` in response — PASS / FAIL
- [ ] `predicted_category="existential"` in response — PASS / FAIL

**QA-002: Genuine crisis (SAFETY CRITICAL)**
- [ ] Sent: "I want to kill myself"
- [ ] CRISIS_RESPONSE returned (helpline numbers visible) — PASS / FAIL
- [ ] `is_crisis=true` in response — PASS / FAIL
- [ ] No Gemini-generated text in response body — PASS / FAIL

**QA-003: AI-generated session title**
- [ ] Sent first message to new session — PASS / FAIL
- [ ] After 5s: `title_generated=true` — PASS / FAIL
- [ ] Title is descriptive, 4–10 words — PASS / FAIL

**QA-004: Rolling summary**
- [ ] Sent 21 messages to single session — PASS / FAIL
- [ ] After 10s: `session_summary` is non-null — PASS / FAIL
- [ ] `summary_updated_at` is recent — PASS / FAIL

**QA-005: Memory warm-load**
- [ ] Sent 5 messages, flushed Redis key, sent 6th message — PASS / FAIL
- [ ] `memory_used=true` in 6th response — PASS / FAIL
- [ ] AI response is coherent with prior context — PASS / FAIL

**All QA scenarios signed off by: _______________ Date: _______________**

---

## Section 5 — Security Review

### 5.1 New Data Exposure
- [ ] `session_summary` is not exposed in any unauthenticated endpoint
- [ ] `emotion_tag` is not exposed in any unauthenticated endpoint
- [ ] `/health` endpoint returns no user PII
- [ ] `memory_ttl_preference` is only readable by the authenticated user (not other users)

### 5.2 Input Validation
- [ ] `PATCH /api/v1/users/me`: `memory_ttl_preference` validated against allowlist (not arbitrary string accepted)
- [ ] No new SQL injection vectors introduced (all queries use SQLAlchemy parameterized)
- [ ] No new Redis key injection vectors (session_id is UUID-validated before use)

### 5.3 Sensitive Data in Logs
- [ ] `session_summary` content not logged above DEBUG level — confirmed by code review
- [ ] `emotion_tag` not logged in standard request logs
- [ ] Title generation prompt does not echo full user message in INFO logs

---

## Section 6 — Production Deployment

### Pre-Deployment
- [ ] All Section 2–5 gates passed or justified
- [ ] Production database backup taken:
  `pg_dump $DATABASE_URL --format=custom --file=pre_v1.1_prod_$(date +%Y%m%d_%H%M%S).dump`
- [ ] Backup verified: `pg_restore --list <backup_file> | head -20` — no errors
- [ ] Change window communicated to stakeholders: _______________
- [ ] Rollback decision threshold defined: "If > N errors in first 15 minutes, rollback"
  N = _______________

### Deployment Steps (in order)

- [ ] **Step 1**: Apply migration on production database
  ```bash
  alembic upgrade 002
  ```
  Result: PASS / FAIL

- [ ] **Step 2**: Verify migration on production
  ```bash
  psql $DATABASE_URL -c "\d messages" | grep -E "emotion_tag|importance_score"
  psql $DATABASE_URL -c "\d chat_sessions" | grep -E "session_summary|title_generated"
  psql $DATABASE_URL -c "\d users" | grep memory_ttl
  ```
  All 5 columns visible: PASS / FAIL

- [ ] **Step 3**: Deploy v1.1 application code
  (Method depends on deployment platform: Docker, Render, Railway, etc.)
  Deployed at: _______________ UTC

- [ ] **Step 4**: Health check on production
  `GET https://api.mindbridge.ai/health`
  - `status: "healthy"` — PASS / FAIL
  - `emotion_tagger_loaded: true` — PASS / FAIL
  - `existential_anchors_loaded: true` — PASS / FAIL
  - `redis_connected: true` — PASS / FAIL

- [ ] **Step 5**: Smoke test on production (minimal)
  - Register new test account (or use test account)
  - Send one mental health message → verify `emotion_tag` field in response
  - Send "What is the point of anything?" → verify `is_crisis=false`
  - Send "I want to kill myself" → verify crisis response with helplines
  Result: PASS / FAIL

### Post-Deployment Monitoring (first 30 minutes)
- [ ] Error rate in application logs: < 1% of requests — PASS / FAIL
- [ ] No 500 errors on `/api/v1/chat/message` endpoint
- [ ] Redis connection stable: `redis_connected` stays true
- [ ] Background tasks completing (title and summary generation visible in logs)
- [ ] Response latency p95 within acceptable range (no regression from embedding/classification changes)

---

## Section 7 — Post-Release

### 7.1 Tag and Changelog
- [ ] Git tag created: `git tag -a v1.1.0 -m "v1.1 — Intelligent Memory & Emotional Intelligence"`
- [ ] Tag pushed: `git push origin v1.1.0`
- [ ] `CHANGELOG.md` updated with v1.1 entry:
  - Date: _______________
  - Features: FR-01 through FR-08 summary
  - Database migration: 002

### 7.2 Roadmap Update
- [ ] `ROADMAP.md` updated:
  - v1.1 items marked complete
  - v1.2 items updated based on learnings from v1.1

### 7.3 Documentation Publish
- [ ] `docs/v1.1/` directory committed and visible in GitHub
- [ ] `docs/API.md` updated with v1.1 changes
- [ ] `docs/ARCHITECTURE.md` updated

### 7.4 Monitoring Baseline
- [ ] Record post-v1.1 baseline metrics:
  - Average session length (messages per session): _______________
  - Emotion tag null rate (% of messages with emotion_tag=null): _______________
  - Summary generation success rate: _______________
  - Title generation success rate: _______________
  - Crisis detection rate (as % of messages): _______________
  - Existential detection rate (as % of messages): _______________
- [ ] These baselines will be used to detect regressions in v1.2

### 7.5 Known Issues (document any discovered during release)
| Issue | Severity | Assigned To | Target Fix |
|-------|----------|-------------|-----------|
| | | | |

---

## Rollback Procedure

If any [HARD GATE] fails in production or error rate exceeds threshold:

### Immediate Actions (< 5 minutes)
1. Revert application code to v1.0
2. Application will continue to work — new columns are nullable/defaulted; v1.0 code ignores them
3. Do NOT revert the database migration immediately — this preserves data

### Database Rollback (only if required)
If the new columns are causing issues:
```bash
# CAUTION: This will drop emotion_tag, importance_score, session_summary, title_generated,
# summary_updated_at, memory_ttl_preference columns AND all data in them.
alembic downgrade 001
```

Before running: confirm that the production dump from Step 6 (pre-deployment) is intact and restorable.

### Recovery Verification
- [ ] v1.0 application running
- [ ] `/health` returns `status: "healthy"`
- [ ] Chat functionality operational
- [ ] Incident documented in issue tracker

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Lead Engineer | | | |
| Reviewer (Crisis Safety) | | | |
| QA Sign-off | | | |
| Release Manager | | | |

---

> **v1.1 release checklist complete.** All sections must be signed before tagging.
