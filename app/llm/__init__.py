"""LLM isolation layer (P2-T03).

The ONLY place the platform talks to a language model. Everything else depends
on the abstract ``LLMClient`` interface and the stable JSON contract in
``schema.py``. Defaults to an offline ``FakeLLMClient`` — no real model is
contacted until the prompt/context/output contracts are confirmed.
"""
