"""Shared helpers used by every stage: config, storyboard validation, caching, logging, retries."""


class NotBuiltYet(Exception):
    """Raised by a stage that exists in the plan but has not been written yet."""


class MissingInput(Exception):
    """A stage needs an output that an earlier stage has not produced yet."""
