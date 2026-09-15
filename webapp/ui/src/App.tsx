import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, POLICY, api } from "./api";
import type { LocationResponse, PriceResponse } from "./types";
import { Footer, Header } from "./components/Shell";
import { InputPage } from "./components/InputPage";
import { PolicyPage } from "./components/PolicyPage";

// One input, one output. A visitor gives a pincode; everything else - the
// unit, the tariff, the bands, the loadings - is the submitted contract,
// held fixed, so the only thing that varies on screen is the location.

export type Status =
  | { name: "idle" }
  | { name: "working"; step: 0 | 1 | 2; progress: number; message: string }
  | { name: "error"; message: string; retryable: boolean }
  | { name: "ready"; location: LocationResponse; result: PriceResponse };

function describe(error: unknown, pincode: string): string {
  if (!(error instanceof ApiError)) return "Something went wrong. Please try again.";
  switch (error.kind) {
    case "pincode_not_found":
      return `Pincode ${pincode} isn't in the India Post boundary set. Check the six digits.`;
    case "upstream_error":
      // ERA5-Land is land-only: a pincode whose centre falls on a sea cell
      // has no reading at all, which retrying will not change.
      if (error.message.includes("no ERA5-Land cell"))
        return `Pincode ${pincode} is on the coast, where the weather grid has no land reading. Try a nearby inland pincode.`;
      return "A data provider didn't answer. Please try again in a moment.";
    case "job_not_found":
      return "The server restarted while the data was downloading. Please try again.";
    default:
      return error.message;
  }
}

/** Locate, fetch, price - each step starts when the one before it lands. */
function usePolicy(pincode: string | null): Status {
  const located = useQuery({
    queryKey: ["location", pincode],
    queryFn: () => api.resolveLocation(pincode!),
    enabled: Boolean(pincode),
  });
  const data = useQuery({
    queryKey: ["data", pincode],
    queryFn: () => api.requestData(pincode!, POLICY.startYear, POLICY.endYear),
    enabled: located.isSuccess,
  });
  const jobId = data.data?.status === "fetching" ? data.data.job_id : null;
  const job = useQuery({
    queryKey: ["job", pincode, jobId],
    queryFn: () => api.jobStatus(jobId!),
    enabled: Boolean(jobId),
    // The pull takes a minute; a visitor who switches tabs meanwhile should
    // come back to a priced policy, not a stalled bar.
    refetchIntervalInBackground: true,
    refetchInterval: (query) =>
      query.state.data?.status === "done" || query.state.data?.status === "error" ? false : 1000,
  });
  const fetched = data.data?.status === "ready" || job.data?.status === "done";
  const priced = useQuery({
    queryKey: ["price", pincode],
    queryFn: ({ signal }) =>
      api.price(pincode!, POLICY.startYear, POLICY.endYear, POLICY.inputs, signal),
    enabled: fetched,
  });

  if (!pincode) return { name: "idle" };
  const failure = located.error ?? data.error ?? job.error ?? priced.error;
  if (failure)
    return {
      name: "error",
      message: describe(failure, pincode),
      retryable: !(
        failure instanceof ApiError &&
        (failure.kind === "pincode_not_found" || failure.message.includes("no ERA5-Land cell"))
      ),
    };
  if (job.data?.status === "error")
    return {
      name: "error",
      message: job.data.error ?? "The irradiance download failed.",
      retryable: true,
    };
  if (located.data && priced.data)
    return { name: "ready", location: located.data, result: priced.data };
  if (!located.data)
    return { name: "working", step: 0, progress: 0, message: `Locating pincode ${pincode}` };
  if (!fetched)
    return {
      name: "working",
      step: 1,
      progress: job.data?.progress ?? 0,
      message: job.data?.message ?? "Requesting twenty years of daily irradiance",
    };
  return { name: "working", step: 2, progress: 1, message: "Pricing the policy" };
}

function pincodeFromUrl(): string | null {
  const value = new URLSearchParams(window.location.search).get("pincode");
  return value && /^\d{6}$/.test(value) ? value : null;
}

// Two pages, told apart by the address alone: "/" takes the pincode, and
// "/?pincode=380006" is that pincode's policy - so a policy link can be shared
// and the browser's back button returns to the input page.
export function App() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState<string | null>(pincodeFromUrl);
  const [draft, setDraft] = useState(() => pincodeFromUrl() ?? "");
  const [active, setActive] = useState<string | null>(pincodeFromUrl);
  const status = usePolicy(active);

  const go = (pincode: string | null) => {
    window.history.pushState(null, "", pincode ? `?pincode=${pincode}` : "./");
    setPage(pincode);
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    const onPop = () => {
      const pincode = pincodeFromUrl();
      setPage(pincode);
      if (pincode) {
        setActive(pincode);
        setDraft(pincode);
      }
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // A pincode submitted on the input page is priced there, with progress in
  // view, and the visitor moves to the policy page once it is ready.
  const awaiting = useRef<string | null>(null);
  useEffect(() => {
    if (status.name === "ready" && awaiting.current === active && page === null) {
      awaiting.current = null;
      go(active);
    }
  }, [status.name, active, page]);

  const submit = (pincode: string) => {
    setDraft(pincode);
    awaiting.current = pincode;
    if (pincode !== active) return setActive(pincode);
    if (status.name === "ready") {
      awaiting.current = null;
      go(pincode);
    } else if (status.name === "error") {
      queryClient.resetQueries({ predicate: (query) => query.queryKey[1] === pincode });
    }
  };

  return (
    <div className={page ? "page" : "page page-input"}>
      <Header page={page ? "policy" : "input"} onHome={() => go(null)} />
      <main className="container">
        {page ? (
          <PolicyPage pincode={page} status={status} onBack={() => go(null)} />
        ) : (
          <InputPage
            draft={draft}
            onDraft={setDraft}
            onSubmit={submit}
            status={status}
            active={active}
          />
        )}
      </main>
      <Footer />
    </div>
  );
}
