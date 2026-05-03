// Mirror of pathwise/core/predicate.py. Evaluates `when` clauses on
// steps and questions client-side so the UI hides/shows in real time as
// answers come in.
//
// Atom: { field: primitive } or { field: { $eq|$ne|$gt|$gte|$lt|$lte|$in|$nin: ... } }
// Combinators: { $all: [...] }, { $any: [...] }, { $not: <pred> }

const predicate = (() => {
  const COMPARISON_OPS = new Set(["$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin", "$contains"]);
  const COMBINATORS = new Set(["$all", "$any", "$not"]);

  function evaluate(pred, answers) {
    if (pred === null || pred === undefined) return true;
    if (typeof pred !== "object") {
      throw new Error("predicate must be an object");
    }
    if (Object.keys(pred).length === 0) return true;

    for (const [key, value] of Object.entries(pred)) {
      if (key === "$all") {
        if (!value.every(sub => evaluate(sub, answers))) return false;
      } else if (key === "$any") {
        if (!value.some(sub => evaluate(sub, answers))) return false;
      } else if (key === "$not") {
        if (evaluate(value, answers)) return false;
      } else if (key.startsWith("$")) {
        throw new Error(`unknown combinator ${key}`);
      } else {
        if (!evalField(key, value, answers)) return false;
      }
    }
    return true;
  }

  function evalField(field, clause, answers) {
    const actual = answers[field];
    if (clause !== null && typeof clause === "object" && !Array.isArray(clause)) {
      for (const [op, expected] of Object.entries(clause)) {
        if (!COMPARISON_OPS.has(op)) {
          throw new Error(`unknown op ${op} on ${field}`);
        }
        if (!evalOp(op, actual, expected)) return false;
      }
      return true;
    }
    return actual === clause;
  }

  function evalOp(op, actual, expected) {
    switch (op) {
      case "$eq":  return actual === expected;
      case "$ne":  return actual !== expected;
      case "$in":  return expected.includes(actual);
      case "$nin": return !expected.includes(actual);
      case "$contains":
        // For multi_choice / string_set answers (actual is an array).
        if (Array.isArray(actual)) return actual.includes(expected);
        return actual === expected;
    }
    if (actual === null || actual === undefined || expected === null) return false;
    switch (op) {
      case "$gt":  return actual > expected;
      case "$gte": return actual >= expected;
      case "$lt":  return actual < expected;
      case "$lte": return actual <= expected;
    }
    throw new Error(`unknown op ${op}`);
  }

  return { evaluate };
})();
