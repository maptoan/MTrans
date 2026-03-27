# -*- coding: utf-8 -*-


class ResourceExhaustedError(Exception):
    """Exception raised when all API keys are exhausted or unavailable."""

    def __init__(self, message="No available API keys."):
        self.message = message
        super().__init__(self.message)
