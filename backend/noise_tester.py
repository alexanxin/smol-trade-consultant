"""
Noise Tester - Validate strategy robustness by injecting noise into data.

Implements Samir Varma's validation principle: A robust strategy should degrade
gracefully when noise is added to inputs. If performance crashes immediately with
small noise, the strategy is just fitting random patterns.

Test Process:
1. Take strategy inputs (price, volume, indicators)
2. Add increasing levels of random noise (1%, 5%, 10%, 20%)
3. Run strategy on noisy data
4. Measure performance degradation
5. Calculate robustness score
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional

logger = logging.getLogger("NoiseTester")


class NoiseTester:
    """
    Strategy validation through noise injection.
    
    Varma's principle: If your strategy can't handle a little noise,
    it's not finding real signal - it's just overfitting.
    """
    
    def __init__(self, random_seed: Optional[int] = 42):
        """
        Initialize Noise Tester.
        
        Args:
            random_seed: Random seed for reproducibility
        """
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)
        
        logger.info(f"NoiseTester initialized with seed={random_seed}")
    
    def inject_noise(
        self,
        data: pd.DataFrame,
        noise_level_pct: float,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Inject random noise into data.
        
        Args:
            data: DataFrame with market data
            noise_level_pct: Noise level as percentage (0.01 = 1%)
            columns: Columns to add noise to (if None, uses all numeric columns)
        
        Returns:
            DataFrame with noise added
        """
        noisy_data = data.copy()
        
        # Determine which columns to add noise to
        if columns is None:
            columns = noisy_data.select_dtypes(include=[np.number]).columns.tolist()
        
        # Add Gaussian noise to each column
        for col in columns:
            if col in noisy_data.columns:
                # Calculate noise: mean=0, std=noise_level_pct * column_std
                col_std = noisy_data[col].std()
                noise = np.random.normal(0, noise_level_pct * col_std, size=len(noisy_data))
                noisy_data[col] = noisy_data[col] + noise
                
                # Ensure no negative values for price/volume
                if col in ['open', 'high', 'low', 'close', 'volume', 'price']:
                    noisy_data[col] = noisy_data[col].clip(lower=0)
        
        logger.debug(f"Injected {noise_level_pct*100}% noise into columns: {columns}")
        
        return noisy_data
    
    def run_noise_stress_test(
        self,
        strategy_func: Callable,
        data: pd.DataFrame,
        noise_levels: List[float] = [0.0, 0.01, 0.05, 0.10, 0.20],
        columns: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Run noise stress test on a strategy.
        
        Args:
            strategy_func: Function that takes data and returns performance metric
            data: Clean market data
            noise_levels: List of noise levels to test (as decimals)
            columns: Columns to add noise to
        
        Returns:
            Dict with test results and robustness score
        """
        results = {
            "noise_levels": [],
            "performance": [],
            "degradation_pct": []
        }
        
        baseline_performance = None
        
        for noise_level in noise_levels:
            logger.info(f"Testing with {noise_level*100}% noise...")
            
            # Inject noise (0.0 = baseline, no noise)
            if noise_level == 0.0:
                test_data = data.copy()
            else:
                test_data = self.inject_noise(data, noise_level, columns)
            
            # Run strategy on noisy data
            try:
                performance = strategy_func(test_data)
            except Exception as e:
                logger.error(f"Strategy failed with {noise_level*100}% noise: {e}")
                performance = 0.0
            
            # Store baseline
            if noise_level == 0.0:
                baseline_performance = performance
            
            # Calculate degradation
            if baseline_performance is not None and baseline_performance != 0:
                degradation_pct = ((performance - baseline_performance) / baseline_performance) * 100
            else:
                degradation_pct = 0.0
            
            results["noise_levels"].append(noise_level)
            results["performance"].append(performance)
            results["degradation_pct"].append(degradation_pct)
            
            logger.info(f"  Performance: {performance:.4f} (degradation: {degradation_pct:+.2f}%)")
        
        # Calculate robustness score
        robustness_score = self.calculate_robustness_score(
            results["noise_levels"],
            results["degradation_pct"]
        )
        
        results["robustness_score"] = robustness_score
        results["baseline_performance"] = baseline_performance
        results["passed"] = robustness_score > 0.7  # Pass if score > 0.7
        
        return results
    
    def calculate_robustness_score(
        self,
        noise_levels: List[float],
        degradation_pcts: List[float]
    ) -> float:
        """
        Calculate robustness score based on performance degradation.
        
        A robust strategy should:
        - Maintain performance with small noise (1-5%)
        - Degrade gracefully with larger noise (10-20%)
        - Not crash immediately
        
        Args:
            noise_levels: List of noise levels tested
            degradation_pcts: List of performance degradations
        
        Returns:
            Robustness score (0.0 to 1.0, higher is better)
        """
        if len(noise_levels) < 2:
            return 0.0
        
        # Skip baseline (0% noise)
        noise_levels = noise_levels[1:]
        degradation_pcts = degradation_pcts[1:]
        
        # Calculate average degradation per unit of noise
        # Lower is better (less degradation per % noise)
        avg_degradation_per_noise = np.mean([
            abs(deg) / (noise * 100) 
            for noise, deg in zip(noise_levels, degradation_pcts)
            if noise > 0
        ])
        
        # Convert to score (0-1, where 1 is most robust)
        # If degradation is < 1% per 1% noise, score is high
        # If degradation is > 5% per 1% noise, score is low
        if avg_degradation_per_noise < 1.0:
            score = 1.0
        elif avg_degradation_per_noise > 5.0:
            score = 0.0
        else:
            # Linear interpolation between 1.0 and 5.0
            score = 1.0 - ((avg_degradation_per_noise - 1.0) / 4.0)
        
        logger.info(f"Robustness Score: {score:.2f} (avg degradation: {avg_degradation_per_noise:.2f}% per 1% noise)")
        
        return max(0.0, min(1.0, score))
    
    def generate_noise_report(self, test_results: Dict[str, any]) -> str:
        """
        Generate a human-readable noise test report.
        
        Args:
            test_results: Results from run_noise_stress_test
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("NOISE STRESS TEST REPORT")
        report.append("=" * 60)
        report.append(f"Baseline Performance: {test_results['baseline_performance']:.4f}")
        report.append(f"Robustness Score: {test_results['robustness_score']:.2f} / 1.00")
        report.append(f"Test Result: {'✅ PASSED' if test_results['passed'] else '❌ FAILED'}")
        report.append("")
        report.append("Noise Level | Performance | Degradation")
        report.append("-" * 60)
        
        for noise, perf, deg in zip(
            test_results["noise_levels"],
            test_results["performance"],
            test_results["degradation_pct"]
        ):
            report.append(f"{noise*100:>10.1f}% | {perf:>11.4f} | {deg:>+10.2f}%")
        
        report.append("=" * 60)
        
        # Interpretation
        if test_results["robustness_score"] > 0.8:
            report.append("✅ Excellent: Strategy is highly robust to noise")
        elif test_results["robustness_score"] > 0.6:
            report.append("⚠️  Good: Strategy is reasonably robust")
        elif test_results["robustness_score"] > 0.4:
            report.append("⚠️  Fair: Strategy shows some noise sensitivity")
        else:
            report.append("❌ Poor: Strategy is likely overfitting noise")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def validate_strategy(
        self,
        strategy_func: Callable,
        data: pd.DataFrame,
        min_robustness_score: float = 0.7
    ) -> bool:
        """
        Validate if a strategy passes the noise test.
        
        Args:
            strategy_func: Strategy function to test
            data: Market data
            min_robustness_score: Minimum acceptable robustness score
        
        Returns:
            True if strategy passes, False otherwise
        """
        results = self.run_noise_stress_test(strategy_func, data)
        
        passed = results["robustness_score"] >= min_robustness_score
        
        # Print report
        report = self.generate_noise_report(results)
        logger.info(f"\n{report}")
        
        return passed
