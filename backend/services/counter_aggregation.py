from __future__ import annotations

from statistics import median


def cumulative_counter_delta(
    values: list[float | int | None],
    *,
    max_step: float | None = None,
) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None

    positive_steps: list[float] = []
    for index, (prev, curr) in enumerate(zip(clean, clean[1:])):
        step = curr - prev
        if step <= 0:
            continue
        later_values = clean[index + 2 :]
        if later_values and min(later_values) <= prev:
            continue
        next_value = clean[index + 2] if index + 2 < len(clean) else None
        if next_value is not None and next_value <= prev:
            continue
        positive_steps.append(step)
    if not positive_steps:
        return 0.0

    if max_step is None:
        typical = median(positive_steps)
        max_step = max(1.0, typical * 20)

    valid_steps = [step for step in positive_steps if step <= max_step]
    return round(sum(valid_steps), 3)
