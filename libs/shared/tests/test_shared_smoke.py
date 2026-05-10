"""Smoke tests for the shared library."""


def test_wiki_builder_importable():
    from shared.wiki_builder import ingest_episode, ingest_supply_chain, rebuild_index
    assert callable(ingest_episode)
    assert callable(ingest_supply_chain)
    assert callable(rebuild_index)


def test_slugify():
    from shared.wiki_builder.slugify import slugify, ticker_slug, episode_slug
    assert slugify("Hello World") == "hello-world"
    assert ticker_slug("AAPL") == "aapl"
    assert episode_slug("Test Pod", 42, "Title") == "test-pod_ep42"


def test_render_entity_page():
    from shared.wiki_builder.pages import render_entity_page
    page = render_entity_page(
        entity_id="tsla",
        name="Tesla",
        entity_type="company",
        tickers=["TSLA"],
        mentions=[],
        ticker_history=[],
    )
    assert "# Tesla" in page
    assert "type: entity" in page


def test_ingest_episode_creates_files(tmp_path):
    from shared.wiki_builder import ingest_episode
    ep_path = ingest_episode(
        podcast_name="Test Podcast",
        episode_number=1,
        title="Test Episode",
        date="2025-01-01",
        tickers=["AAPL"],
        tags=["tech"],
        summary_text="Summary here.",
        wiki_root=tmp_path,
    )
    assert ep_path.exists()
    assert (tmp_path / "entities" / "aapl.md").exists()
    assert (tmp_path / "topics" / "tech.md").exists()


def test_rebuild_index(tmp_path):
    from shared.wiki_builder import ingest_episode, rebuild_index
    ingest_episode(
        podcast_name="Test",
        episode_number=1,
        title="Ep",
        date="2025-01-01",
        tickers=[],
        tags=[],
        summary_text="X",
        wiki_root=tmp_path,
    )
    index = rebuild_index(wiki_root=tmp_path)
    assert index.exists()
    assert "1 episodes" in index.read_text()


def test_config_importable():
    from shared.config import load_yaml_config, get_env
    assert callable(load_yaml_config)
    assert callable(get_env)


def test_secrets_importable():
    from shared.secrets import bootstrap, reset
    assert callable(bootstrap)
    assert callable(reset)


def test_gcs_importable():
    from shared.gcs import create_gcs_client, get_bucket
    assert callable(create_gcs_client)
    assert callable(get_bucket)
