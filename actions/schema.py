from abc import ABC
from functools import wraps


def auth(keys):
    def class_decorator(cls):
        original_init = cls.__init__

        @wraps(cls.__init__)
        def new_init(self, *args, **kwargs):
            # Do something with the keys if needed e.g. env keys
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return class_decorator


def secure(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Security checks or preparations can be done here
        return func(self, *args, **kwargs)

    # Set a custom attribute on the wrapper to indicate this method is secured
    wrapper.is_secure = True
    return wrapper


class ActionPack(ABC):
    def __init__(self, auth: dict):
        self.auth = auth


def get_http_method(method_name):
    if method_name.startswith("get_"):
        return "GET"
    elif method_name.startswith("post_"):
        return "POST"
    elif method_name.startswith("delete_"):
        return "DELETE"
    else:
        return "Unknown"


import inspect
from typing import get_type_hints


class ActionRunner:
    def __init__(self, action_pack_instance):
        self.action_pack = action_pack_instance

    def get_actions(self):
        actions = {}
        for method_name in dir(self.action_pack):
            if method_name.startswith("_"):
                continue
            method = getattr(self.action_pack, method_name)
            if callable(method):
                docstring = inspect.getdoc(method)
                signature = inspect.signature(method)
                parameters = []
                for param_name, param in signature.parameters.items():
                    if param_name == "self":
                        continue
                    param_type = get_type_hints(method).get(
                        param_name, str
                    )  # Default to str if type hint not provided
                    param_description = (
                        ""  # Extract this from the docstring if possible
                    )
                    parameters.append(
                        {
                            "name": param_name,
                            "in": "query",  # Assume query for simplicity; this might need refinement
                            "description": param_description,
                            "required": param.default is inspect.Parameter.empty,
                            "schema": {
                                "type": "string"  # Simplified; real implementation would map Python types to OpenAPI types
                            },
                        }
                    )

                http_method = (
                    "get"  # Default to GET; refine this based on method_name prefix
                )
                if method_name.startswith("post_"):
                    http_method = "post"
                elif method_name.startswith("delete_"):
                    http_method = "delete"

                actions[method_name] = {
                    "summary": docstring.split("\n")[0] if docstring else "",
                    "description": docstring,
                    "operationId": method_name,
                    "parameters": parameters,
                    "responses": {  # This is a simplification; actual response schemas depend on method return types
                        "200": {"description": "Success"}
                    },
                    "tags": [
                        http_method.upper()
                    ],  # Tagging with HTTP method for grouping
                }
        return actions

    def run_action(self, action_name, *args, **kwargs):
        if action_name not in self.get_actions():
            raise ValueError(f"Action '{action_name}' not found.")

        action_info = self.get_actions()[action_name]

        if action_info["secure"]:
            if not all(
                key in self.action_pack.auth
                for key in getattr(self.action_pack, "auth_keys", [])
            ):
                missing_keys = [
                    key
                    for key in getattr(self.action_pack, "auth_keys", [])
                    if key not in self.action_pack.auth
                ]
                raise ValueError(
                    f"Missing authentication keys for secure action: {', '.join(missing_keys)}"
                )

        method = getattr(self.action_pack, action_name)
        return method(*args, **kwargs)
