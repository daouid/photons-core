# coding: spec

from photons_transport.targets.script import AFRWrapper, ScriptRunner

from photons_app.errors import PhotonsAppError, BadRunWithResults
from photons_app import helpers as hp

from delfick_project.norms import sb
from unittest import mock
import asyncio
import pytest


class Sem:
    def __init__(self, limit):
        self.limit = limit

    def __eq__(self, other):
        return isinstance(other, asyncio.Semaphore) and other._value == self.limit


describe "AFRWrapper":

    @pytest.fixture()
    def V(self):
        class V:
            called = []

            afr = mock.Mock(name="afr")

            res1 = mock.Mock(name="res1")
            res2 = mock.Mock(name="res2")

            @hp.memoized_property
            def script(s):
                class FakeScript:
                    async def run_with(fs, *args, **kwargs):
                        s.called.append(("run_with", args, kwargs))
                        yield s.res1
                        yield s.res2

                return FakeScript()

            @hp.memoized_property
            def target(s):
                class FakeTarget:
                    async def args_for_run(fs, *args, **kwargs):
                        s.called.append(("args_for_run", args, kwargs))
                        return s.afr

                    async def close_args_for_run(fs, *args, **kwargs):
                        s.called.append(("close_args_for_run", args, kwargs))

                return FakeTarget()

        return V()

    async it "does not impose a limit if limit is given as None", V:
        assert V.called == []

        a = mock.Mock(name="a")
        kwargs = {"b": a, "limit": None}
        args_for_run = mock.NonCallableMock(name="args_for_run")

        async with AFRWrapper(V.target, args_for_run, kwargs) as afr:
            assert afr is args_for_run

        assert kwargs == {"b": a, "limit": None}
        assert V.called == []

    async it "turns limit into a semaphore", V:
        a = mock.Mock(name="a")
        kwargs = {"b": a, "limit": 50}
        args_for_run = mock.NonCallableMock(name="args_for_run")

        async with AFRWrapper(V.target, args_for_run, kwargs) as afr:
            assert afr is args_for_run

        assert kwargs == {"b": a, "limit": Sem(50)}
        assert V.called == []

    async it "passes on limit if it has acquire", V:
        a = mock.Mock(name="a")
        limit = mock.NonCallableMock(name="limit", spec=["acquire"])
        kwargs = {"b": a, "limit": limit}
        args_for_run = mock.NonCallableMock(name="args_for_run")

        async with AFRWrapper(V.target, args_for_run, kwargs) as afr:
            assert afr is args_for_run

        assert kwargs == {"b": a, "limit": limit}
        assert V.called == []

    async it "passes on limit if it is already a Semaphore", V:
        a = mock.Mock(name="a")
        limit = asyncio.Semaphore(1)
        kwargs = {"b": a, "limit": limit}
        args_for_run = mock.NonCallableMock(name="args_for_run")

        async with AFRWrapper(V.target, args_for_run, kwargs) as afr:
            assert afr is args_for_run

        assert kwargs == {"b": a, "limit": limit}
        assert V.called == []

    async it "creates and closes the afr if none provided", V:
        a = mock.Mock(name="a")
        limit = asyncio.Semaphore(1)
        kwargs = {"b": a}

        async with AFRWrapper(V.target, sb.NotSpecified, kwargs) as afr:
            assert afr is V.afr
            V.called.append(("middle", kwargs))

        assert V.called == [
            ("args_for_run", (), {}),
            ("middle", {"b": a, "limit": Sem(30)}),
            ("close_args_for_run", (V.afr,), {}),
        ]

describe "ScriptRunner":

    @pytest.fixture()
    def V(self):
        class V:
            afr = mock.Mock(name="afr")
            res1 = mock.Mock(name="res1")
            res2 = mock.Mock(name="res2")
            called = []
            target = mock.Mock(name="target", spec=[])

            @hp.memoized_property
            def script(s):
                class FakeScript:
                    async def run_with(fs, *args, **kwargs):
                        s.called.append(("run_with", args, kwargs))
                        yield s.res1
                        yield s.res2

                return FakeScript()

            @hp.memoized_property
            def runner(s):
                return ScriptRunner(s.script, s.target)

            @hp.memoized_property
            def FakeTarget(s):
                class FakeTarget:
                    async def args_for_run(fs, *args, **kwargs):
                        s.called.append(("args_for_run", args, kwargs))
                        return s.afr

                    async def close_args_for_run(fs, *args, **kwargs):
                        s.called.append(("close_args_for_run", args, kwargs))

                return FakeTarget

        return V()

    async it "takes in script and target":
        script = mock.Mock(name="script")
        target = mock.Mock(name="target")

        runner = ScriptRunner(script, target)

        assert runner.script is script
        assert runner.target is target

    describe "run_with":
        async it "does nothing if no script":
            runner = ScriptRunner(None, mock.NonCallableMock(name="target"))
            reference = mock.Mock(name="reference")

            got = []
            async for info in runner.run_with(reference):
                got.append(info)

            assert got == []

        async it "calls run_with on the script", V:
            assert V.called == []

            a = mock.Mock(name="a")
            reference = mock.Mock(name="reference")
            args_for_run = mock.NonCallableMock(name="args_for_run", spec=[])

            found = []
            async for info in V.runner.run_with(reference, args_for_run=args_for_run, b=a):
                found.append(info)

            assert found == [V.res1, V.res2]
            assert V.called == [("run_with", (reference, args_for_run), {"b": a, "limit": Sem(30)})]

        async it "can create an args_for_run", V:
            a = mock.Mock(name="a")
            reference = mock.Mock(name="reference")

            V.runner.target = V.FakeTarget()

            found = []
            async for info in V.runner.run_with(reference, b=a):
                found.append(info)

            assert found == [V.res1, V.res2]
            assert V.called == [
                ("args_for_run", (), {}),
                ("run_with", (reference, V.afr), {"b": a, "limit": Sem(30)}),
                ("close_args_for_run", (V.afr,), {}),
            ]

    describe "run_with_all":
        async it "calls run_with on the script", V:
            assert V.called == []

            a = mock.Mock(name="a")
            reference = mock.Mock(name="reference")
            args_for_run = mock.NonCallableMock(name="args_for_run", spec=[])

            found = await V.runner.run_with_all(reference, args_for_run=args_for_run, b=a)

            assert found == [V.res1, V.res2]
            assert V.called == [("run_with", (reference, args_for_run), {"b": a, "limit": Sem(30)})]

        async it "raises BadRunWithResults if we have risen exceptions", V:
            error1 = PhotonsAppError("failure")

            class FakeScript:
                async def run_with(s, *args, **kwargs):
                    V.called.append(("run_with", args, kwargs))
                    yield V.res1
                    raise error1

            runner = ScriptRunner(FakeScript(), V.FakeTarget())

            assert V.called == []

            a = mock.Mock(name="a")
            reference = mock.Mock(name="reference")

            try:
                await runner.run_with_all(reference, b=a)
                assert False, "Expected error"
            except BadRunWithResults as error:
                assert error.kwargs["results"] == [V.res1]
                assert error.errors == [error1]

            assert V.called == [
                ("args_for_run", (), {}),
                ("run_with", (reference, V.afr), {"b": a, "limit": Sem(30)}),
                ("close_args_for_run", (V.afr,), {}),
            ]
