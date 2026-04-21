-- Migration 001: Index pour la maintenance des predictions
-- Audit F01/R6 : selfmodel_predictions a 5.2M rows (1578 MB = 74% DB)
-- mais seulement 215 (0.004%) verifiees. Cet index accelere les queries
-- de verification et d'archivage sur les predictions non verifiees.

CREATE INDEX IF NOT EXISTS idx_selfmodel_predictions_stale
ON selfmodel_predictions (predicted_at)
WHERE was_correct IS NULL;
