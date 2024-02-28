import inspect
from typing import get_type_hints
from abc import ABC
from functools import wraps
from docstring_parser import parse

START_PATH = "/v1/actions"


def map_python_type_to_openapi(python_type):
    """Map Python types to OpenAPI types."""
    type_mapping = {
        int: "integer",
        float: "number",
        bool: "boolean",
        str: "string",
        list: "array",
        dict: "object",
    }
    return type_mapping.get(python_type, "string")


def auth(keys):
    """Decorator to set authentication keys for an ActionPack."""

    def class_decorator(cls):
        """Class decorator to set authentication keys for an ActionPack."""
        original_init = cls.__init__

        @wraps(cls.__init__)
        def new_init(self, *args, **kwargs):
            """Wrapper function for the __init__ method."""
            # Do something with the keys if needed e.g. env keys
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return class_decorator


def secure(func):
    """Decorator to mark an action as secure."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """Wrapper function for the action."""
        # Security checks or preparations can be done here
        return func(self, *args, **kwargs)

    # Set a custom attribute on the wrapper to indicate this method is secured
    wrapper.is_secure = True
    return wrapper


class ActionPack(ABC):
    """Base class for ActionPacks."""

    def __init__(self, auth: dict):
        """Initialize the ActionPack with authentication keys."""
        self.auth = auth


class ActionRunner:
    """Class to run actions and generate OpenAPI specification."""

    def __init__(self, action_pack_instance):
        """Initialize the ActionRunner with an ActionPack instance."""
        self.action_pack = action_pack_instance

    def get_actions(self):
        """Get all actions from the action pack."""
        actions = {}
        for method_name in dir(self.action_pack):
            if method_name.startswith("_"):
                continue
            method = getattr(self.action_pack, method_name)
            if callable(method):
                docstring = (inspect.getdoc(method) or "").strip()
                parsed_docstring = parse(docstring) if docstring else None
                signature = inspect.signature(method)
                parameters = []

                for param_name, param in signature.parameters.items():
                    if param_name == "self":
                        continue
                    param_type = get_type_hints(method).get(param_name, str)
                    openapi_type = map_python_type_to_openapi(param_type)
                    param_description = next(
                        (
                            p.description
                            for p in parsed_docstring.params
                            if p.arg_name == param_name
                        ),
                        "",
                    )
                    parameters.append(
                        {
                            "name": param_name,
                            "in": "query",  # This needs refinement based on actual parameter usage
                            "description": param_description,
                            "required": param.default is inspect.Parameter.empty,
                            "schema": {"type": openapi_type},
                        }
                    )

                http_method = "POST"

                actions[method_name] = {
                    "summary": parsed_docstring.short_description
                    if parsed_docstring
                    else "",
                    "description": parsed_docstring.long_description
                    if parsed_docstring
                    else "",
                    "operationId": method_name,
                    "parameters": parameters,
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",  # This should be refined based on actual return types
                                    }
                                }
                            },
                        }
                    },
                    "tags": [http_method],
                }

        # Convert to OpenAPI specification
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.action_pack.__class__.__name__ + " API",
                "version": "1.0.0",
                "description": f"API for {self.action_pack.__class__.__name__}",
            },
            "paths": {},
        }

        for endpoint, details in actions.items():
            path = f"{START_PATH}/{self.action_pack.__class__.__name__}/{endpoint}"
            openapi_spec["paths"][path] = {
                http_method: {
                    "tags": details["tags"],
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "operationId": details["operationId"],
                    "parameters": details["parameters"],
                    "responses": details["responses"],
                }
            }
        return openapi_spec

    def run_action(self, action_name, data):
        """Run an action from the action pack."""
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
        return method(**data)
