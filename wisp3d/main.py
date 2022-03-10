from wisp3d.pegboard.pegboard_script import PegboardScript
from wisp3d.script import ScriptInput

if __name__ == "__main__":
    with open("config.yml", "rt") as f:
        script_input = ScriptInput.from_yaml(f.read())

    build = PegboardScript().create_build(script_input)
    build.resolve_all()
