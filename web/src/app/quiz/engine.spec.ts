import fixture from './parity.fixture.json';
import { loadEngine } from './data';
import { Answer, Engine } from './engine';

/* The port must agree with the Python reference on every number. The fixture
   was produced by scripts/quiz_parity_fixture.py; if a case fails here, one
   side changed without the other. */
describe('Engine parity with the Python reference', () => {
  let engine: Engine;

  beforeEach(() => {
    engine = loadEngine();
  });

  it('is checking against the dataset the site ships', () => {
    expect(fixture.dataset).toBe('full');
    expect(fixture.cases.length).toBeGreaterThan(20);
  });

  for (const c of fixture.cases) {
    it(`matches case ${c.label}`, () => {
      const result = engine.score(c.answers as unknown as Answer[]);

      for (const k of engine.keys) {
        expect(result.rawTotals[k]).toBeCloseTo(c.expected.rawTotals[k as keyof typeof c.expected.rawTotals], 6);
        expect(result.profile[k]).toBeCloseTo(c.expected.profile[k as keyof typeof c.expected.profile], 6);
      }

      expect(result.matches.map((m) => m.dinosaur.id)).toEqual(
        c.expected.leaderboard.map((m) => m.id),
      );
      result.matches.forEach((m, i) => {
        const e = c.expected.leaderboard[i];
        expect(m.distance).toBeCloseTo(e.distance, 6);
        expect(m.matchPercent).toBeCloseTo(e.matchPercent, 6);
        expect(m.confidence).toBeCloseTo(e.confidence, 6);
      });

      expect(result.summary).toEqual(c.expected.summary);
    });
  }
});

describe('Engine invariants', () => {
  const engine = loadEngine();
  const allFirst: Answer[] = engine.questions.map((q) => [q.id, q.options[0].id]);

  it('keeps calibrated coordinates inside the box', () => {
    const p = engine.normalize(engine.accumulate(allFirst));
    for (const k of engine.keys) {
      expect(p[k]).toBeGreaterThanOrEqual(engine.min);
      expect(p[k]).toBeLessThanOrEqual(engine.max);
    }
  });

  it('confidence is a distribution', () => {
    const total = engine.rank(engine.zero()).reduce((a, m) => a + m.confidence, 0);
    expect(total).toBeCloseTo(1, 9);
  });

  it('standing on a dinosaur returns that dinosaur at 100%', () => {
    for (const d of engine.dinosaurs) {
      const top = engine.rank(d.traits)[0];
      expect(top.dinosaur.id).toBe(d.id);
      expect(top.matchPercent).toBeCloseTo(100, 9);
    }
  });

  it('rejects unknown answers instead of silently scoring them', () => {
    expect(() => engine.score([['charging', 'nope']])).toThrow();
  });
});
