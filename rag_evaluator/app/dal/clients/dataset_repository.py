import json
import os
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from app.core.exceptions import DatasetException
from app.schemas.dataset_schema import EvaluationCase, EvaluationDataset


class DatasetRepository(Protocol):
    """Contrat de lecture d'un dataset d'évaluation."""

    def load(self) -> list[EvaluationCase]:
        """Charge et valide tous les cas du dataset.

        Returns:
            Cas validés, prêts à être évalués.

        Raises:
            DatasetException: Si la lecture ou la validation échoue.
        """
        ...


class JsonDatasetRepository:
    """Lit un dataset JSON depuis le stockage local."""

    def __init__(self, path: Path) -> None:
        """Configure le fichier dataset à lire.

        Args:
            path: Chemin du fichier JSON monté dans le conteneur.
        """
        self._path = path

    @classmethod
    def from_environment(cls) -> "JsonDatasetRepository":
        """Construit le repository depuis `DATASET_PATH`.

        Returns:
            Repository configuré avec le chemin du dataset.

        Raises:
            DatasetException: Si `DATASET_PATH` n'est pas configuré.
        """
        dataset_path = os.getenv("DATASET_PATH")
        if not dataset_path:
            raise DatasetException(
                message="DATASET_PATH doit être configuré",
                details={"env_var": "DATASET_PATH"},
            )
        return cls(Path(dataset_path))

    def load(self) -> list[EvaluationCase]:
        """Lit puis valide le dataset complet avec Pydantic.

        Returns:
            Cas validés, sans validation différée dans la boucle métier.

        Raises:
            DatasetException: Si le fichier est illisible, invalide ou incomplet.
        """
        try:
            with self._path.open("r", encoding="utf-8") as dataset_file:
                raw_dataset = json.load(dataset_file)
            return EvaluationDataset.model_validate(raw_dataset).root
        except json.JSONDecodeError as exception:
            raise DatasetException(
                message="Dataset JSON invalide",
                internal_message="Décodage JSON du dataset impossible",
                internal_details={"dataset_path": str(self._path)},
            ) from exception
        except ValidationError as exception:
            raise DatasetException(
                message="Dataset non conforme au schéma attendu",
                details={"errors": exception.error_count()},
                internal_message="Validation Pydantic du dataset impossible",
                internal_details={"dataset_path": str(self._path)},
            ) from exception
        except OSError as exception:
            raise DatasetException(
                message="Impossible de lire le dataset",
                internal_message="Lecture du fichier dataset impossible",
                internal_details={
                    "dataset_path": str(self._path),
                    "error_type": type(exception).__name__,
                },
            ) from exception
