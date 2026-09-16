# -*- coding: utf-8 -*-
"""Generate mock sensor payloads matching 评估报告数据/生理数据.txt."""
import random
from datetime import datetime, timedelta


CHANNEL_DEFINITIONS = [
    ("心率", 1), ("呼吸", 2), ("体温", 3), ("眼动数据", 4), ("表情数据", 5),
    ("加速度", 11), ("角速度", 12), ("Delta", 21), ("Theta", 22),
    ("Alpha", 23), ("Beta", 24), ("Gamma", 25), ("皮电", 31),
    ("血氧", 41), ("温湿度", 61),
]


def _round(value):
    return round(float(value), 3)


def _text(value):
    return str(_round(value))


def _time(start, seconds, millis=True):
    value = start + timedelta(seconds=seconds)
    return value.strftime("%H:%M:%S.%f")[:-3] if millis else value.strftime("%H:%M:%S")


def _series(target, low, high, count, rng):
    values = [max(low, min(high, rng.gauss(target, max((high - low) / 6, 1e-6)))) for _ in range(count)]
    values[0], values[1] = low, high
    for _ in range(20):
        residual = target * count - sum(values)
        if abs(residual) < 1e-6:
            break
        step = residual / (count - 2)
        for index in range(2, count):
            values[index] = max(low, min(high, values[index] + step))
    return [_round(value) for value in values]


def _scalar(label, date_type, values, start, rate):
    return {
        "label": label,
        "preValue": _text(sum(values) / len(values)),
        "maxValue": _text(max(values)),
        "minValue": _text(min(values)),
        "dateValues": [
            {"time": _time(start, index / rate), "x": None, "y": None, "z": None, "value": _text(value)}
            for index, value in enumerate(values)
        ],
        "dateType": date_type,
    }


def _vector(label, date_type, points, start, rate):
    return {
        "label": label, "preValue": None, "maxValue": None, "minValue": None,
        "dateValues": [
            {
                "time": _time(start, index / rate),
                "x": None if point[0] is None else _text(point[0]),
                "y": None if point[1] is None else _text(point[1]),
                "z": None if point[2] is None else _text(point[2]),
                "value": None,
            }
            for index, point in enumerate(points)
        ],
        "dateType": date_type,
    }


def _expressions(distribution, start, count, rng):
    names = {"happy": "高兴", "surprise": "惊讶", "neutral": "中性", "sadness": "悲伤", "fear": "恐惧", "disgust": "厌恶", "anger": "愤怒"}
    keys = [key for key, weight in distribution.items() if key in names and weight > 0]
    selected = rng.choices(keys, weights=[distribution[key] for key in keys], k=count)
    return {
        "label": "表情数据", "preValue": None, "maxValue": None, "minValue": None,
        "dateValues": [
            {"time": _time(start, index, False), "x": names[key], "y": names[key], "z": None, "value": "0"}
            for index, key in enumerate(selected)
        ],
        "dateType": 5,
    }


def generate_physiology_payload(summary, seed, eeg=None, expressions=None, duration_sec=60, start_time=None):
    """Return the exact top-level/channel schema used by the real physiology JSON."""
    rng = random.Random(seed)
    start = start_time or datetime(2026, 6, 24, 15, 13, 22)
    eeg = eeg or {"delta": 25.0, "theta": 30.0, "alpha": 30.0, "beta": 35.0, "gamma": 20.0}
    expressions = expressions or {"neutral": 0.55, "happy": 0.2, "sadness": 0.15, "anger": 0.1}

    def values(avg_key, range_key, rate):
        low, high = map(float, summary[range_key])
        return _series(float(summary[avg_key]), low, high, duration_sec * rate, rng)

    heart = values("heart_rate_avg", "heart_rate_range", 2)
    breath = values("respiration_avg", "respiration_range", 2)
    temperature = values("temperature_avg", "temperature_range", 2)
    delta = _series(float(eeg["delta"]), 1, max(65, float(eeg["delta"])), duration_sec, rng)
    theta = _series(float(eeg["theta"]), 5, max(78, float(eeg["theta"])), duration_sec, rng)
    eda_avg = max(1, min(12, 2 + max(0, float(summary["heart_rate_avg"]) - 70) * 0.08))
    eda = _series(eda_avg, 1, max(15, eda_avg + 5), duration_sec, rng)
    spo2 = _series(97, 94, 99, duration_sec, rng)
    eye = [(rng.uniform(.15, .85), rng.uniform(.1, .9), None) for _ in range(duration_sec * 10)]
    acceleration = [(rng.gauss(0, .12), rng.gauss(-.35, .12), rng.gauss(.8, .08)) for _ in range(duration_sec * 5)]
    angular = [(rng.gauss(0, 1.8), rng.gauss(0, 2.2), rng.gauss(0, 1.2)) for _ in range(duration_sec * 5)]
    alpha = [(rng.gauss(eeg["alpha"], 3), None, rng.gauss(eeg["alpha"], 3)) for _ in range(duration_sec * 3)]
    beta = [(rng.gauss(eeg["beta"], 4), None, rng.gauss(eeg["beta"], 4)) for _ in range(duration_sec * 3)]
    gamma = [(rng.gauss(eeg["gamma"], 3), rng.gauss(eeg["gamma"], 3), None) for _ in range(duration_sec * 3)]
    environment = [(rng.gauss(25, .15), rng.gauss(55, .4), None) for _ in range(duration_sec)]
    data = [
        _scalar("心率", 1, heart, start + timedelta(seconds=17), 2),
        _scalar("呼吸", 2, breath, start + timedelta(seconds=16), 2),
        _scalar("体温", 3, temperature, start + timedelta(seconds=20), 2),
        _vector("眼动数据", 4, eye, start + timedelta(seconds=15), 10),
        _expressions(expressions, start + timedelta(seconds=22), duration_sec, rng),
        _vector("加速度", 11, acceleration, start + timedelta(seconds=25), 5),
        _vector("角速度", 12, angular, start + timedelta(seconds=25), 5),
        _scalar("Delta", 21, delta, start, 1), _scalar("Theta", 22, theta, start, 1),
        _vector("Alpha", 23, alpha, start, 3), _vector("Beta", 24, beta, start, 3),
        _vector("Gamma", 25, gamma, start, 3), _scalar("皮电", 31, eda, start + timedelta(seconds=4), 1),
        _scalar("血氧", 41, spo2, start + timedelta(seconds=19), 1),
        _vector("温湿度", 61, environment, start, 1),
    ]
    return {"msg": "操作成功", "code": 200, "data": data, "nextStartTime": (start + timedelta(seconds=duration_sec)).strftime("%Y-%m-%d %H:%M:%S")}


def channel_average(payload, label):
    return float(next(channel for channel in payload["data"] if channel["label"] == label)["preValue"])


def validate_schema(payload):
    assert set(payload) == {"msg", "code", "data", "nextStartTime"}
    assert [(item["label"], item["dateType"]) for item in payload["data"]] == CHANNEL_DEFINITIONS
    for channel in payload["data"]:
        assert set(channel) == {"label", "preValue", "maxValue", "minValue", "dateValues", "dateType"}
        for point in channel["dateValues"]:
            assert set(point) == {"time", "x", "y", "z", "value"}
