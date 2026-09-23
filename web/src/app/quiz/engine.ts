/* The matching algorithm, ported line-for-line from the Python reference in
   src/dinoclub/quiz/scoring.py.

   Why a port and not an API: a club website should be a static page that
   works forever on free hosting. A second server to keep alive is the part
   that quietly dies in a year. The Python package stays the reference
   implementation and the audit tool; this file ships. The two read the same
   JSON data files, and engine.spec.ts checks this port against a fixture the
   Python side generated, so they cannot drift without a test going red.

   Steps:
     1. accumulate -- sum the effects of every option picked
     2. calibrate  -- rescale each axis so user spread matches dinosaur spread
     3. measure    -- Euclidean distance to every dinosaur
     4. rank       -- nearest wins; softmax over distance for confidence */

export interface Trait {
  key: string;
  name: string;
  negative: string;
  positive: string;
  question?: string;
}

export interface TraitSpaceData {
  scale: { min: number; max: number };
  traits: Trait[];
}

export interface Dinosaur {
  id: string;
  name: string;
  tagline: string;
  blurb: string;
  traits: Record<string, number>;
}

export interface Option {
  id: string;
  text: string;
  effects: Record<string, number>;
}

export interface Question {
  id: string;
  text: string;
  options: Option[];
}

export type Vector = Record<string, number>;
export type Answer = readonly [questionId: string, optionId: string];

export interface Match {
  dinosaur: Dinosaur;
  distance: number;
  matchPercent: number;
  confidence: number;
}

export interface Result {
  winner: Dinosaur;
  runnerUp: Match | null;
  profile: Vector;
  rawTotals: Vector;
  matches: Match[];
  summary: string[];
}

/* Same constants as the Python side. */
export const DEFAULT_TEMPERATURE = 2.6;
export const DEFAULT_SPREAD = 1.0;

export class Engine {
  readonly keys: string[];
  readonly min: number;
  readonly max: number;

  private readonly byQuestion = new Map<string, Question>();
  private readonly byDinosaur = new Map<string, Dinosaur>();

  constructor(
    readonly space: TraitSpaceData,
    readonly dinosaurs: Dinosaur[],
    readonly questions: Question[],
  ) {
    this.keys = space.traits.map((t) => t.key);
    this.min = space.scale.min;
    this.max = space.scale.max;
    for (const q of questions) this.byQuestion.set(q.id, q);
    for (const d of dinosaurs) this.byDinosaur.set(d.id, d);
  }

  question(id: string): Question {
    const q = this.byQuestion.get(id);
    if (!q) throw new Error(`no question ${id}`);
    return q;
  }

  option(questionId: string, optionId: string): Option {
    const o = this.question(questionId).options.find((x) => x.id === optionId);
    if (!o) throw new Error(`no option ${optionId} on question ${questionId}`);
    return o;
  }

  trait(key: string): Trait {
    const t = this.space.traits.find((x) => x.key === key);
    if (!t) throw new Error(`no trait ${key}`);
    return t;
  }

  /** Half the box width -- 5 on the default -5..+5 scale. */
  get halfRange(): number {
    return (this.max - this.min) / 2;
  }

  /** Corner to opposite corner: sqrt(n) * (max - min). */
  get maxDistance(): number {
    return Math.sqrt(this.keys.length * (this.max - this.min) ** 2);
  }

  matchPercent(distance: number): number {
    return 100 * (1 - distance / this.maxDistance);
  }

  distance(a: Vector, b: Vector): number {
    let sum = 0;
    for (const k of this.keys) sum += (a[k] - b[k]) ** 2;
    return Math.sqrt(sum);
  }

  zero(): Vector {
    return Object.fromEntries(this.keys.map((k) => [k, 0]));
  }

  clamp(v: Vector): Vector {
    return Object.fromEntries(
      this.keys.map((k) => [k, Math.min(this.max, Math.max(this.min, v[k]))]),
    );
  }

  /** Step 1. Raw totals -- NOT yet comparable with dinosaur vectors. */
  accumulate(answers: readonly Answer[]): Vector {
    const totals = this.zero();
    for (const [qid, oid] of answers) {
      const option = this.option(qid, oid);
      for (const [k, v] of Object.entries(option.effects)) totals[k] += v;
    }
    return totals;
  }

  /** Step 2a. Per-axis multiplier: sd(dinosaurs) / sd(user totals).
      The user sd is exact: a total is a sum of independent per-question
      contributions, so its variance is the sum of per-question variances. */
  axisScales(spread = DEFAULT_SPREAD): Vector {
    const scales: Vector = {};
    for (const k of this.keys) {
      let userVariance = 0;
      for (const q of this.questions) {
        const vals = q.options.map((o) => o.effects[k] ?? 0);
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        userVariance += vals.reduce((a, v) => a + (v - mean) ** 2, 0) / vals.length;
      }
      const userSd = Math.sqrt(userVariance);

      const coords = this.dinosaurs.map((d) => d.traits[k]);
      const dinoMean = coords.reduce((a, b) => a + b, 0) / coords.length;
      const dinoSd = Math.sqrt(
        coords.reduce((a, c) => a + (c - dinoMean) ** 2, 0) / coords.length,
      );
      scales[k] = userSd === 0 ? 0 : (spread * dinoSd) / userSd;
    }
    return scales;
  }

  /** Step 2b. Apply the scales and clamp into the box. */
  normalize(raw: Vector, spread = DEFAULT_SPREAD): Vector {
    const scales = this.axisScales(spread);
    return this.clamp(Object.fromEntries(this.keys.map((k) => [k, raw[k] * scales[k]])));
  }

  /** Steps 3 and 4. Nearest first; ties broken by id so reloads are stable. */
  rank(profile: Vector, temperature = DEFAULT_TEMPERATURE): Match[] {
    if (temperature <= 0) throw new Error('temperature must be positive');
    const dists = this.dinosaurs.map((d) => ({ d, dist: this.distance(profile, d.traits) }));
    const nearest = Math.min(...dists.map((x) => x.dist));
    const weights = dists.map((x) => Math.exp(-(x.dist - nearest) / temperature));
    const total = weights.reduce((a, b) => a + b, 0);

    const matches = dists.map((x, i) => ({
      dinosaur: x.d,
      distance: x.dist,
      matchPercent: this.matchPercent(x.dist),
      confidence: weights[i] / total,
    }));
    matches.sort((a, b) => a.distance - b.distance || a.dinosaur.id.localeCompare(b.dinosaur.id));
    return matches;
  }

  /** Render a coordinate as a phrase, mirroring Trait.describe(). */
  describe(key: string, value: number): string {
    const t = this.trait(key);
    const mag = Math.abs(value);
    const pole = value >= 0 ? t.positive : t.negative;
    if (mag < 0.75) return `balanced between ${t.negative} and ${t.positive}`;
    if (mag < 2.0) return `leans ${pole}`;
    if (mag < 3.5) return `clearly ${pole}`;
    return `strongly ${pole}`;
  }

  score(
    answers: readonly Answer[],
    { temperature = DEFAULT_TEMPERATURE, spread = DEFAULT_SPREAD } = {},
  ): Result {
    const rawTotals = this.accumulate(answers);
    const profile = this.normalize(rawTotals, spread);
    const matches = this.rank(profile, temperature);
    const ordered = [...this.keys].sort((a, b) => Math.abs(profile[b]) - Math.abs(profile[a]));
    return {
      winner: matches[0].dinosaur,
      runnerUp: matches[1] ?? null,
      profile,
      rawTotals,
      matches,
      summary: ordered.slice(0, 2).map((k) => this.describe(k, profile[k])),
    };
  }
}
