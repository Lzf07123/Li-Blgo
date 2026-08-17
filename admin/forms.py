"""配置表单字段规格与解析：把友好的表单值写回 YAML 数据。"""

from typing import Optional

import yaml


def nested_get(data: dict, path: list[str]):
    cur = data
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def nested_set(data: dict, path: list[str], value) -> None:
    cur = data
    for part in path[:-1]:
        cur = cur.setdefault(part, {})
    cur[path[-1]] = value


def parse_config(data: dict, fields: list[dict], form) -> tuple[Optional[dict], str]:
    """按字段规格把表单合并进 data。返回 (new_data, error)。"""
    for spec in fields:
        name = spec["name"]
        ftype = spec.get("type", "text")
        label = spec.get("label", name)
        path = name.split(".")
        if ftype == "checkbox":
            raw = str(form.get(name, ""))
            nested_set(data, path, raw in ("1", "on", "true"))
        elif ftype == "csv":
            raw = str(form.get(name, ""))
            items = [x.strip() for x in raw.split(",") if x.strip()]
            nested_set(data, path, items)
        elif ftype == "list":
            rows = []
            columns = spec.get("columns", [])
            idx = 0
            while True:
                row = {}
                found = False
                for col in columns:
                    key = col["key"]
                    raw = form.get(f"{name}[{idx}][{key}]")
                    if raw is None:
                        continue
                    found = True
                    row[key] = str(raw).strip()
                if not found:
                    break
                if any(row.values()):
                    rows.append(row)
                idx += 1
            nested_set(data, path, rows)
        elif ftype == "number":
            raw = str(form.get(name, "")).strip()
            if raw == "":
                nested_set(data, path, None)
            else:
                try:
                    nested_set(data, path, int(raw))
                except ValueError:
                    return None, f"{label} 必须是数字"
        elif ftype == "yaml":
            raw = str(form.get(name, ""))
            try:
                value = yaml.safe_load(raw or "{}") or {}
            except yaml.YAMLError as exc:
                return None, f"{label} 解析失败：{exc}"
            nested_set(data, path, value)
        else:
            nested_set(data, path, str(form.get(name, "")).strip())
    return data, ""
