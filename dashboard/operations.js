/* Derived operations view over Central's canonical records.
 *
 * This module is intentionally pure: it reads plain arrays and returns a
 * summary. It never writes, closes, verifies, or promotes a record. The browser
 * loads it as window.CentralOperations; Node tests load it through CommonJS.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.CentralOperations = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var UNRESOLVED_THREAD_STATUS = ["open", "active", "decision_pending"];
  var VERIFIED_REVIEW_RESULTS = ["pass", "approved", "verified"];
  var STALE_WORK_STATUS = ["proposed", "ready", "active", "blocked"];

  function ageDays(value, nowMs) {
    var date = new Date(value);
    if (isNaN(date.getTime())) return null;
    return Math.floor((nowMs - date.getTime()) / 86400000);
  }

  function toMillis(value) {
    if (value instanceof Date) return value.getTime();
    if (typeof value === "number" && isFinite(value)) return value;
    return Date.now();
  }

  function summarize(data, options) {
    data = data || {};
    options = options || {};
    var now = toMillis(options.now);
    var maxAgeDays = typeof options.maxAgeDays === "number" ? options.maxAgeDays : 30;
    var staleDays = typeof options.staleDays === "number" ? options.staleDays : 14;

    var messages = data.messages || [];
    var threads = data.threads || [];
    var work = data.work || [];
    var reviews = data.reviews || [];
    var decisions = data.decisions || [];
    var legacy = data.legacy || [];

    var messageIds = {};
    messages.forEach(function (message) {
      if (message && message.message_id) messageIds[message.message_id] = true;
    });
    var threadIds = {};
    threads.forEach(function (thread) {
      if (thread && thread.thread_id) threadIds[thread.thread_id] = true;
    });

    var reviewResults = {};
    reviews.forEach(function (review) {
      if (!review || !review.work_id) return;
      if (!reviewResults[review.work_id]) reviewResults[review.work_id] = [];
      reviewResults[review.work_id].push(review.result);
    });

    var awaiting = [];
    var verifiedWithoutReview = [];
    var stale = [];
    work.forEach(function (item) {
      if (!item) return;
      var verification = item.verification || {};
      if (item.status === "implemented" && verification.status !== "verified") {
        awaiting.push(item);
      }
      if (item.status === "verified") {
        var results = reviewResults[item.id] || [];
        var hasVerifiedReview = results.some(function (result) {
          return VERIFIED_REVIEW_RESULTS.indexOf(result) !== -1;
        });
        if (!hasVerifiedReview) verifiedWithoutReview.push(item);
      }
      if (STALE_WORK_STATUS.indexOf(item.status) !== -1) {
        var idle = ageDays(item.updated_at, now);
        if (idle !== null && idle > staleDays) {
          stale.push({
            id: item.id,
            title: item.title,
            status: item.status,
            owner: item.owner,
            updated_at: item.updated_at,
            idleDays: idle
          });
        }
      }
    });
    stale.sort(function (a, b) { return b.idleDays - a.idleDays; });

    var unresolved = threads.filter(function (thread) {
      return thread && UNRESOLVED_THREAD_STATUS.indexOf(thread.status) !== -1;
    });
    var aging = [];
    unresolved.forEach(function (thread) {
      var age = ageDays(thread.created_at, now);
      if (age !== null && age > maxAgeDays) {
        aging.push({
          thread_id: thread.thread_id,
          title: thread.title,
          status: thread.status,
          created_at: thread.created_at,
          ageDays: age
        });
      }
    });
    aging.sort(function (a, b) { return b.ageDays - a.ageDays; });

    var decisionsWithoutWork = decisions.filter(function (decision) {
      return !decision || !Array.isArray(decision.related_work_ids) || decision.related_work_ids.length === 0;
    });

    var unknownMessage = [];
    threads.forEach(function (thread) {
      (thread.message_ids || []).forEach(function (messageId) {
        if (!messageIds[messageId]) unknownMessage.push(messageId);
      });
    });
    var unknownThread = messages.filter(function (message) {
      return !message || !threadIds[message.thread_id];
    });

    var mappedThreads = {};
    legacy.forEach(function (mapping) {
      if (mapping && mapping.thread_id) mappedThreads[mapping.thread_id] = true;
    });
    var emptyThreads = threads.filter(function (thread) {
      return thread && Array.isArray(thread.message_ids) && thread.message_ids.length === 0;
    });
    var emptyWithoutEvidence = emptyThreads.filter(function (thread) {
      return !mappedThreads[thread.thread_id];
    }).map(function (thread) {
      return thread.thread_id;
    });

    var broken = unknownMessage.length > 0 || unknownThread.length > 0;
    var attention = awaiting.length > 0 || verifiedWithoutReview.length > 0 ||
      aging.length > 0 || stale.length > 0 || decisionsWithoutWork.length > 0 ||
      emptyWithoutEvidence.length > 0;
    var status = broken ? "invalid" : attention ? "attention" : "healthy";

    return {
      status: status,
      awaiting: awaiting,
      verifiedWithoutReview: verifiedWithoutReview,
      stale: stale,
      unresolved: unresolved,
      aging: aging,
      decisionsWithoutWork: decisionsWithoutWork,
      unknownMessage: unknownMessage,
      unknownThread: unknownThread,
      emptyThreads: emptyThreads,
      emptyWithoutEvidence: emptyWithoutEvidence,
      legacyMapped: emptyThreads.length - emptyWithoutEvidence.length,
      staleDays: staleDays,
      maxAgeDays: maxAgeDays
    };
  }

  return {
    summarize: summarize,
    ageDays: ageDays,
    UNRESOLVED_THREAD_STATUS: UNRESOLVED_THREAD_STATUS
  };
});
