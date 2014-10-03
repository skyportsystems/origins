import unittest
import logging
from origins.graph import neo4j


class MockHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }


class Neo4jTestCase(unittest.TestCase):
    def setUp(self):
        neo4j.client.purge()

    def test_batch(self):
        with neo4j.client.transaction(batch_size=2) as tx:
            tx.send([{
                'statement': 'CREATE ({ props })',
                'parameters': {'props': {'foo': 1}},
            }, {
                'statement': 'CREATE ({ props })',
                'parameters': {'props': {'foo': 2}},
            }, {
                'statement': 'CREATE ({ props })',
                'parameters': {'props': {'foo': 3}},
            }])

            self.assertEqual(tx._batches, 2)

        self.assertEqual(neo4j.tx.send('MATCH (n) RETURN count(n)')[0][0], 3)

    def test_rollback(self):
        tx = neo4j.client.transaction()

        # Create node
        tx.send('CREATE ({})')

        # Visibility in transaction
        self.assertEqual(len(tx.send('MATCH (n) RETURN n')), 1)

        tx.rollback()

        # Change not committed
        self.assertEqual(len(neo4j.tx.send('MATCH (n) RETURN n')), 0)

    def test_nesting(self):
        tx = neo4j.client.transaction()

        with tx as tx1:
            self.assertEqual(tx1._depth, 1)

            with tx1 as tx2:
                self.assertEqual(tx2._depth, 2)

                with tx2 as tx3:
                    self.assertEqual(tx3._depth, 3)

                    tx3.send('CREATE (n)')

                self.assertEqual(tx2._depth, 2)
                self.assertFalse(tx2._closed)

            self.assertEqual(tx1._depth, 1)
            self.assertFalse(tx1._closed)

        self.assertIsNotNone(neo4j.tx.send('MATCH (n) RETURN id(n)')[0][0])

    def test_autocommit(self):
        tx = neo4j.client.transaction(autocommit=True)

        with tx as tx1:
            tx1.send('CREATE (n)')

            with tx1 as tx2:
                tx2.send('CREATE (n)')

            tx1.rollback()

        self.assertEqual(tx._depth, 0)
        tx.send('CREATE (n)')
        r = tx.send('MATCH (n) RETURN n')

        self.assertEqual(len(r), 1)

    def test_defer(self):
        tx = neo4j.client.transaction()

        data = tx.send('CREATE (n {foo: 1}) RETURN n', defer=True)
        self.assertIsNone(data)

        data = tx.send('CREATE (n {foo: 2}) RETURN n', defer=True)
        self.assertIsNone(data)

        self.assertEqual(len(tx._queue), 2)

        data = tx.commit()

        self.assertEqual(len(tx._queue), 0)

        self.assertEqual(len(data), 2)

    def test_uncommitted(self):
        handler = MockHandler(logging.ERROR)
        neo4j.logger.addHandler(handler)

        tx = neo4j.client.transaction()

        # Uncommitted
        tx.send('CREATE (n)')

        self.assertTrue(tx.commit_uri)

        # Unsent
        tx.send('CREATE (n)', defer=True)

        # Mimic call on exit
        neo4j._transaction_exit(tx)

        self.assertEqual(len(handler.messages['error']), 2)

        # Remove handler for subsequent tests
        neo4j.logger.removeHandler(handler)
