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
from .server import DiscoveryResult, FedFalsifyDiscovery, RepairDecision

__all__ = [
    "BENCHMARKS",
    "BenchmarkResult",
    "BenchmarkSpec",
    "CandidateEquation",
    "ClientDataset",
    "DiscoveryResult",
    "FedFalsifyDiscovery",
    "FederatedFalsifierClient",
    "GeneratedBenchmark",
    "RepairDecision",
    "TermCatalog",
    "generate_benchmark",
    "generate_exception_clients",
    "generate_heterogeneous_clients",
    "generate_spurious_correlation_clients",
    "run_exception_benchmark",
    "run_spurious_correlation_benchmark",
]

__version__ = "0.4.0"
