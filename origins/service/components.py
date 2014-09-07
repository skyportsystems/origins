from flask import url_for
from origins.graph import components
from .nodes import Nodes, Node


def prepare(n, r=None):
    n = n.to_dict()

    if not r:
        r = components.resource(n['uuid']).uuid

    n['_links'] = {
        'self': {
            'href': url_for('component', uuid=n['uuid'],
                            _external=True),
        },
        'resource': {
            'href': url_for('resource', uuid=r, _external=True)
        },
    }

    return n


class Components(Nodes):
    module = components

    def prepare(self, n, resource=None):
        return prepare(n, r=resource)

    def get_attrs(self, data):
        return {
            'id': data.get('id'),
            'type': data.get('type'),
            'label': data.get('label'),
            'description': data.get('description'),
            'properties': data.get('properties'),
            'resource': data.get('resource'),
        }


class Component(Node):
    module = components

    def prepare(self, n, resource=None):
        return prepare(n, r=resource)

    def get_attrs(self, data):
        return {
            'type': data.get('type'),
            'label': data.get('label'),
            'description': data.get('description'),
            'properties': data.get('properties'),
        }
