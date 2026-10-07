"""
Executive Reporting package.
"""

def __getattr__(name):
    if name == "run_inference":
        from .daily_inference import run_inference
        return run_inference
    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = ["run_inference"]
