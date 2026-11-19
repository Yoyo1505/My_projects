# Budget Allocation Auction: key results

Simulation, not real data. Valuations are simulated; only the overspend money and ratio come from the synthetic demo parquet. N = 240 units, K = 30 slots, B = 480 slots, seed 2026.

1. **VCG truthfulness:** 0 violations in 2000 random unit-misreport pairs. Raw max gain 1.1e-13 (floating-point noise).
2. **Other mechanisms, same test:** Uniform price 2 violations (max gain 0.0006); first price 378 (18.9%, max gain 1.82); proportional 1001 (50.1%, max gain 3.31).
3. **Truthful efficiency:** VCG, first price and uniform price reach 1.0000 of the optimum; proportional reaches 0.9901.
4. **Random inflation U[1,2] (20 draws):** VCG efficiency 0.9780 +/- 0.0016; proportional 0.9811 +/- 0.0015. Inflation reduces VCG efficiency too, because VCG controls incentives only.
5. **Best response (one simultaneous round):** VCG best response is truth for all units; first price has 206 units with a profitable deviation (efficiency 0.9796); proportional has all 240 units deviating (mean gain 2.05).
6. **VCG revenue:** 318.50 money units, 66.4% of the budget and 66.4% of the total true value allocated. VCG is not budget-balanced; the planner keeps the surplus unless it rebates it, and no rebate design is tested here.
7. **Individual rationality:** no truthful unit has negative utility under any mechanism (minimum utility 0 for VCG, first price and uniform; 0.31 for proportional).
8. **Number of units:** VCG truthful efficiency is 1.0000 for N = 24 to 480; under inflation it stays within 0.972 to 0.979.
9. **Budget size:** under inflation, VCG efficiency rises from 0.939 (B = 60) to 0.998 (B = 1920). Proportional truthful efficiency is non-monotone (0.933 at B = 240, 0.990 at B = 480); the cause was not investigated.

Caveats:
- Valuations and replication noise are simulated. The only data-derived inputs are the overspend money (relative scale 0.96 to 1.04) and the overspend ratio.
- The overspend ratio is exactly 1.03 for all six centers, so the decay rule gives d_c = 0.75 for every center. The results do not depend on the real ratio.
- Truthfulness is tested on 2000 sampled pairs with a scale-and-decay misreport family. This supports the theory but does not prove it.
- Efficiency gaps are small (at most about 2 percent under inflation) because the market is homogeneous in decay.
- Inflation and sweep results use 10 to 20 random draws on a single market seed.
