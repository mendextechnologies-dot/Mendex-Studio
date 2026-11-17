"""Explicit-data semiconductor comparison; analytical estimates, never approvals.

No bundled device ratings. Losses are interpolated only inside the supplied
voltage/current/temperature grid at its declared gate conditions. Foster
coefficients must describe the COMPLETE junction-to-boundary thermal path.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from bisect import bisect_left
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import Model

Positive = Annotated[float, Field(gt=0, le=1e12, strict=True)]
Nonnegative = Annotated[float, Field(ge=0, le=1e12, strict=True)]
Temperature = Annotated[float, Field(gt=-273.15, le=1000, strict=True)]
Text = Annotated[str, Field(min_length=1, max_length=2000)]


class LossPoint(Model):
    voltage_v: Positive | None = None
    current_a: Nonnegative
    junction_temp_c: Temperature
    on_voltage_v: Nonnegative
    e_on_j: Nonnegative
    e_off_j: Nonnegative


class FosterBranch(Model):
    resistance_k_w: Positive
    tau_s: Positive


class FatiguePoint(Model):
    delta_t_k: Positive
    cycles_to_failure: Positive


class FatigueModel(Model):
    source: Text
    conditions: Text
    mean_temp_min_c: Temperature
    mean_temp_max_c: Temperature
    heating_time_min_s: Positive
    heating_time_max_s: Positive
    curve: list[FatiguePoint] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def ordered(self):
        if self.mean_temp_min_c > self.mean_temp_max_c or self.heating_time_min_s > self.heating_time_max_s:
            raise ValueError("Fatigue validity bounds must be ordered")
        ordered = sorted(self.curve, key=lambda p: p.delta_t_k)
        if len({p.delta_t_k for p in ordered}) != len(ordered):
            raise ValueError("Fatigue curve has duplicate temperature swings")
        if any(b.cycles_to_failure > a.cycles_to_failure for a, b in zip(ordered, ordered[1:])):
            raise ValueError("Fatigue curve cycles must not increase with temperature swing")
        return self


class DeviceModel(Model):
    name: Text
    mpn: str | None = Field(default=None, min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=200)
    component_reference: str | None = Field(default=None, min_length=1, max_length=100)
    source: Text
    gate_conditions: Text
    loss_scope: Text  # Explicitly list included/excluded reverse recovery, gate, Coss etc.
    reference_voltage_v: Positive
    frequency_min_hz: Positive
    frequency_max_hz: Positive
    max_junction_temp_c: Temperature
    loss_points: list[LossPoint] = Field(min_length=4, max_length=400)
    thermal_source: Text
    boundary: Literal["ambient", "case"]
    foster: list[FosterBranch] = Field(min_length=1, max_length=12)
    fatigue: FatigueModel | None = None

    @model_validator(mode="after")
    def grid(self):
        currents = {p.current_a for p in self.loss_points}
        temperatures = {p.junction_temp_c for p in self.loss_points}
        explicit = [p.voltage_v is not None for p in self.loss_points]
        if any(explicit) and not all(explicit):
            raise ValueError("Supply voltage_v for every loss point or omit it for every point")
        voltages = {p.voltage_v if p.voltage_v is not None else self.reference_voltage_v for p in self.loss_points}
        keys = {(p.voltage_v, p.current_a, p.junction_temp_c) for p in self.loss_points}
        if len(currents) < 2 or len(temperatures) < 2 or len(keys) != len(self.loss_points) or len(keys) != len(voltages) * len(currents) * len(temperatures):
            raise ValueError("Loss points require a complete unique voltage x current x temperature grid, at least 2 currents x 2 temperatures")
        if not min(voltages) <= self.reference_voltage_v <= max(voltages):
            raise ValueError("Reference voltage must lie within supplied loss-table voltages")
        if self.frequency_min_hz > self.frequency_max_hz:
            raise ValueError("Frequency validity bounds must be ordered")
        return self


class OperatingPoint(Model):
    voltage_v: Positive
    gate_conditions: Text
    current_a: Nonnegative  # Constant conduction-interval current, NOT output or full-period RMS.
    output_power_w: Positive
    duty_cycle: Annotated[float, Field(gt=0, lt=1, strict=True)]
    frequency_hz: Positive
    boundary_temp_c: Temperature
    other_losses_w: Nonnegative
    quantity: int = Field(ge=1, le=100, strict=True)


class Sweep(Model):
    load_factors: list[Positive] = Field(min_length=1, max_length=100)
    frequencies_hz: list[Positive] = Field(min_length=1, max_length=100)
    boundary_temperatures_c: list[Temperature] = Field(min_length=1, max_length=100)


class LoadSegment(Model):
    duration_s: Positive
    current_a: Nonnegative
    output_power_w: Nonnegative
    frequency_hz: Positive
    duty_cycle: Annotated[float, Field(gt=0, lt=1, strict=True)]
    other_losses_w: Nonnegative


class ThermalCycle(Model):
    delta_t_k: Positive
    mean_temp_c: Temperature
    heating_time_s: Positive
    count: Positive
    conditions: Text

    @model_validator(mode="after")
    def physical_range(self):
        if self.mean_temp_c - self.delta_t_k / 2 <= -273.15:
            raise ValueError("Thermal cycle reaches below absolute zero")
        return self


class AnalysisRequest(Model):
    schema_version: Literal["1.0"] = "1.0"
    assumptions: list[Text] = Field(min_length=1, max_length=30)
    devices: list[DeviceModel] = Field(min_length=1, max_length=5)
    model_library: list[DeviceModel] = Field(default_factory=list, max_length=50)
    expected_component_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    operating_point: OperatingPoint
    sweeps: Sweep
    load_cycle: list[LoadSegment] = Field(default_factory=list, max_length=200)
    repeat_cycles: int = Field(default=1, ge=1, le=10, strict=True)
    samples_per_segment: int = Field(default=10, ge=1, le=50, strict=True)
    thermal_cycles: list[ThermalCycle] = Field(default_factory=list, max_length=200)
    cycle_count_source: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def limits(self):
        if len({d.name for d in self.devices}) != len(self.devices):
            raise ValueError("Device names must be unique")
        references = [d.component_reference for d in self.devices if d.component_reference]
        if len(set(references)) != len(references):
            raise ValueError("Each revision component may be bound only once in a comparison")
        if len(self.load_cycle) * self.repeat_cycles * self.samples_per_segment > 5000:
            raise ValueError("Load cycle exceeds 5000 samples per device")
        if self.thermal_cycles and not self.cycle_count_source:
            raise ValueError("Thermal cycle counts require their source/method")
        return self


def import_loss_csv(text: str) -> list[dict]:
    """SI-only loss table import; provenance and test conditions are separate required inputs."""
    if len(text.encode("utf-8")) > 200_000:
        raise ValueError("Loss CSV exceeds 200 kB")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    fields = set(LossPoint.model_fields) - {"voltage_v"}
    headers = reader.fieldnames or []
    if set(headers) not in (fields, fields | {"voltage_v"}) or len(headers) != len(set(headers)):
        raise ValueError("CSV headers must be current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j, with optional voltage_v")
    rows = []
    for row in reader:
        if len(rows) >= 400 or None in row:
            raise ValueError("Loss CSV has too many rows or malformed columns")
        rows.append(LossPoint.model_validate({k: float(v) for k, v in row.items()}).model_dump())
    if not rows:
        raise ValueError("Loss CSV is empty")
    return rows


class OutsideModel(ValueError):
    pass


def _bracket(axis, value):
    if value < axis[0] - 1e-9 or value > axis[-1] + 1e-9:
        raise OutsideModel(f"{value:g} outside supplied model range {axis[0]:g}–{axis[-1]:g}; no extrapolation")
    value = min(axis[-1], max(axis[0], value))
    i = max(1, min(len(axis) - 1, bisect_left(axis, value)))
    a, b = axis[i - 1], axis[i]
    return a, b, (value - a) / (b - a)


class Evaluator:
    def __init__(self, device: DeviceModel, op: OperatingPoint):
        self.device, self.op = device, op
        self.currents = sorted({p.current_a for p in device.loss_points})
        self.temperatures = sorted({p.junction_temp_c for p in device.loss_points})
        self.voltages = sorted({p.voltage_v if p.voltage_v is not None else device.reference_voltage_v for p in device.loss_points})
        self.grid = {(p.voltage_v if p.voltage_v is not None else device.reference_voltage_v, p.current_a, p.junction_temp_c): p for p in device.loss_points}
        self.resistance = sum(b.resistance_k_w for b in device.foster)

    def losses(self, current, temperature, frequency, duty):
        if len(self.voltages) == 1 and not math.isclose(self.op.voltage_v, self.voltages[0], rel_tol=1e-9):
            raise OutsideModel("Operating voltage does not match device loss-table reference voltage")
        v0, v1, wv = _bracket(self.voltages, self.op.voltage_v) if len(self.voltages) > 1 else (self.voltages[0], self.voltages[0], 0.0)
        if self.op.gate_conditions != self.device.gate_conditions:
            raise OutsideModel("Operating gate conditions do not match supplied device model")
        if not self.device.frequency_min_hz <= frequency <= self.device.frequency_max_hz:
            raise OutsideModel("Frequency outside supplied validity bounds")
        if temperature > self.device.max_junction_temp_c:
            raise OutsideModel("Junction temperature exceeds supplied device limit")
        i0, i1, wi = _bracket(self.currents, current)
        t0, t1, wt = _bracket(self.temperatures, temperature)
        def interp(field):
            def plane(v):
                a = getattr(self.grid[v, i0, t0], field) * (1 - wi) + getattr(self.grid[v, i1, t0], field) * wi
                b = getattr(self.grid[v, i0, t1], field) * (1 - wi) + getattr(self.grid[v, i1, t1], field) * wi
                return a * (1 - wt) + b * wt
            return plane(v0) * (1 - wv) + plane(v1) * wv
        conduction = current * interp("on_voltage_v") * duty
        switching = (interp("e_on_j") + interp("e_off_j")) * frequency
        return conduction, switching

    def steady(self, current, output_power, frequency, duty, boundary, other):
        low = max(boundary, self.temperatures[0])
        high = min(self.temperatures[-1], self.device.max_junction_temp_c)
        def balance(t):
            pc, ps = self.losses(current, t, frequency, duty)
            return boundary + self.resistance * (pc + ps) - t
        # Each table interval is affine at fixed current. A nonnegative balance
        # slope prevents a unique stable solution: do not mask thermal runaway.
        boundaries = sorted({low, high, *(t for t in self.temperatures if low < t < high)})
        for a, b in zip(boundaries, boundaries[1:]):
            if b > a and (balance(b) - balance(a)) / (b - a) >= -1e-10:
                raise OutsideModel("Unstable or non-unique thermal feedback inside supplied model range")
        if low > high or balance(low) < -1e-7 or balance(high) > 1e-7:
            raise OutsideModel("No bounded steady-state thermal solution inside model/device limits")
        for _ in range(48):
            mid = (low + high) / 2
            if balance(mid) > 0:
                low = mid
            else:
                high = mid
        tj = (low + high) / 2
        pc, ps = self.losses(current, tj, frequency, duty)
        total = (pc + ps) * self.op.quantity + other
        return {"status": "COMPUTED", "conduction_w": pc, "switching_w": ps,
                "device_loss_w": pc + ps, "represented_system_loss_w": total,
                "efficiency_pct": 100 * output_power / (output_power + total) if output_power > 0 else None,
                "junction_temp_c": tj, "thermal_margin_k": self.device.max_junction_temp_c - tj}

    def transient(self, request):
        # Cold start at the FIXED boundary; every independent device has its own thermal path.
        states = [0.0] * len(self.device.foster)
        elapsed = 0.0
        points = [{"time_s": 0.0, "junction_temp_c": self.op.boundary_temp_c,
                   "device_loss_w": None, "status": "INITIAL_CONDITION"}]
        for _ in range(request.repeat_cycles):
            for segment in request.load_cycle:
                dt = segment.duration_s / request.samples_per_segment
                factors = [math.exp(-dt / b.tau_s) for b in self.device.foster]
                for _ in range(request.samples_per_segment):
                    # Backward thermal/loss coupling: solve temperature at this step.
                    memory = sum(s * f for s, f in zip(states, factors))
                    resistance = sum(b.resistance_k_w * (1 - f) for b, f in zip(self.device.foster, factors))
                    low = max(self.op.boundary_temp_c + memory, self.temperatures[0])
                    high = min(self.temperatures[-1], self.device.max_junction_temp_c)
                    def balance(t):
                        pc, ps = self.losses(segment.current_a, t, segment.frequency_hz, segment.duty_cycle)
                        return self.op.boundary_temp_c + memory + resistance * (pc + ps) - t
                    if low > high or balance(low) < -1e-7 or balance(high) > 1e-7:
                        raise OutsideModel("Transient thermal solution outside model/device limits")
                    for _ in range(40):
                        mid = (low + high) / 2
                        if balance(mid) > 0:
                            low = mid
                        else:
                            high = mid
                    tj = (low + high) / 2
                    pc, ps = self.losses(segment.current_a, tj, segment.frequency_hz, segment.duty_cycle)
                    states = [s * f + (pc + ps) * b.resistance_k_w * (1 - f)
                              for s, f, b in zip(states, factors, self.device.foster)]
                    elapsed += dt
                    total = (pc + ps) * self.op.quantity + segment.other_losses_w
                    points.append({"time_s": elapsed, "status": "COMPUTED", "junction_temp_c": tj,
                                   "device_loss_w": pc + ps, "conduction_w": pc, "switching_w": ps,
                                   "represented_system_loss_w": total,
                                   "efficiency_pct": 100 * segment.output_power_w / (segment.output_power_w + total)
                                   if segment.output_power_w > 0 else None})
        return {"status": "COMPUTED", "points": points,
                "sampled_temperature_ripple_k": max(p["junction_temp_c"] for p in points) - min(p["junction_temp_c"] for p in points),
                "note": "Cold-start profile span, not periodic switching ripple; convergence requires timestep refinement."}


def _unevaluated(reason):
    return {"status": "NOT_EVALUATED", "reason": str(reason)}


def _fatigue(device, request):
    model = device.fatigue
    if model is None or not request.thermal_cycles:
        return _unevaluated("Supply sourced fatigue curve and externally counted thermal-cycle bins; mission profile is not automatically cycle-counted")
    curve = sorted(model.curve, key=lambda p: p.delta_t_k)
    axis = [p.delta_t_k for p in curve]
    damage, bins = 0.0, []
    for cycle in request.thermal_cycles:
        if (cycle.conditions != model.conditions or not model.mean_temp_min_c <= cycle.mean_temp_c <= model.mean_temp_max_c
                or not model.heating_time_min_s <= cycle.heating_time_s <= model.heating_time_max_s):
            return _unevaluated("Cycle conditions, mean temperature or heating time do not match supplied fatigue applicability")
        if cycle.mean_temp_c + cycle.delta_t_k / 2 > device.max_junction_temp_c:
            return _unevaluated("Thermal cycle exceeds supplied device junction-temperature limit")
        try:
            a, b, _ = _bracket(axis, cycle.delta_t_k)
        except OutsideModel as exc:
            return _unevaluated(exc)
        left, right = curve[axis.index(a)], curve[axis.index(b)]
        weight = math.log(cycle.delta_t_k / a) / math.log(b / a)
        nf = math.exp(math.log(left.cycles_to_failure) * (1 - weight) + math.log(right.cycles_to_failure) * weight)
        contribution = cycle.count / nf
        damage += contribution
        bins.append({"delta_t_k": cycle.delta_t_k, "count": cycle.count, "cycles_to_failure": nf, "damage": contribution})
    return {"status": "COMPUTED", "method": "Miner linear damage with log-log curve interpolation",
            "damage_fraction": damage, "equivalent_profile_blocks_to_damage_one": 1 / damage if damage > 0 else None,
            "bins": bins, "source": model.source, "cycle_count_source": request.cycle_count_source,
            "note": "User-model estimate, not remaining life, reliability qualification or Infineon lifetime prediction."}


def analyze_power_thermal(parameters: dict | AnalysisRequest, *, binding_errors: dict[int, str] | None = None) -> dict:
    request = AnalysisRequest.model_validate(parameters)
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
    result = {"schema_version": "1.0", "calculation": "power_thermal_analysis", "evaluation_status": "NOT_EVALUATED",
              "evidence_type": "CALCULATED", "request_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
              "inputs": request.model_dump(mode="json"), "devices": [],
              "warnings": ["Analytical estimates from user-supplied models; no vendor qualification or physical validation.",
                           "Constant conduction-interval current: Pcond=I*Von*duty; Psw=(Eon+Eoff)*frequency.",
                           "Fixed gate conditions; trilinear voltage/current/temperature interpolation when a complete voltage grid is supplied; no extrapolation.",
                           "Efficiency includes only quantity*modeled device loss + explicit other losses. Independent identical thermal paths; no mutual heating.",
                           "Foster model must cover complete junction-to-fixed-boundary path. Do not concatenate junction-case and heatsink Foster networks."]}
    op = request.operating_point
    for index, device in enumerate(request.devices):
        reason = (binding_errors or {}).get(index)
        if device.component_reference and binding_errors is None:
            reason = "Bound components require a revision context; use a revision-aware preview or guarded calculation record"
        if reason:
            result["devices"].append({"name": f"{device.component_reference or device.name} — model unavailable",
                "source": device.source, "thermal_source": device.thermal_source, "boundary": device.boundary,
                "operating_point": _unevaluated(reason), "load_sweep": [], "frequency_sweep": [], "boundary_sweep": [],
                "load_cycle": _unevaluated(reason), "lifetime": _unevaluated(reason), "thermal_impedance": []})
            continue
        evaluator = Evaluator(device, op)
        def point(**changes):
            args = dict(current=op.current_a, output_power=op.output_power_w, frequency=op.frequency_hz,
                        duty=op.duty_cycle, boundary=op.boundary_temp_c, other=op.other_losses_w)
            args.update(changes)
            try:
                return evaluator.steady(**args)
            except OutsideModel as exc:
                return _unevaluated(exc)
        entry = {"name": device.name, "source": device.source, "thermal_source": device.thermal_source,
                 "boundary": device.boundary, "operating_point": point(),
                 "load_sweep": [{"x": x, **point(current=op.current_a * x, output_power=op.output_power_w * x)} for x in request.sweeps.load_factors],
                 "frequency_sweep": [{"x": x, **point(frequency=x)} for x in request.sweeps.frequencies_hz],
                 "boundary_sweep": [{"x": x, **point(boundary=x)} for x in request.sweeps.boundary_temperatures_c],
                 "lifetime": _fatigue(device, request)}
        if request.load_cycle:
            try:
                entry["load_cycle"] = evaluator.transient(request)
            except OutsideModel as exc:
                entry["load_cycle"] = _unevaluated(exc)
        else:
            entry["load_cycle"] = _unevaluated("No load-cycle profile supplied")
        times = sorted({b.tau_s * factor for b in device.foster for factor in (0.01, 0.1, 1, 10)})
        entry["thermal_impedance"] = [{"time_s": t, "impedance_k_w": sum(b.resistance_k_w * -math.expm1(-t / b.tau_s) for b in device.foster)} for t in [0, *times]]
        result["devices"].append(entry)
    # Refuse numerical overflow anywhere; never serialize infinity or replace it with zero.
    json.dumps(result, allow_nan=False)
    return result
