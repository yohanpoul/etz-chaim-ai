-- Demo seed data for Etz Chaim AI dashboard.
-- Loaded via `etzchaim demo` after `etzchaim start`.
-- Idempotent : ON CONFLICT DO NOTHING.

-- 5 epistememory concepts sampling the Kabbale-AI domain
INSERT INTO epistememory (concept, domain, confidence, epistemic_status, content)
VALUES
  ('Partzuf', 'kabbalah', 0.95, 'verified',
   'Mature configuration of Sephirot — the 6 composition layers in Etz Chaim AI.'),
  ('Transformer', 'ai', 0.95, 'verified',
   'Attention-based neural architecture, the generative substrate wrapped by the cognitive architecture.'),
  ('Sephirah', 'kabbalah', 0.95, 'verified',
   'Discrete attribute through which intelligence organizes itself — 10 specialized capability modules.'),
  ('Attention mechanism', 'ai', 0.9, 'verified',
   'Mechanism by which transformers select relevant context — wrapped by the masakh 5-level filtration.'),
  ('Tsimtsum', 'kabbalah', 0.9, 'verified',
   'Primordial contraction — analogous to information bottleneck in representation learning.')
ON CONFLICT DO NOTHING;

-- 1 demo tension in dissensuengine (Tiferet productive dialectic)
INSERT INTO tension_points (perspective_a, perspective_b, reconciliation)
VALUES
  ('LLM reasoning as statistical pattern matching (Bender, Koller 2020)',
   'LLM reasoning as genuine causal inference (Webb et al. 2023)',
   'Distinct levels coexist : shallow matching for retrieval, deeper causal inference emerges with scale.')
ON CONFLICT DO NOTHING;
