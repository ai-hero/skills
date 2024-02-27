import importlib
from .actions.packs import ActionPack, ActionRunner
from flask import Flask, jsonify, request

app = Flask(__name__)


def load_action_packs():
    action_packs_module = importlib.import_module(
        ".actions", package="packs"
    )  # Adjust the package name
    action_packs = {}

    for attribute_name in dir(action_packs_module):
        attribute = getattr(action_packs_module, attribute_name)
        if (
            isinstance(attribute, type)
            and issubclass(attribute, ActionPack)
            and attribute is not ActionPack
        ):
            # Instantiate the ActionPack subclass with necessary authentication or other initialization parameters
            action_packs[attribute_name] = attribute(
                auth={"key": "value"}
            )  # Replace auth dict with actual required auth parameters

    return action_packs


action_packs = load_action_packs()


@app.route("/get_actions/<action_pack>", methods=["GET"])
def get_actions(action_pack):
    if action_pack not in action_packs:
        return jsonify({"error": "ActionPack not found"}), 404

    action_runner = ActionRunner(action_packs[action_pack])
    actions = action_runner.get_actions()
    return jsonify(actions)


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
