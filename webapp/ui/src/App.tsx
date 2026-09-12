import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, REFERENCE_INPUTS, REFERENCE_UNIT, api } from "./api";
import type { Inputs, LocationResponse, PriceResponse, Unit } from "./types";
import { Results } from "./components/Results";
import { clearSession, loadSession, saveSession } from "./session";
import { PincodeMap } from "./components/PincodeMap";
import { InputsSummary } from "./components/InputsSummary";
import { LocationChip, Shell } from "./components/Shell";
import {
  BandsStep,
  DataStep,
  PayoutsStep,
  PricingStep,
  TariffStep,
  UnitStep,
  YearsStep,
} from "./components/steps";

const EARLIEST_YEAR = 2005;

/** The guided sequence, in the order the decisions are actually made. */
const STEPS = [
  { key: "data", title: "The data" },
  { key: "years", title: "Years to price" },
  { key: "unit", title: "The insured units" },
  { key: "tariff", title: "Tariff" },
  { key: "bands", title: "Payout bands" },
  { key: "payouts", title: "Payouts" },
  { key: "pricing", title: "Pricing" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

type Stage =
  | { name: "entry" }
  | { name: "confirm"; location: LocationResponse }
  | { name: "fetching"; location: LocationResponse; jobId: string }
  | { name: "steps"; location: LocationResponse; step: number }
  | { name: "workspace"; location: LocationResponse };

function useDebounced<T>(value: T, ms: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return settled;
}

function errorText(error: unknown): string | undefined {
  if (!error) return undefined;
  return error instanceof ApiError ? error.message : String(error);
}

const saved = loadSession();

export function App() {
  // A fetch in flight cannot be resumed - job state lives in the server's
  // memory - so that case comes back to the confirmation screen instead.
  const [stage, setStage] = useState<Stage>(() => {
    if (!saved?.location) return { name: "entry" };
    if (saved.stage === "steps")
      return { name: "steps", location: saved.location, step: saved.step };
    if (saved.stage === "workspace") return { name: "workspace", location: saved.location };
    return { name: "confirm", location: saved.location };
  });
  const [pincode, setPincode] = useState(saved?.pincode ?? "380006");
  const [resumed, setResumed] = useState(Boolean(saved?.location));
  // Once the flow has been completed, the steps stop being a corridor:
  // any of them can be opened directly and each hands back to the results.
  const [completed, setCompleted] = useState(saved?.completed ?? false);

  // The contract as the user thinks about it: a unit, a count, and the terms.
  // The engine's flat input contract is derived from these.
  const [unit, setUnit] = useState<Unit>(saved?.unit ?? REFERENCE_UNIT);
  const [units, setUnits] = useState(saved?.units ?? 1);
  const [tariff, setTariff] = useState(saved?.tariff ?? REFERENCE_INPUTS.tariff);
  const [bands, setBands] = useState(
    saved?.bands ?? {
      boundary_sigmas: REFERENCE_INPUTS.boundary_sigmas,
      payout_sigmas: REFERENCE_INPUTS.payout_sigmas,
    },
  );
  const [loadings, setLoadings] = useState(
    saved?.loadings ?? {
      risk_coeff: REFERENCE_INPUTS.risk_coeff,
      expense_pct: REFERENCE_INPUTS.expense_pct,
      profit_pct: REFERENCE_INPUTS.profit_pct,
    },
  );

  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const latestYear = health.data?.latest_complete_year ?? 2024;
  const [range, setRange] = useState<{ start: number; end: number } | null>(
    saved?.years ?? null,
  );
  const years = range ?? { start: EARLIEST_YEAR, end: latestYear };

  const location = "location" in stage ? stage.location : null;

  const inputs: Inputs = useMemo(
    () => ({
      capacity_kw: unit.capacity_kw * units,
      pr: unit.pr,
      aep50: unit.aep50 * units,
      tariff,
      ...bands,
      ...loadings,
    }),
    [unit, units, tariff, bands, loadings],
  );
  const settled = useDebounced(inputs, 150);

  useEffect(() => {
    saveSession({
      pincode,
      location,
      stage:
        stage.name === "steps" || stage.name === "workspace" || stage.name === "confirm"
          ? stage.name
          : "entry",
      step: stage.name === "steps" ? stage.step : 0,
      completed,
      years: range,
      unit,
      units,
      tariff,
      bands,
      loadings,
    });
  }, [pincode, location, stage, range, unit, units, tariff, bands, loadings, completed]);

  const startOver = () => {
    clearSession();
    setRange(null);
    setUnit(REFERENCE_UNIT);
    setUnits(1);
    setTariff(REFERENCE_INPUTS.tariff);
    setBands({
      boundary_sigmas: REFERENCE_INPUTS.boundary_sigmas,
      payout_sigmas: REFERENCE_INPUTS.payout_sigmas,
    });
    setLoadings({
      risk_coeff: REFERENCE_INPUTS.risk_coeff,
      expense_pct: REFERENCE_INPUTS.expense_pct,
      profit_pct: REFERENCE_INPUTS.profit_pct,
    });
    setResumed(false);
    setCompleted(false);
    setStage({ name: "entry" });
  };

  const resolve = useMutation({
    mutationFn: () => api.resolveLocation(pincode),
    onSuccess: (location) => setStage({ name: "confirm", location }),
  });

  const startFetch = useMutation({
    mutationFn: async (location: LocationResponse) => ({
      location,
      data: await api.requestData(location.pincode, EARLIEST_YEAR, latestYear),
    }),
    onSuccess: ({ location, data }) =>
      setStage(
        data.status === "ready"
          ? { name: "steps", location, step: 0 }
          : { name: "fetching", location, jobId: data.job_id! },
      ),
  });

  const pricing = stage.name === "steps" || stage.name === "workspace";

  // Priced from the bands step onward: sigma and the backtest chart are what
  // the band decisions get made against, so they have to be on screen before
  // the bands are chosen.
  const price = useQuery({
    queryKey: ["price", location?.pincode, years.start, years.end, settled],
    queryFn: ({ signal }) =>
      api.price(location!.pincode, years.start, years.end, settled, signal),
    enabled: Boolean(location) && pricing,
    placeholderData: keepPreviousData,
    retry: false,
  });

  const invalid =
    price.error instanceof ApiError && price.error.kind === "invalid_inputs"
      ? price.error.message
      : undefined;

  function renderStep(key: StepKey) {
    switch (key) {
      case "data":
        return <DataStep pincode={location!.pincode} />;
      case "years":
        return (
          <YearsStep
            years={years}
            available={{ first: EARLIEST_YEAR, last: latestYear }}
            latestYear={latestYear}
            onChange={(start, end) => setRange({ start, end })}
          />
        );
      case "unit":
        return <UnitStep unit={unit} units={units} onUnit={setUnit} onUnits={setUnits} />;
      case "tariff":
        return (
          <TariffStep
            tariff={tariff}
            expectedGeneration={unit.aep50 * units}
            onChange={setTariff}
          />
        );
      case "bands":
        return (
          <BandsStep inputs={inputs} result={price.data} onChange={setBands} />
        );
      case "payouts":
        return (
          <PayoutsStep
            inputs={inputs}
            result={price.data}
            onChange={(payout_sigmas) => setBands({ ...bands, payout_sigmas })}
          />
        );
      case "pricing":
        return (
          <PricingStep
            inputs={inputs}
            result={price.data}
            onChange={(patch) => setLoadings({ ...loadings, ...patch })}
          />
        );
    }
  }

  const exportPayload = () => ({
    pincode: location?.pincode,
    start_year: years.start,
    end_year: years.end,
    inputs: settled,
  });

  const download = async (kind: "xlsx" | "report") => {
    const response = await fetch(api.exportUrl(kind), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(exportPayload()),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Export failed" }));
      alert(body.detail);
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `Solar_Parametric_${location?.pincode}.${kind === "xlsx" ? "xlsx" : "pdf"}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Shell
      context={
        location && stage.name !== "entry" ? (
          <LocationChip
            pincode={location.pincode}
            office={location.attributes.Office_Name}
            lat={location.pixel.lat}
            lon={location.pixel.lon}
          />
        ) : null
      }
      actions={
        stage.name === "workspace" || (stage.name === "steps" && completed) ? (
          <>
            <button onClick={() => download("xlsx")}>Workbook</button>
            <button onClick={() => download("report")}>Report</button>
            <button
              onClick={() => {
                setResumed(false);
                setStage({ name: "entry" });
              }}
            >
              New pincode
            </button>
          </>
        ) : null
      }
    >
      {resumed && stage.name !== "entry" && (
        <div className="resume-note">
          <span>
            Picked up where you left off — {pincode}
            {stage.name === "steps" ? `, step ${stage.step + 1}` : ""}. Your inputs were
            remembered.
          </span>
          <button onClick={startOver}>Start fresh</button>
        </div>
      )}
      {stage.name === "entry" && (
        <Entry
          pincode={pincode}
          setPincode={setPincode}
          onSubmit={() => resolve.mutate()}
          pending={resolve.isPending}
          error={resolve.error}
        />
      )}

      {stage.name === "confirm" && (
        <Confirm
          location={stage.location}
          onBack={() => setStage({ name: "entry" })}
          onConfirm={() => startFetch.mutate(stage.location)}
          pending={startFetch.isPending}
          error={startFetch.error}
        />
      )}

      {stage.name === "fetching" && (
        <Fetching
          jobId={stage.jobId}
          onDone={() => setStage({ name: "steps", location: stage.location, step: 0 })}
          onFailed={() => setStage({ name: "entry" })}
        />
      )}

      {stage.name === "steps" && (
        <Wizard
          step={stage.step}
          invalid={invalid}
          completed={completed}
          onStep={(step) => {
            if (step < 0) return setStage({ name: "entry" });
            if (step >= STEPS.length) {
              setCompleted(true);
              return setStage({ name: "workspace", location: stage.location });
            }
            return setStage({ name: "steps", location: stage.location, step });
          }}
          onResults={() => setStage({ name: "workspace", location: stage.location })}
        >
          {renderStep(STEPS[stage.step].key)}
        </Wizard>
      )}

      {stage.name === "workspace" && (
        <Workspace
          years={years}
          inputs={settled}
          invalid={invalid}
          result={price.data}
          stale={price.isFetching || Boolean(invalid)}
          unit={unit}
          units={units}
          onEditStep={(step) => setStage({ name: "steps", location: stage.location, step })}
          onEditAll={() => setStage({ name: "steps", location: stage.location, step: 0 })}
        />
      )}
    </Shell>
  );
}

function Entry({
  pincode,
  setPincode,
  onSubmit,
  pending,
  error,
}: {
  pincode: string;
  setPincode: (value: string) => void;
  onSubmit: () => void;
  pending: boolean;
  error: unknown;
}) {
  return (
    <div className="landing">
      <section className="landing-hero">
        <span className="eyebrow">Parametric weather-index insurance</span>
        <h1>Price a solar generation shortfall cover for any Indian pincode.</h1>
        <p className="hero-lede">
          Twenty years of ERA5-Land irradiance, turned into a tiered contract
          you can see, argue with and export. No site visit, no proof of loss —
          the payout follows a public weather index.
        </p>
        <form
          className="hero-form"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <label className="field-label" htmlFor="pincode">
            Pincode
          </label>
          <div className="hero-entry">
            <input
              id="pincode"
              type="text"
              inputMode="numeric"
              placeholder="380006"
              value={pincode}
              maxLength={6}
              onChange={(event) => setPincode(event.target.value.replace(/\D/g, ""))}
            />
            <button className="primary" type="submit" disabled={pincode.length !== 6 || pending}>
              {pending ? "Looking up…" : "Start pricing"}
            </button>
          </div>
          {error ? <p className="error">{errorText(error)}</p> : null}
        </form>
      </section>

      <section className="how">
        {[
          {
            n: "01",
            title: "Find the cell",
            body: "The pincode boundary gives a centroid, which snaps to the ERA5-Land grid cell that settles every claim.",
          },
          {
            n: "02",
            title: "Pull the record",
            body: "Daily surface solar radiation, one year at a time, cached once so every later change is instant.",
          },
          {
            n: "03",
            title: "Shape the contract",
            body: "Set the units, the tariff, the severity bands and what each pays. The backtest re-runs as you type.",
          },
          {
            n: "04",
            title: "Price and export",
            body: "Burn cost, risk margin and loadings, out to a live-formula workbook or a policy report.",
          },
        ].map((card) => (
          <article key={card.n} className="how-card">
            <span className="how-number">{card.n}</span>
            <h2>{card.title}</h2>
            <p>{card.body}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function Confirm({
  location,
  onBack,
  onConfirm,
  pending,
  error,
}: {
  location: LocationResponse;
  onBack: () => void;
  onConfirm: () => void;
  pending: boolean;
  error: unknown;
}) {
  return (
    <div className="centered">
      <div className="card panel wide">
        <h1>Confirm the location</h1>
        <p className="muted" style={{ marginTop: 6 }}>
          Claims settle on the grid cell's reading, not on the rooftop's own
          output — so it is worth seeing how the two relate before pulling
          twenty years of data.
        </p>
        <PincodeMap location={location} />
        <dl style={{ marginTop: 12 }}>
          <Row label="Pincode" value={location.pincode} />
          {location.attributes.Office_Name && (
            <Row label="Post office" value={location.attributes.Office_Name} />
          )}
          {location.attributes.Division && (
            <Row
              label="Division"
              value={`${location.attributes.Division}, ${location.attributes.Circle ?? ""}`}
            />
          )}
          <Row
            label="Pincode centroid"
            value={`${location.centroid.lat.toFixed(4)}°N, ${location.centroid.lon.toFixed(4)}°E`}
          />
          <Row
            label="ERA5-Land pixel"
            value={`${location.pixel.lat.toFixed(4)}°N, ${location.pixel.lon.toFixed(4)}°E`}
          />
        </dl>
        <div className="button-row">
          <button className="primary" onClick={onConfirm} disabled={pending}>
            {pending ? "Starting…" : "Fetch irradiance data"}
          </button>
          <button onClick={onBack}>Different pincode</button>
        </div>
        {error ? <p className="error">{errorText(error)}</p> : null}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function Fetching({
  jobId,
  onDone,
  onFailed,
}: {
  jobId: string;
  onDone: () => void;
  onFailed: () => void;
}) {
  const done = useRef(false);
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.jobStatus(jobId),
    refetchInterval: (query) =>
      query.state.data?.status === "done" || query.state.data?.status === "error" ? false : 1000,
  });

  useEffect(() => {
    if (job.data?.status === "done" && !done.current) {
      done.current = true;
      onDone();
    }
  }, [job.data?.status, onDone]);

  return (
    <div className="centered">
      <div className="card panel">
        <h1>Fetching irradiance data</h1>
        <p className="muted" style={{ marginTop: 6 }}>
          One year at a time from ERA5-Land. This happens once per pincode —
          afterwards every change is instant.
        </p>
        <progress value={job.data?.progress ?? 0} max={1} style={{ marginTop: 10 }} />
        <p style={{ fontSize: 13 }}>{job.data?.message ?? "Starting…"}</p>
        {job.data?.status === "error" && (
          <>
            <p className="error">{job.data.error}</p>
            <div className="button-row">
              <button onClick={onFailed}>Start over</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Wizard({
  step,
  invalid,
  completed,
  onStep,
  onResults,
  children,
}: {
  step: number;
  invalid?: string;
  completed: boolean;
  onStep: (step: number) => void;
  onResults: () => void;
  children: ReactNode;
}) {
  const current = STEPS[step];
  const last = step === STEPS.length - 1;
  // Before the first run the steps are a sequence, because a later step needs
  // what an earlier one produced. Afterwards every answer exists, so the list
  // becomes plain navigation.
  const reachable = (index: number) => completed || index < step;
  return (
    <div className="wizard">
      <nav className="rail">
        <ol className="stepper">
          {STEPS.map((entry, index) => (
            <li
              key={entry.key}
              className={index === step ? "current" : index < step || completed ? "done" : undefined}
            >
              <button
                onClick={() => reachable(index) && onStep(index)}
                disabled={!reachable(index) && index !== step}
              >
                <span className="step-number">{index + 1}</span>
                {entry.title}
              </button>
            </li>
          ))}
        </ol>
        {completed && (
          <button className="rail-return" onClick={onResults}>
            ← Back to results
          </button>
        )}
      </nav>

      <div className="card step-card">
        <div className="card-head">
          <h1>{current.title}</h1>
          <span className="muted" style={{ fontSize: 12 }}>
            step {step + 1} of {STEPS.length}
          </span>
        </div>
        {children}
        {invalid && <p className="error">{invalid}</p>}
        <div className="button-row step-actions">
          <button onClick={() => onStep(step - 1)} disabled={step === 0 && completed}>
            {step === 0 ? "Change pincode" : "Back"}
          </button>
          <button className="primary" onClick={() => onStep(step + 1)} disabled={Boolean(invalid)}>
            {last ? "See the result" : "Next"}
          </button>
          {completed && !last && (
            <button onClick={onResults} className="ghost">
              Done editing
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Workspace({
  years,
  inputs,
  invalid,
  result,
  stale,
  unit,
  units,
  onEditStep,
  onEditAll,
}: {
  years: { start: number; end: number };
  inputs: Inputs;
  invalid?: string;
  result: PriceResponse | undefined;
  stale: boolean;
  unit: Unit;
  units: number;
  onEditStep: (step: number) => void;
  onEditAll: () => void;
}) {
  return (
    <div className="dashboard">
      <div className="dash-head">
        <div>
          <h1>Solar generation shortfall cover</h1>
          <p className="muted">
            Priced on {years.start}–{years.end}. Every figure below recomputes
            from the inputs — click any of them to change it.
          </p>
        </div>
        <button onClick={onEditAll}>Walk through the inputs</button>
      </div>

      <InputsSummary
        inputs={inputs}
        unit={unit}
        units={units}
        years={years}
        result={result}
        onEdit={onEditStep}
      />

      {invalid && <p className="error">{invalid}</p>}
      {result ? (
        <Results result={result} stale={stale} />
      ) : (
        <div className="card">
          <p className="muted">Pricing…</p>
        </div>
      )}
    </div>
  );
}
