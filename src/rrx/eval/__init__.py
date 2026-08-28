"""Evaluation-orchestration package.

Stage A scope only: drives the already-frozen A3-D policy
(`rrx.agent.policy.a3d_policy`) through the already-frozen A3 runner
(`rrx.harness.runner.run_episode_a3`) over the official `dev` split and
produces a reproducible raw result. No comparator arms, no §7 success-
criteria judgement, no simulator/policy changes. See `rrx.eval.runner`.
"""

from __future__ import annotations
