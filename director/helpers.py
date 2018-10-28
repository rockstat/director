from inflection import underscore
from prodict import Prodict


def def_val(val, def_val):
    return val if val != None else def_val

def nn(arg):
    """ not nil """
    return arg != None


def isn(arg):
    """ not nil """
    return arg == None


def tar_image_cmd(path):
    """
    Method for build tar image from source path
    """
    # -c create archive mode
    # -C directory In c and r mode, this changes the directory before adding the following files.
    # -X filename Read a list of exclusion patterns from the specified file.
    # --exclude pattern Do not process files or directories that match the specified pattern.
    # tar -C ___ -c -X ___/.dockerignore .
    return ['tar', '-C', f'{path}', '-c', '-X', f'{path}/.dockerignore', '.']


def req_to_bool(v) -> None or bool:
    if v == None:
        return v
    if isinstance(v, bool):
        return bool
    return str(v).lower() in ("yes", "true", "t", "1")


def underdict(obj):
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            key = underscore(key)
            new_dict[key] = underdict(value)
        return new_dict
    # if hasattr(obj, '__iter__'):
    #     return [underdict(value) for value in obj]
    else:
        return obj


def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def merge_dicts(*args):
    if len(args) == 0:
        return
    d = args[0]
    for d2 in args[1:]:
        d.update(d2)
    return d
