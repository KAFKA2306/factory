import assert from "node:assert/strict";
import test from "node:test";

import {MAX_COMPARE, readFactoryDbState, updateFactoryDbSearch} from "../web/url-state.mjs";

test("filter and comparison state round-trips through the URL", () => {
  const search = updateFactoryDbSearch("", {
    country: "JP",
    process: "assembly",
    q: "Toyota",
    sort: "name",
    compare: ["facility:a", "facility:b"]
  });
  assert.deepEqual(readFactoryDbState(search), {
    country: "JP",
    process: "assembly",
    q: "Toyota",
    sort: "name",
    compare: ["facility:a", "facility:b"]
  });
});

test("unrelated referral parameters survive state updates", () => {
  const search = updateFactoryDbSearch("utm_source=industry-note", {
    country: "US",
    process: "",
    q: "battery",
    sort: "country",
    compare: []
  });
  const params = new URLSearchParams(search);
  assert.equal(params.get("utm_source"), "industry-note");
  assert.equal(params.get("country"), "US");
  assert.equal(params.get("q"), "battery");
  assert.equal(params.has("sort"), false);
});

test("comparison URL state is bounded to the public UI limit", () => {
  const ids = Array.from({length: MAX_COMPARE + 2}, (_, index) => `facility:${index}`);
  const search = updateFactoryDbSearch("", {compare: ids});
  assert.equal(readFactoryDbState(search).compare.length, MAX_COMPARE);
});
