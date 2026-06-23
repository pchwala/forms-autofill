import type {
  PreviewDistribution,
  PreviewPersona,
  PreviewQuestion,
} from '../hooks/usePipeline';

/**
 * Recompute aggregate answer distributions for the currently-selected personas.
 * Mirrors `backend/preview.py:aggregate_distributions` so client-side toggling
 * matches what the server would produce: selected personas are renormalized to
 * 100%, and personas that skip a question (routing) are excluded from that
 * question's base and reported via `skipped_percent`.
 */
export function aggregateDistributions(
  personas: PreviewPersona[],
  selectedCodes: string[],
  questions: PreviewQuestion[],
): PreviewDistribution[] {
  const codeToPct = new Map(personas.map((p) => [p.code, p.count_percent]));
  const selected = selectedCodes.filter((c) => codeToPct.has(c));
  const selectedTotal = selected.reduce((sum, c) => sum + (codeToPct.get(c) ?? 0), 0) || 1;

  return questions.map((q) => {
    const contributing = selected.filter((c) => q.per_persona[c] != null);
    const contributingTotal = contributing.reduce((sum, c) => sum + (codeToPct.get(c) ?? 0), 0);

    const optPct = new Map<string, number>(q.options.map((opt) => [opt, 0]));
    if (contributingTotal > 0) {
      for (const code of contributing) {
        const share = (codeToPct.get(code) ?? 0) / contributingTotal;
        const weights = q.per_persona[code]!;
        for (const [opt, w] of Object.entries(weights)) {
          optPct.set(opt, (optPct.get(opt) ?? 0) + share * w);
        }
      }
    }

    const skippedPercent = Math.round(((selectedTotal - contributingTotal) / selectedTotal) * 100);

    return {
      id: q.id,
      label: q.label,
      type: q.type,
      options: q.options.map((opt) => ({
        option: opt,
        percent: Math.round((optPct.get(opt) ?? 0) * 10) / 10,
      })),
      skipped_percent: skippedPercent,
      grid_id: q.grid_id,
      grid_label: q.grid_label,
      row_label: q.row_label,
    };
  });
}
