import unittest
import pkg_resources
from gpc.fsdb import Database
import os
import tempfile
import shutil
import logging

logging.basicConfig(level=logging.DEBUG)

class TestFSDB(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.dbdir = os.path.join(self.tempdir, 'my_db')
        Database.create(self.dbdir)

        schema = '''
            create table some_table (
              some_id text primary key,
              some_text text
              );
            '''

        with Database(self.dbdir) as db:
            with db.transaction() as tr:
                tr.executescript(schema)
                tr.execute(
                    'INSERT OR ABORT INTO some_table (some_id, some_text) '
                    'VALUES (?, ?)', ('abc', 'def'))

    def test_write_read(self):
        with Database(self.dbdir) as db:
            with db.transaction() as tr:
                row, = tr.execute('SELECT * FROM some_table')
                self.assertTrue(row == ('abc', 'def'))

    def tearDown(self):
        shutil.rmtree(self.tempdir)

if __name__ == '__main__':
    unittest.main()