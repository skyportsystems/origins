from __future__ import unicode_literals, absolute_import
from .. import graph
from ..utils import res, build_uri, PATH_SEPERATOR


class Client(object):
    def scheme(self):
        return self.__module__.split('.')[-1]

    def uri(self, path=None):
        host = res(self, 'host')
        port = res(self, 'port')
        scheme = res(self, 'scheme')
        return build_uri(scheme=scheme, host=host, port=port, path=path)


class Node(graph.Node):
    """A node contains attributes and a parent (if not the origin).
    It implements a dict-like interface for accessing the attributes of the
    node.
    """
    __slots__ = ('id', '_rels', '_types', 'props', 'parent', 'client')

    name_attribute = ('name', 'label')
    label_attribute = ('label', 'name')

    def __init__(self, props=None, parent=None, client=None):
        super(Node, self).__init__(props)
        self.parent = parent
        self.client = client
        self.sync()

    def __unicode__(self):
        return unicode(self.name)

    def __bytes__(self):
        return bytes(self.name)

    def __str__(self):
        return str(self.name)

    # TODO rename these methods
    def _contains(self, iterable, klass, type='CONTAINS', relprops=None):
        if relprops is None:
            relprops = {'container': klass.__name__.lower()}
        for props in iterable:
            instance = klass(props, parent=self, client=self.client)
            self.relate(instance, type, relprops)

    def _containers(self, container):
        return self.rels(type='CONTAINS')\
            .filter('container', container).nodes()

    # Hierarchy-based properties relative to the CONTAINS relationship
    @property
    def root(self):
        "Returns the root node."
        if self.parent:
            return self.parent.root
        return self

    @property
    def isroot(self):
        "Returns true if this node is the root."
        return self.root is self

    @property
    def isleaf(self):
        "Returns true if this node is a leaf."
        return len(self.rels(type='CONTAINS')) == 0

    @property
    def relpath(self):
        "Returns the path of relationships from the root to this node."
        path = []
        parent = self.parent
        current = self
        while parent:
            path.append(parent.rels(node=current, type='CONTAINS')[0])
            current = parent
            parent = current.parent
        path.reverse()
        return graph.Rels(path)

    @property
    def path(self):
        "Returns the pathname of this node from the root."
        names = [str(r.start) for r in self.relpath] + [str(self)]
        return PATH_SEPERATOR.join(names)

    @property
    def uri(self):
        "Returns the URI of this node. This is useful as a unique identifier."
        return self.client.uri(self.path)

    @property
    def name(self):
        """Returns the name for this node. The `name_attribute` class
        property can be specified as a list or single attribute name.
        """
        if isinstance(self.name_attribute, (str, unicode)):
            return self.props.get(self.name_attribute)
        value = None
        for attr in self.name_attribute:
            value = self.props.get(attr)
            if value:
                break
        return value

    @property
    def label(self):
        """Returns the label for this node. The `label_attribute` class
        property can be specified as a list or single attribute name.
        """
        if isinstance(self.label_attribute, (str, unicode)):
            return self.props.get(self.label_attribute)
        value = None
        for attr in self.label_attribute:
            value = self.props.get(attr)
            if value:
                break
        return value

    def serialize(self, uri=True, name=True, label=True):
        "Serializes node properties."
        props = self.props.copy()
        if uri:
            props['uri'] = self.uri
        if name:
            props['name'] = self.name
        if label:
            props['label'] = self.label
        return props

    def sync(self):
        "Loads and syncs the immediate relationships relative to this node."
