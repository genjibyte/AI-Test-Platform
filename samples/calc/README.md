# sample: calc

A minimal single-module JUnit5 Maven project used as the Phase 1 end-to-end
fixture (P1-T11). Original tests are green; it has one partially-covered branch
(`max`) so coverage is a meaningful non-trivial number.

Used by `tests/e2e/test_phase1_e2e.py::test_real_build_and_parse`, which runs
real `mvn test` + JaCoCo against this directory and parses the real reports.
