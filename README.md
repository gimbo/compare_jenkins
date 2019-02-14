# Two tools for working with Jenkins

(Forked/expanded from
[evilkost/compare_jenkins](https://github.com/evilkost/compare_jenkins))

Two small Jenkins-related tools which I sometimes find useful, particularly when
working on a project with a fluctuating (and possibly nondeterministic) number
of test failures - a less than ideal situation, but one for which these tools
can be handy...

See below for more details, but briefly, we have:

* `jen-compare` - compare two sets of Jenkins test results and report on
  disjoint sets of failing tests between two sets.
* `jen-job-history` - report on the build history of some job: which branches
  and revisions correspond to which builds, etc.  This is sometimes handy for
  working out which builds to target with `jen_compare`.



## Installation / requirements

* These tools require python >= 3.7; if you absolutely have to run this on an
  older version, see the
  [archival](https://github.com/gimbo/gentle-jenkins-tools/tree/archival) tag,
  which is an old version which ought to work with python2.7 (I _think_).

* The best way to install this package is with
  [`pipx`](https://github.com/pipxproject/pipx):

  ```shell
  pipx install --spec <path to package> gentle-jenkins-tools
  ```

* (Note that pipsi _won't_ work, because this package uses
  [`poetry`](https://github.com/sdispater/poetry) not `setuptools`.)

* You may find [`pyenv`](https://github.com/pyenv/pyenv) helpful if you're not
  using it already - it enables you to run whatever versions of python you want,
  in parallel.



## The tools



### `jen-compare`

Use `jen-compare` to compare two sets of Jenkins test results in jenkins, and to
report on the disjoint sets of failing tests between the two sets.

It's probably easiest understood by example...

Suppose we have a `master` branch and a feature branch `xyz`, based off that;
suppose also that Jenkins is set up to test those branches using jobs called
`master` and `feature` respectively.

Then, to compare the results of the builds `master/7` and `feature/42`, say:

```shell
$ jen-compare http://jenkins.host.example/ master/7 feature/42
Fetching failures from left branch
Fetching failures from right branch
Failed in the left branch..: 9
Failed in the right branch.: 12

=== left failed, right passed: 3 ===
tests.test_things.BigThingTest.test_some_property
tests.test_things.BigThingTest.test_weirdness
tests.test_roles.PostmanTest.test_always_knocks_twice

=== left passed, right failed: 2 ===
tests.test_roles.LawyerTest.test_bird_law
tests.test_roles.SecretAgentTest.test_has_tinnitius
```

What we see here:

* First, that the left build (i.e. `master/7`) had 9 failures, whereas the right
  build (i.e.  `feature/42`) had 12.

* Then, we see the 3 tests which failed on the left but not the right - so they
  failed for the `master` branch but not for `xyz` - that suggests that either
  they're fixed in `xyz`, or perhaps they're randomly failing; generally we're
  not so interested in these, however.

* Finally, we see the part we're probably most interested in: the tests which
  failed for `xyz` but not `master`; these are good candidates for being new
  test failures in our `xyz` branch (assuming they're not also random failures -
  we could run them locally to find out, e.g. using
  [testwang](https://github.com/gimbo/testwang)).

Note that in the above example we specified the server explicitly. The server
can be specified via the JEN_COMPARE_DEFAULT_BASE environment variable, in which
case it can be omitted from the args:

```shell
$ export JEN_COMPARE_DEFAULT_BASE=http://jenkins.host.example
$ jen-compare main/7 feature-xyz/42
...
```

See `jen-compare --help` for more.



### `jen-job-history`

Use `jen-job-history` to see the build history of some job: which branches and
  revisions correspond to which builds, etc.

E.g., hitting the same Jenkins server mentioned above, and asking for history of
the `feature` job:

```shell
$ python jen-job-history http://jenkins.host.example feature
  Build  Timestamp              Time  Revision    Branch
  * 339  2019-02-15 10:50:01  ?8m37s  139c9367    xyz
    338  2019-02-15 09:27:01   8m54s  b2f273b1    xyz
    337  2019-02-14 20:10:01   9m25s  ef25c86f    doodah
    336  2019-02-14 17:07:01   8m39s  ad001752    archer
    335  2019-02-14 15:47:01   9m22s  c4832dc6    harvey_birdman
    334  2019-02-14 15:30:23   9m14s  18b2c273    archer
    333  2019-02-14 14:42:23   8m02s  0f8d94f9    xyz
    332  2019-02-14 12:20:50   8m15s  aa49e187    xyz
```

Hopefully that's mainly self-explanatory; things to note:

* The tool retrieves the full history retained on the Jenkins server for the
  specified job - in this case 8 builds.

* Build 339 is still in progress (hence the `*` next to the build number - and
  the `?` next to the time, as that is then an estimate). All the other builds
  have finished.

* This job is configured to run vs many different branches; on other jobs, that
  might not be true, in which case the "Branch" column would be very boring.  Ah
  well.

Again, `JEN_COMPARE_DEFAULT_BASE` can be set as above, in which case the server
argument can be omitted.

See `jen-job-history --help` for more.



## Limitations / future work

A couple of limitations arising because these are "the simplest thing that could
work" to scratch my personal itches...

* The main limitation at the moment is that there's no authentication handling:
  the tools assume your Jenkins installation is wide open and doesn't require
  login.  This is definitely intended future work.

* The other limitation to note is that the tools both make some assumptions
  about the structure of your jobs, i.e. that they're pretty simple, and
  basically just do a single step which runs the tests.  More complex
  jobs/pipelines will almost certainly break these tools.  This is less likely
  to get any attention from me, unless my requirements change drastically.

Definite TODOs:

* Make these tools really easy to install (possibly from PyPI).
* Add authentication to both tools.
* Add a limit argument to `jen-job-history` so it only gets the last `n` builds
  rather than all it can find.
* Some tests would be nice. :-)
