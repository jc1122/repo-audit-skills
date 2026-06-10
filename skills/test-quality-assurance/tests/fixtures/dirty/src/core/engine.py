"""Internal engine implementation -- should NOT be imported by tests directly."""


class DataEngine:
    def __init__(self, data: list[float] | None = None):
        self._data = data or []
        self._cache: dict[str, float] = {}

    def _normalize_value(self, v: float) -> float:
        return max(0.0, min(v, 100.0))

    def _compute_aggregate(self) -> float:
        if not self._data:
            return 0.0
        normalized = [self._normalize_value(v) for v in self._data]
        return sum(normalized) / len(normalized)

    def process(self, scale: float = 1.0) -> dict[str, float]:
        agg = self._compute_aggregate()
        result = {"aggregate": agg * scale, "count": len(self._data)}
        self._cache["last"] = result["aggregate"]
        return result

    def cached_value(self):
        return self._cache.get("last")


class InternalHelper:
    """Implementation detail helpful only for internal wiring."""

    def __init__(self, engine: DataEngine):
        self._engine = engine

    def _validate(self) -> bool:
        return len(self._engine._data) > 0
