# ACO adaptation validation (2026-11-12)

## Method

540 runs: 3 synthetic tasks x 6 policies x 30 seeds (1001-1030). Each run has 30000 two-operator sequences; rho=0.0001. Task 0 remains stationary at (0,2); task 1 switches from (0,2) to (1,3) after 15000 sequences, with a small reward for either matching position; task 2 switches similarly but rewards complete matches only. The original switching task is unchanged. All policies call the actual ACO implementation. Uniform uses epsilon=1 with the same bookkeeping infrastructure, so its timing is not a minimal-rand baseline.

Recent statistics: decay all S,N by gamma=0.999 per completed sequence, then add occurrence counts to N and, for any positive reward, to S. eta=(S+1)/(N+2); the original eta+0.001 term remains. No reward weighting was added. The recent module jointly changes forgetting, smoothing and update timing; these were not separately ablated. Exploration mixes normalized ACO probabilities with epsilon/m.

Recovered means at least one complete match in the second half; this is not proof of sustained recovery. For stationary task 0 it only means a second-half success. Restricted mean delay assigns 15000 to unrecovered runs. Late counts cover the final 5000 sequences. Process CPU timing is descriptive; no CPU affinity or host isolation.

## Original switching task

| config | recovered | n | median_p2 | median_late | restricted_mean_delay | median_us |
| --- | --- | --- | --- | --- | --- | --- |
| original | 1 | 30 | 0.0 | 0.0 | 14549.3667 | 0.9001 |
| recent | 16 | 30 | 73.5 | 73.5 | 9031.9667 | 0.8986 |
| explore05 | 30 | 30 | 359.0 | 151.0 | 3171.7 | 0.9372 |
| combined05 | 30 | 30 | 583.0 | 94.0 | 1654.7333 | 0.9212 |
| combined10 | 30 | 30 | 542.5 | 93.5 | 939.7 | 0.9284 |
| uniform | 30 | 30 | 54.5 | 18.0 | 355.7333 | 0.9365 |

## Other tasks

| task | config | recovered | median_p1 | median_p2 | median_late |
| --- | --- | --- | --- | --- | --- |
| 0 | original | 11 | 0.0 | 0.0 | 0.0 |
| 0 | recent | 30 | 924.0 | 267.5 | 82.0 |
| 0 | explore05 | 30 | 838.0 | 181.0 | 56.0 |
| 0 | combined05 | 30 | 745.5 | 162.0 | 55.0 |
| 0 | combined10 | 30 | 682.0 | 174.0 | 60.0 |
| 0 | uniform | 30 | 50.5 | 52.0 | 17.0 |
| 2 | original | 0 | 14668.0 | 0.0 | 0.0 |
| 2 | recent | 30 | 14358.0 | 11544.5 | 4920.5 |
| 2 | explore05 | 4 | 13273.0 | 0.0 | 0.0 |
| 2 | combined05 | 30 | 13185.5 | 10540.0 | 4500.5 |
| 2 | combined10 | 30 | 11955.5 | 9588.5 | 4079.5 |
| 2 | uniform | 30 | 50.5 | 54.5 | 18.0 |

## Interpretation

The combined 5% policy recovered in 30/30 runs, versus 1/30 original and 16/30 recent-only. Exploration-only also recovered in 30/30, but had fewer second-half successes (median 359 versus 583) and a longer restricted mean delay (3172 versus 1655). In the full-reward-only switching task the combined policy recovered in 30/30 versus 4/30 exploration-only. This supports complementary effects in these tasks, not a universal efficacy claim.

Trade-offs remain: recent-only had more second-half successes in the stationary task (267.5 versus 162 combined05). In task 1 exploration-only had more final-window successes (151 versus 94). Uniform discovered the changed goal sooner but repeated it far less often. Epsilon=0.1 accelerated rediscovery but reduced success counts in some tasks. Neither epsilon nor gamma is established as optimal. 30/30 is a finite-sample observation, not guaranteed recovery.

## Correctness and integration

correctness.txt records exact legacy-output regression with both new mechanisms disabled (excluding CPU timing), prior/decay assertions, and uniform-policy frequency checks. integration-results.json contains the actual AFL async/sync smoke tests. First integration attempt lacked Redis; it exposed an existing dangling redis_ctx after connection failure. That cleanup bug was fixed and the failed attempt remains recorded in integration.log. Retry uses an isolated Redis server. Smoke tests do not measure coverage gains.

## Usage and reproduction

New controls are opt-in: AFL_ACO_RECENT=1 AFL_ACO_GAMMA=0.999 AFL_ACO_EPSILON=0.05. Defaults remain legacy history and epsilon=0 to preserve old experiments. Run python3 validation/aco_adaptation/run.py, regression.py and analyze.py from the repository root (use each full path). run.py overwrites same-name results: archive before rerunning. plan.json records configurations and shuffled order; source_sha256.json records source hashes; traces/ contains all learning curves.

Next: compare original, exploration-only and combined05 on real targets with independent coverage measurement and equal budgets. Do not combine these new-version results with the previous manuscript data.
