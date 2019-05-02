from typing import Iterable, Sequence, Mapping, Callable, List, Set, Optional

from typing_extensions import Protocol

import datetime


class Environment(Protocol):
    def destroy(self):
        ...


class Loc(Protocol):
    ...


class Digest(Protocol):
    ...


class Task(Protocol):
    out_locs: Iterable[Loc]

    def run(self, env: Environment):
        ...


class Calc(Protocol):
    task: Task
    inputs: Mapping[Loc, Digest]


class Result(Protocol):
    calc: Calc
    loc: Loc
    digest: Digest
    opinion: Optional[bool]


class Comp(Protocol):
    task: Task
    inputs: Mapping[Loc, Comp]
    out_loc: Loc


class Log(Protocol):
    def get_result(self, calc: Calc, out_loc: Loc) -> Digest:
        ...

    def get_calc(self, comp: Comp) -> Calc:
        ...

    def save_response(
        self, comp: Comp, digest: Digest, time: datetime.datetime
    ):
        ...

    def save_run(
        self,
        calc: Calc,
        results: Mapping[Loc, Digest],
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ):
        ...


class Storage(Protocol):
    def can_restore(self, digest: Digest) -> bool:
        ...

    def restore(self, env: Environment, loc: Loc, digest: Digest):
        ...

    def store(self, env: Environment, loc: Loc) -> Digest:
        ...
