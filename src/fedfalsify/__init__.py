"""FedFalsify: counterexample-guided federated mechanism discovery."""

from .basis import CandidateEquation, TermCatalog
from .client import FederatedFalsifierClient
from .data import ClientDataset, generate_heterogeneous_clients
from .server import DiscoveryResult, FedFalsifyDiscovery

__all__ = [
    "CandidateEquation",
    "ClientDataset",
    "DiscoveryResult",
    "FedFalsifyDiscovery",
    "FederatedFalsifierClient",
    "TermCatalog",
    "generate_heterogeneous_clients",
]

__version__ = "0.1.0"
