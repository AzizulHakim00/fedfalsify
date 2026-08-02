"""FedFalsify: certificate-guided federated symbolic discovery."""

from .basis import CandidateEquation, TermCatalog
from .benchmarks import (
    BENCHMARKS,
    BenchmarkResult,
    BenchmarkSpec,
    GeneratedBenchmark,
    generate_benchmark,
    run_exception_benchmark,
    run_spurious_correlation_benchmark,
)
from .client import FederatedFalsifierClient
from .data import (
    ClientDataset,
    generate_exception_clients,
    generate_heterogeneous_clients,
    generate_spurious_correlation_clients,
)
from .expression_baselines import TreeModel, TreeSearchOutput, run_tree_search
from .expression_tree import Expr, expression_library, recognized_term
from .privacy import NoisyCertificateClient, SensitivityProbe, leave_one_out_sensitivity
from .replacement import (
    CoreReplacementResult,
    FederatedCoreReplacement,
    ReplacementCertificate,
)
from .server import DiscoveryResult, FedFalsifyDiscovery, RepairDecision
from .statistics import (
    BootstrapInterval,
    McNemarResult,
    mcnemar_exact,
    paired_bootstrap_difference,
    wilson_interval,
)

__all__ = [
    "BENCHMARKS",
    "BenchmarkResult",
    "BenchmarkSpec",
    "BootstrapInterval",
    "CandidateEquation",
    "ClientDataset",
    "CoreReplacementResult",
    "DiscoveryResult",
    "Expr",
    "FedFalsifyDiscovery",
    "FederatedCoreReplacement",
    "FederatedFalsifierClient",
    "GeneratedBenchmark",
    "McNemarResult",
    "NoisyCertificateClient",
    "RepairDecision",
    "ReplacementCertificate",
    "SensitivityProbe",
    "TermCatalog",
    "TreeModel",
    "TreeSearchOutput",
    "expression_library",
    "generate_benchmark",
    "generate_exception_clients",
    "generate_heterogeneous_clients",
    "generate_spurious_correlation_clients",
    "leave_one_out_sensitivity",
    "mcnemar_exact",
    "paired_bootstrap_difference",
    "recognized_term",
    "run_exception_benchmark",
    "run_spurious_correlation_benchmark",
    "run_tree_search",
    "wilson_interval",
]

__version__ = "0.6.0"
