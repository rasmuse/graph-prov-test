import os
import sqlite3
import logging
import pkg_resources
import boyle
import attr

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 'v0.0.0'

class Log:

    @staticmethod
    def create(path):
        """
        Create a new Log database.

        Args:
            path (str): Where to create the database.
        """
        schema_path = pkg_resources.resource_filename(
            __name__, "resources/schema-{}.sql".format(SCHEMA_VERSION))

        with open(schema_path, 'r') as f:
            schema_script = f.read()

        conn = sqlite3.connect(path)

        with conn:
            conn.executescript(schema_script)

        conn.close()

    def __init__(self, path):
        if not os.path.exists(path):
            Log.create(path)
        self.conn = sqlite3.connect(path)

    def close(self):
        self.conn.close()

    def save_calc(self, calc):
        with self.conn:
            self.conn.execute(
                'INSERT OR IGNORE INTO calc(calc_id, task_id) '
                'VALUES (?, ?)',
                (calc.calc_id, calc.task.task_id))

            self.conn.executemany(
                'INSERT OR IGNORE INTO input (calc_id, instr_id, digest) '
                'VALUES (?, ?, ?)',
                [
                    (calc.calc_id, inp.instr.instr_id, inp.digest)
                    for inp in calc.inputs
                ])

    def _def_exists(self, d):
        self.conn.execute(
            'SELECT COUNT(def_id) FROM def WHERE (def_id = ?)',
            (d.def_id,))

        return cur.fetchone() != None

    def save_def(self, d):
        for p in d.parents:
            if not _def_exists(p):
                raise ValueError(
                    f'parent {p} of definition {d} must be saved first')

        self.save_calc(d.calc)

        with self.conn:
            self.conn.execute(
                'INSERT OR IGNORE INTO def(def_id, calc_id, instr_id) '
                'VALUES (?, ?, ?)',
                (d.def_id, d.calc.calc_id, d.instr.instr_id))

            self.conn.executemany(
                'INSERT OR IGNORE INTO parent(def_id, parent_id) '
                'VALUES (?, ?)',
                [(d.def_id, p.def_id) for p in d.parents])

    def save_user(self, user):
        with self.conn:
            self.conn.execute(
                'INSERT INTO user(user_id, name) VALUES(?, ?)',
                (user.user_id, user.name))

    def get_user(self, user_id):
        q = self.conn.execute(
            'SELECT name FROM user WHERE (user_id = ?)',
            (user_id,)
            )
        name, = q.fetchone()
        return boyle.User(user_id=user_id, name=name)

    def save_run(self, run):
        self.save_calc(run.calc)
        self.save_user(run.user)

        with self.conn:
            self.conn.execute(
                'INSERT INTO run '
                '(run_id, calc_id, user_id, start_time, end_time) '
                'VALUES (?, ?, ?, ?, ?)',
                (
                    run.run_id,
                    calc.calc_id,
                    user.user_id,
                    run.start_time,
                    run.end_time
                    )
                )

            self.conn.executemany(
                'INSERT OR IGNORE INTO result (run_id, instr_id, digest) '
                'VALUES (?, ?, ?)',
                [
                    (run.run_id, resource.instr.instr_id, resource.digest)
                    for resource in run.results
                ])

    def _get_opinions_by_resource(self, calc, instr):
        query = self.conn.execute(
            'SELECT DISTINCT digest, trust.user_id, correct FROM result '
            'INNER JOIN run USING (run_id) '
            'LEFT OUTER JOIN trust USING (calc_id, instr_id, digest) '
            'WHERE (instr_id = ? AND calc_id = ?)',
            (instr.instr_id, calc.calc_id))

        opinions = {}
        logger.debug('Getting opinions')
        for digest, user_id, correct in query:
            logger.debug(
                f'digest: {digest}, user_id: {user_id}, correct: {correct}')
            resource = boyle.Resource(instr=instr, digest=digest)
            if not resource in opinions:
                opinions[resource] = {}
            if user_id:
                opinions[resource][user_id] = correct

        return opinions

    def get_result(self, calc, instr, user):
        opinions_by_resource = self._get_opinions_by_resource(calc, instr)

        def is_candidate(resource):
            opinions = opinions_by_resource[resource]

            # A result is a candidate if there are no explicit opinions
            if not opinions:
                return True

            # If the user has an explicit opinion, that trumps everything else
            if user.user_id in opinions:
                return opinions[user.user_id]

            # Otherwise, let's see what others think
            # (if we come here, there must be at least one other opinion)
            those_in_favor = {
                user_id for user_id, correct in opinions.items() if correct
                }

            return True if those_in_favor else False

        candidates = [r for r in opinions_by_resource if is_candidate(r)]

        # If there is no digest left, nothing is found.
        # If there is exactly one left, it can be used.
        # If there is more than one left, there is a conflict.

        if not candidates:
            raise NotFoundException()
        elif len(candidates) == 1:
            match, = candidates
            return match
        else:
            raise ConflictException(candidates)

    def get_calculation(self, d, user):
        inputs = [
            self.get_result(self.get_calculation(p.calc, user), p.instr, user)
            for p in d.parents
            ]
        return Calculation(inputs=inputs, task=d.task)


    def get_storage_meta(self, resource):
        raise NotImplementedError()