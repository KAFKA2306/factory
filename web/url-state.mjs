export const MAX_COMPARE = 4;

export function readFactoryDbState(search) {
  const params = search instanceof URLSearchParams ? search : new URLSearchParams(search);
  return {
    country: params.get("country") || "",
    process: params.get("process") || "",
    q: params.get("q") || "",
    sort: params.get("sort") || "country",
    compare: (params.get("compare") || "").split(",").filter(Boolean).slice(0, MAX_COMPARE)
  };
}

export function updateFactoryDbSearch(search, state) {
  const params = search instanceof URLSearchParams
    ? new URLSearchParams(search)
    : new URLSearchParams(search);
  const values = {
    country: state.country || "",
    process: state.process || "",
    q: (state.q || "").trim(),
    sort: !state.sort || state.sort === "country" ? "" : state.sort,
    compare: (state.compare || []).slice(0, MAX_COMPARE).join(",")
  };
  Object.entries(values).forEach(([key, value]) => {
    if (value) params.set(key, value);
    else params.delete(key);
  });
  return params.toString();
}
