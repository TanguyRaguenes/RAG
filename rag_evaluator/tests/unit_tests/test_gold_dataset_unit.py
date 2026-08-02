from pathlib import Path

from app.dal.clients.dataset_repository import JsonDatasetRepository


def test_gold_dataset_contains_50_unique_cases_with_existing_sources() -> None:
    service_root = Path(__file__).resolve().parents[2]
    cases = JsonDatasetRepository(service_root / "data" / "dataset.json").load()
    wiki_directory = service_root / "data" / "wikis"

    assert len(cases) == 50
    assert [case.id for case in cases] == [f"Q{index:03d}" for index in range(1, 51)]
    assert len({case.id for case in cases}) == 50

    expected_sources = {
        source for case in cases for source in (case.expected_sources or [])
    }
    assert expected_sources
    assert all((wiki_directory / source).is_file() for source in expected_sources)
