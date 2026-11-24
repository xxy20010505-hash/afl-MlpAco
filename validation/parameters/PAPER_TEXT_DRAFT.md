# Draft for reporting parameter diagnostics

This draft is limited to the diagnostic experiments in this directory. It must not be presented as a FuzzBench sensitivity study or a validation of the original manuscript's results.

## MC sampling and uncertainty bonus

For a seed feature vector x, we perform T stochastic forward passes with Dropout active and calculate the sample mean mu and sample standard deviation s. The scheduling score is q = clip(mu + lambda*s, 0, 1). With the implementation's shared-uniform exploration rule, the acceptance probability is approximately max(epsilon, q), where epsilon = 0.05. For the single-pass control, s is set to zero; this is not an uncertainty estimator. The standard deviation bonus is an exploration heuristic and should not be interpreted as a calibrated confidence bound.

We evaluated T in {1,2,4,8,16,32} using the C inference implementation and one fixed diagnostic MLP. The model was trained on a synthetic six-feature classification task with a fixed training seed. For each of 128 feature vectors and five measurement blocks, an independent set of 256 stochastic predictions provided a Monte Carlo reference, followed by fresh predictions for each candidate T. We report the mean absolute errors of the estimated predictive mean and standard deviation relative to this reference, together with forward-inference latency. These errors quantify sampling approximation rather than predictive classification accuracy. The reference itself is subject to sampling error. The measured values are provided in mc_summary.csv.

To isolate the uncertainty coefficient, we reused the same sampled predictions at T=8 and evaluated lambda in {0,0.25,0.5,1,2}. Increasing lambda raised the theoretical acceptance probability, as expected from the scoring rule. This confirms the direction of the exploration effect but does not establish a benefit in coverage or bug discovery. The values are provided in lambda_summary.csv.

## Global evaporation

Evaporation is applied once per completed ACO mutation sequence to all pheromone entries, before reward deposition, with lower and upper bounds of 0.1 and 100. A transition that receives no subsequent reward decays as max(0.1, tau_0*(1-rho)^k). Thus its unclamped half-life is log(0.5)/log(1-rho). With tau_0=1 and rho=1e-4, the half-life is approximately 6,931 updates and the lower bound is reached after approximately 23,025 updates. These are update-count quantities, not wall-clock times.

We additionally used a deliberately nonstationary synthetic reward task to stress the actual ACO implementation: the rewarded two-operator sequence changed halfway through 30,000 iterations. Ten seeds (1001 through 1010) were used for each rho in {0,1e-5,1e-4,1e-3,1e-2,1e-1}. This task is a mechanism stress test, not a program-coverage benchmark. Recovery after the reward change was poor across several settings. Because the heuristic hit/try counters retain lifetime history, global pheromone evaporation alone does not guarantee adaptation to changing reward distributions. Consequently, these results do not establish an optimal evaporation rate or justify a claim that premature convergence has been eliminated.

## End-to-end pilot

Two instrumented hand-written targets were used in a short pilot with three repetitions per parameter configuration. The candidate configurations varied one parameter at a time around rho=1e-4, T=8, lambda=1. Each run lasted 12 seconds, with reduced warm-up thresholds, one-second model publication/check intervals, and a capped initial havoc stage budget to exercise online learning during the short budget. These settings and targets differ from the main evaluation. We report completed executions, AFL queue size, AFL-deduplicated crashes, skipped seed rounds, and actual model adoptions. Runs without model adoption are explicitly reported as invalid for evaluating neural scheduling. The pilot is intended to detect failures and gross sensitivity, and is insufficient to establish statistically significant efficacy or a globally optimal configuration.

## Candidate defaults

The settings rho=1e-4, T=8, lambda=1 remain provisional engineering defaults. The MC diagnostic can support a latency-versus-estimation-precision trade-off, but the final configuration should be selected on separate validation targets and then held fixed for the main benchmark evaluation. The current stress test motivates further investigation of exploration and heuristic-history adaptation.

## Numerical observations from the recorded runs

In the final microbenchmark performed after the pilot fuzzers stopped, the median inference times for T=4, 8, 16, and 32 were 13, 26, 60, and 116.5 microseconds, respectively. The corresponding predictive-mean MAEs against the 256-sample reference were 0.0343, 0.0233, 0.0199, and 0.0109. The standard-deviation MAEs were 0.0309, 0.0214, 0.0143, and 0.00950. These measurements support considering T=8 as a provisional compromise, but they do not establish an optimum for fuzzing efficacy.

At T=8, increasing lambda from 0 to 1 and 2 increased the average theoretical acceptance probability from 0.3109 to 0.3919 and 0.4728 on the diagnostic feature set. At lambda=2, 0.94% of the scores were clipped at one. This demonstrates the exploration/filtering trade-off without proving a coverage benefit.

All 42 pilot runs exited normally; 41 adopted at least one learned model. The remaining binary-target run at lambda=2 did not adopt a model and cannot evaluate the neural scheduling parameters. No statistical significance or superiority claim is made from these short runs. The host workload was not isolated, and early pilot runs overlapped an earlier diagnostic sweep; final microbenchmark results were remeasured without concurrent pilot fuzzers.

In the nonstationary ACO task, none of the 60 runs discovered the new rewarded complete sequence after the change. Only three of ten runs per evaporation setting had discovered the complete rewarded sequence before the change. This negative result should be reported as a limitation of this particular stress test and implementation, rather than omitted or used to claim an optimal evaporation rate.
