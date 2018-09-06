Compare test results in jenkins. Detects disjoint sets of failing tests between two branches.

Sample usage:

    ./jen_compare.py http://jenkins.host.example/job main/7 feature-xyz/42

This will compare the results of the main/7 and feature-xyz/42 jobs on the specified server.

The server can be specified via the JEN_COMPARE_DEFAULT_BASE environment variable, in which case the following would work:

    ./jen_compare.py main/7 feature-xyz/42
