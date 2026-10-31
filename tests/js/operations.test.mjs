import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const operations = require("../../dashboard/operations.js");

const NOW = Date.parse("2026-01-15T00:00:00Z");

function base() {
  return {
    threads: [{
      thread_id: "thread:one",
      title: "Thread",
      status: "open",
      created_at: "2026-01-10T00:00:00Z",
      message_ids: ["msg:one"],
    }],
    messages: [{ message_id: "msg:one", thread_id: "thread:one" }],
    work: [{
      id: "work:one",
      title: "Work",
      status: "active",
      owner: "agent",
      updated_at: "2026-01-10T00:00:00Z",
      verification: { status: "pending" },
    }],
    reviews: [],
    decisions: [{ id: "dec:one", related_work_ids: ["work:one"] }],
    legacy: [],
  };
}

test("recent coordinated records are healthy", () => {
  const report = operations.summarize(base(), { now: NOW });
  assert.equal(report.status, "healthy");
  assert.deepEqual(report.awaiting, []);
  assert.deepEqual(report.stale, []);
});

test("implemented work awaits verification", () => {
  const data = base();
  data.work[0].status = "implemented";
  const report = operations.summarize(data, { now: NOW });
  assert.equal(report.status, "attention");
  assert.deepEqual(report.awaiting.map((item) => item.id), ["work:one"]);
});

test("verified work without a verifying review is flagged", () => {
  const data = base();
  data.work[0].status = "verified";
  data.work[0].verification = { status: "verified" };
  data.reviews = [{ work_id: "work:one", result: "pending" }];
  const report = operations.summarize(data, { now: NOW });
  assert.deepEqual(report.verifiedWithoutReview.map((item) => item.id), ["work:one"]);
});

test("stale open work is derived from updated_at", () => {
  const data = base();
  data.work[0].updated_at = "2025-12-01T00:00:00Z";
  const report = operations.summarize(data, { now: NOW, staleDays: 14 });
  assert.equal(report.status, "attention");
  assert.equal(report.stale[0].id, "work:one");
  assert.ok(report.stale[0].idleDays > 14);
});

test("aging unresolved threads are derived from created_at", () => {
  const data = base();
  data.threads[0].created_at = "2025-11-01T00:00:00Z";
  const report = operations.summarize(data, { now: NOW, maxAgeDays: 30 });
  assert.equal(report.aging[0].thread_id, "thread:one");
  assert.ok(report.aging[0].ageDays > 30);
});

test("decisions without related work are flagged", () => {
  const data = base();
  data.decisions[0].related_work_ids = [];
  const report = operations.summarize(data, { now: NOW });
  assert.deepEqual(report.decisionsWithoutWork.map((item) => item.id), ["dec:one"]);
});

test("broken thread or message references make the report invalid", () => {
  const data = base();
  data.threads[0].message_ids = ["msg:missing"];
  let report = operations.summarize(data, { now: NOW });
  assert.equal(report.status, "invalid");
  assert.deepEqual(report.unknownMessage, ["msg:missing"]);

  const other = base();
  other.messages[0].thread_id = "thread:missing";
  report = operations.summarize(other, { now: NOW });
  assert.equal(report.status, "invalid");
  assert.equal(report.unknownThread.length, 1);
});

test("legacy-mapped empty threads are distinguished from unexplained gaps", () => {
  const data = base();
  data.messages = [];
  data.threads[0].message_ids = [];
  let report = operations.summarize(data, { now: NOW });
  assert.equal(report.status, "attention");
  assert.deepEqual(report.emptyWithoutEvidence, ["thread:one"]);

  data.legacy = [{ id: "LTM-001", thread_id: "thread:one", legacy_index: 0 }];
  report = operations.summarize(data, { now: NOW });
  assert.equal(report.status, "healthy");
  assert.equal(report.legacyMapped, 1);
  assert.deepEqual(report.emptyWithoutEvidence, []);
});

test("missing timestamps do not manufacture staleness", () => {
  const data = base();
  delete data.work[0].updated_at;
  const report = operations.summarize(data, { now: NOW });
  assert.deepEqual(report.stale, []);
  assert.equal(operations.ageDays("not-a-date", NOW), null);
});
