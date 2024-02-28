import importlib
import pkgutil
import yaml
import falcon
from falcon import media
from actions.schema import ActionPack, ActionRunner


def load_action_packs(package="actions.packs"):
    action_packs = {}
    package = importlib.import_module(package)

    def load_from_package(package):
        for loader, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            module = importlib.import_module(module_name)
            if not is_pkg:
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if (
                        isinstance(attribute, type)
                        and issubclass(attribute, ActionPack)
                        and attribute is not ActionPack
                    ):
                        action_packs[attribute_name] = attribute
            else:
                load_from_package(module)

    load_from_package(package)
    print(action_packs)
    return action_packs


action_packs = load_action_packs()


class ActionsRoute:
    """Route to get all actions from an ActionPack."""

    def on_get(self, req, resp, action_pack):
        """Get all actions from an ActionPack."""
        if action_pack not in action_packs:
            resp.media = {"error": "ActionPack not found"}
            resp.status = falcon.HTTP_404
            return

        action_runner = ActionRunner(action_packs[action_pack](auth={}))
        actions = action_runner.get_actions()
        resp.content_type = "text/yaml"
        resp.body = yaml.dump(actions)
        resp.status = falcon.HTTP_200


class OneActionRoute:
    """Route to run a single action from an ActionPack."""

    def on_post(self, req, resp, action_pack, action_name):
        """Run a single action from an ActionPack."""
        if action_pack not in action_packs:
            resp.media = {"error": "ActionPack not found"}
            resp.status = falcon.HTTP_404
            return

        data = req.media

        # Extract headers starting with 'X-Key-'
        auth = {k: v for k, v in req.headers.items() if k.startswith("X-KEY-")}

        action_runner = ActionRunner(action_packs[action_pack](auth=auth))

        if action_name not in action_runner.get_actions():
            resp.media = {"error": "Action not found"}
            resp.status = falcon.HTTP_404
            return

        try:
            result = action_runner.run_action(action_name, data)
            resp.media = {"result": result}
        except ValueError as e:
            resp.media = {"error": str(e)}
            resp.status = falcon.HTTP_400


app = falcon.App()
app.add_route("/v1/actions/{action_pack}", ActionsRoute())
app.add_route("/v1/actions/{action_pack}/{action_name}/run", OneActionRoute())
