"""Thin clients for each external service. Stages call these; they never log or cache themselves
(that is run_model_step's job), so every provider is used the same way."""
