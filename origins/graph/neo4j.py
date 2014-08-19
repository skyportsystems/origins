import os
import math
import json
import logging
import requests
from origins import config


logger = logging.getLogger(__name__)


# Default URI to Neo4j REST endpoint
NEO4J_HOST = os.environ.get('ORIGINS_NEO4J_HOST',
                            config.options['neo4j_host'])

NEO4J_PORT = os.environ.get('ORIGINS_NEO4J_PORT',
                            config.options['neo4j_port'])

DEFAULT_URI = 'http://{}:{}/db/data/'.format(NEO4J_HOST, NEO4J_PORT)

# Default number of statements that will be sent in one request
DEFAULT_BATCH_SIZE = 100

# Endpoint for opening a transaction
TRANSACTION_URI_TMPL = '{}transaction'

# Endpoint for the single transaction
SINGLE_TRANSACTION_URI_TMPL = '{}transaction/commit'

# Supported result formats
RESULT_FORMATS = {'row', 'graph', 'REST'}

# Required headers
HEADERS = {
    'accept': 'application/json; charset=utf-8',
    'content-type': 'application/json',
    'x-stream': 'true',
}


class Neo4jError(Exception):
    def __init__(self, errors, *args):
        if isinstance(errors, list):
            message = []

            for error in errors:
                error.setdefault('stackTrace', '')
                message.append('{code}: {message}\n{stackTrace}'
                               .format(**error))

            message = '\n'.join(message)
        else:
            message = errors

        super(Neo4jError, self).__init__(message, *args)


def _normalize_results(response, keys=True):
    if not response:
        return

    result = []

    # Raw results contained in a list..
    for results in response:
        data = results['data']
        columns = results['columns']

        for row in data:
            row = row['row']

            if keys:
                if row and isinstance(row[0], dict):
                    row = row[0]
                elif isinstance(row, list):
                    row = dict(zip(columns, row))

            result.append(row)

    return result


def _normalize_statements(statements, parameters):
    if not statements:
        return []

    # Statement with parameters
    if isinstance(statements, dict):
        return [statements]

    if isinstance(statements, (list, tuple)):
        _statements = []

        for x in statements:
            _statements.extend(_normalize_statements(x, parameters))

        return _statements

    # Bare statement
    return [{
        'statement': str(statements),
        'parameters': parameters,
    }]


def _normalize_formats(formats):
    if isinstance(formats, str):
        formats = [formats]

    invalid = [f for f in formats if f not in RESULT_FORMATS]

    if invalid:
        raise Neo4jError('unkown support format(s): {}'
                         .format(', '.join(invalid)))

    return formats


def _merge_response(output, data):
    if output is None:
        return data

    output['results'].extend(data['results'])
    output['errors'].extend(data['errors'])

    if 'transaction' in data:
        output['transaction'] = data['transaction']

    return output


def _send_request(url, payload):
    "Sends a request to the server."
    # Prevent overhead of serialization
    if logger.level <= logging.DEBUG:
        logger.debug(json.dumps(payload, indent=4))

    data = json.dumps(payload)
    resp = requests.post(url, data=data, headers=HEADERS)

    resp.raise_for_status()
    resp_data = resp.json()

    if resp_data['errors']:
        raise Neo4jError(resp_data['errors'])

    return resp, resp_data


class Client(object):
    def __init__(self, uri=DEFAULT_URI):
        self.uri = uri

    def transaction(self, batch_size=None):
        return Transaction(self.uri, batch_size)

    def send(self, *args, **kwargs):
        batch_size = kwargs.pop('batch_size', None)
        tx = Transaction(self.uri, batch_size)
        return tx.commit(*args, **kwargs)


