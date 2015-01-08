import json
import logging

PACK_PREFIX = 'origins:'

UNPACK_MAP = {
    'prov:type': 'type',
    'prov:label': 'label'
}

PACK_MAP = {
    'type': 'prov:type',
    'label': 'prov:label',
}

logger = logging.getLogger(__name__)


def pack(a):
    """Takes a dict and merges the nested 'properties' dict into the output.
    Top-level keys are put in the `origins` namespace.
    """
    b = {}

    if not a:
        return b

    for k, v in a.items():
        if v is None:
            continue

        # Special case for properties
        if k == 'properties':
            for _k, _v in v.items():
                if _v is not None:
                    # JSON encode nested maps
                    if isinstance(_v, dict):
                        _v = json.dumps(_v)
                    b[_k] = _v

        # Everything else is prefixed
        elif k in PACK_MAP:
            b[PACK_MAP[k]] = v
        elif k:
            b['{}{}'.format(PACK_PREFIX, k)] = v

    return b


def unpack(b):
    """Takes a dict and unpacks non-Origins properties into a nested
    'properties' dict.
    """
    if not b:
        return

    a = {}
    p = {}

    # Most Neo4j results are nested as lists
    if isinstance(b, (list, tuple)):
        b = b[0]

    low = len(PACK_PREFIX)

    for k, v in b.items():
        if k in UNPACK_MAP:
            a[UNPACK_MAP[k]] = v
        elif k.startswith(PACK_PREFIX):
            a[k[low:]] = v
        else:
            # JSON decode nested maps and arrays
            if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                try:
                    v = json.loads(v)
                except ValueError:
                    pass

            p[k] = v

    a['properties'] = p or None

    return a
