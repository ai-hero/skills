import importlib
from actions.schema import ActionPack, ActionRunner
from flask import Flask, jsonify, request
import pkgutil
import yaml

app = Flask(__name__)


def load_action_packs(package="actions.packs"):
    action_packs = {}
    package = importlib.import_module(package)

    # Recursively load submodules and subpackages
    def load_from_package(package):
        for loader, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            module = importlib.import_module(module_name)
            if not is_pkg:  # If it's a module, check for ActionPack subclasses
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if (
                        isinstance(attribute, type)
                        and issubclass(attribute, ActionPack)
                        and attribute is not ActionPack
                    ):
                        # Instantiate the ActionPack subclass with necessary authentication or other initialization parameters
                        action_packs[attribute_name] = attribute(
                            auth={"key": "value"}
                        )  # Replace auth dict with actual required auth parameters
            else:  # If it's a package, recurse into it
                load_from_package(module)

    load_from_package(package)
    print(action_packs)
    return action_packs


action_packs = load_action_packs()


@app.route("/actions/<action_pack>", methods=["GET"])
def get_actions(action_pack):
    if action_pack not in action_packs:
        return jsonify({"error": "ActionPack not found"}), 404

    action_runner = ActionRunner(action_packs[action_pack])
    actions = action_runner.get_actions()
    return yaml.dump(actions), 200, {"Content-Type": "text/yaml"}


@app.route("/run_actions/<action_pack>/run", methods=["POST"])
def run_action(action_pack):
    if action_pack not in action_packs:
        return jsonify({"error": "ActionPack not found"}), 404

    data = request.json
    action_name = data.get("action_name")
    args = data.get("args", [])
    kwargs = data.get("kwargs", {})

    action_runner = ActionRunner(action_packs[action_pack])

    if action_name not in action_runner.get_actions():
        return jsonify({"error": "Action not found"}), 404

    try:
        result = action_runner.run_action(action_name, *args, **kwargs)
        return jsonify({"result": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
