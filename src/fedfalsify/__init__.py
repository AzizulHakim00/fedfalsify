"""FedFalsify: counterexample-guided federated mechanism discovery."""

from .basis import CandidateEquation, TermCatalog
from .benchmarks import (
    BenchmarkResult,
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
    "BenchmarkResult",
    "CandidateEquation",
    "ClientDataset",
    "DiscoveryResult",
    "FedFalsifyDiscovery",
    "FederatedFalsifierClient",
    "RepairDecision",
    "TermCatalog",
    "generate_exception_clients",
    "generate_heterogeneous_clients",
    "generate_spurious_correlation_clients",
    "run_exception_benchmark",
    "run_spurious_correlation_benchmark",
]

__version__ = "0.2.0"
