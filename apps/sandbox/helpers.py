import copy
import json


class Helpers:
    @staticmethod
    def get(data, path, default=None):
        if not isinstance(path, str) or not path:
            return default
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return default
            elif isinstance(current, (list, tuple)):
                if part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return default
                else:
                    return default
            else:
                return default
        return current

    @staticmethod
    def set_value(data, path, value):
        if not isinstance(path, str) or not path:
            return data
        parts = path.split(".")
        if len(parts) == 1:
            if isinstance(data, dict):
                new = dict(data)
                new[parts[0]] = value
                return new
            return {parts[0]: value}

        key = parts[0]
        child = data.get(key) if isinstance(data, dict) else None
        if not isinstance(child, (dict, list, tuple)):
            child = {}
        new_child = Helpers.set_value(child, ".".join(parts[1:]), value)
        new = dict(data) if isinstance(data, dict) else {}
        new[key] = new_child
        return new

    @staticmethod
    def pick(data, keys):
        if not isinstance(data, dict):
            return {}
        if not isinstance(keys, (list, tuple, set)):
            return {}
        return {key: data[key] for key in keys if isinstance(key, str) and key in data}

    @staticmethod
    def omit(data, keys):
        if not isinstance(data, dict):
            return {}
        excluded = set(keys) if isinstance(keys, (list, tuple, set)) else set()
        return {key: value for key, value in data.items() if key not in excluded}

    @staticmethod
    def to_json(obj):
        return json.dumps(obj)

    @staticmethod
    def from_json(text):
        return json.loads(text)