class Transaction(object):
    def __init__(self, client=None, batch_size=None):
        if not client:
            client = Client()
        elif isinstance(client, str):
            client = Client(client)

        if not batch_size:
            batch_size = DEFAULT_BATCH_SIZE

        self.client = client
        self.transaction_uri = TRANSACTION_URI_TMPL.format(client.uri)
        self.commit_uri = None
        self.batch_size = batch_size
        self.batches = 0

        # transaction is committed or rolled back
        self._closed = False
        # track the depth of a transaction to prevent it from being comitted in
        # sub-context managers
        self._depth = 0

    def __enter__(self):
        self._depth += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._depth -= 1

        if not self._closed and self._depth == 0:
            if exc_type:
                if self.commit_uri:
                    self.rollback()
            else:
                self.commit()

    def _send(self, url, statements=None, parameters=None, formats=None):
        if self._closed:
            raise Neo4jError('transaction closed')

        statements = _normalize_statements(statements, parameters)

        if formats:
            formats = _normalize_formats(formats)

        resp_data = None

        # Send at least one request
        batches = max(1, int(math.ceil(len(statements) / self.batch_size)))

        for i in range(batches):
            logger.info('sending batch {}/{} to {}'
                        .format(i + 1, batches, url))

            start, end = i * self.batch_size, (i + 1) * self.batch_size

            data = {'statements': statements[start:end]}

            if formats:
                data['resultDataContents'] = formats

            resp, _resp_data = _send_request(url, data)

            resp_data = _merge_response(resp_data, _resp_data)

            # Implicit switch to transaction URL
            if 'location' in resp.headers:
                url = self.transaction_uri = resp.headers['location']

            self.batches += 1

        return resp_data

    def send(self, statements, parameters=None, formats=None, raw=False,
             keys=False):
        """Sends statements to an existing transaction or opens a new one.

        This must be followed by `commit` or `rollback` to close the
        transaction, otherwise the transaction will timeout on the server
        and implicitly rolled back.
        """
        data = self._send(self.transaction_uri, statements,
                          parameters=parameters, formats=formats)

        if 'commit' in data:
            if not self.commit_uri:
                logger.info('begin: {}'.format(data['commit']))

            self.commit_uri = data['commit']

        if raw:
            return data

        return _normalize_results(data['results'], keys=keys)

    def commit(self, statements=None, parameters=None, formats=None, raw=False,
               keys=False):
        "Commits an open transaction or performs a single transaction request."
        if self.commit_uri:
            uri = self.commit_uri
        else:
            uri = SINGLE_TRANSACTION_URI_TMPL.format(self.client.uri)

        data = self._send(uri, statements, parameters=parameters,
                          formats=formats)

        logger.info('commit: {}'.format(uri))

        self._closed = True

        if raw:
            return data

        return _normalize_results(data['results'], keys=keys)

    def rollback(self):
        if not self.commit_uri:
            raise Neo4jError('no pending transaction')

        requests.delete(self.transaction_uri, headers=HEADERS)
        logger.info('rollback: {}'.format(self.transaction_uri))

        self._closed = True


def send(statements, parameters=None, formats=None, uri=None, raw=False,
         keys=False, batch_size=None):
    """Sends a single request to the Neo4j transaction endpoint.

    One or more statements can be given, formats including: `row`, `graph`,
    and `REST` can be specified (default is `row`).
    """
    with Transaction(uri, batch_size) as tx:
        return tx.commit(statements, parameters=parameters, formats=formats,
                         raw=raw, keys=keys)


def purge(*args, **kwargs):
    "Deletes all nodes and relationships."

    result = send('START n=node(*) '
                  'OPTIONAL MATCH (n)-[r]-() '
                  'DELETE r, n '
                  'RETURN count(distinct r), count(distinct n)',
                  *args, **kwargs)

    return {
        'nodes': result[0][0],
        'relationships': result[0][1],
    }


def summary(pretty=False):
    "Returns a summary of relationships in graph."
    return send('OPTIONAL MATCH (s)-[r]->(e) '
                'RETURN labels(s), count(distinct s), type(r), '
                'labels(e), count(distinct e)'
                'ORDER BY labels(s)[0], labels(e)[0], type(r)')