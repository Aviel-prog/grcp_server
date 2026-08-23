from src.core.engine import Loader

# TODO clean files - DONE
# TODO clean names
# TODO implement validatetors
# TODO implement is_exist
# TODO plugins - DONE
# TODO create umls
# TODO cr - from the claude logs and detailng prompt - solide, ded code, code smell, production ready
# TODO create git tree and plan

if __name__ == '__main__':
    with Loader.load_plugin("math_plugin") as math_p:
        print(math_p.add(1, 2))
