"""Roadmap indexing preserves stable identities and meaningful change times."""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from models.news_item import NewsItem
from sources._rss import parse_feed_to_items
from storage.table_client import NewsStore


def test_roadmap_status_whitelist():
    feed = b'''<rss version="2.0"><channel><item>
    <title>Teams: New feature</title><link>https://www.microsoft.com/roadmap?id=123</link>
    <pubDate>Fri, 09 Oct 2026 10:00:00 GMT</pubDate>
    <category>Rolling out</category><category>Desktop</category>
    <description>Must never be stored</description></item></channel></rss>'''
    item = parse_feed_to_items(feed, source_id="m365-roadmap", source_name="Roadmap")[0]
    assert item.tags == ("rolling out",)
    assert "Must never be stored" not in item.model_dump_json()


def test_index_unchanged_metadata_does_not_reset_change_time():
    client = MagicMock()
    client.__enter__.return_value = client
    client.query_entities.return_value = []
    item = NewsItem(title="Teams: Feature", published_at=datetime(2026, 10, 9, tzinfo=UTC),
                    source_id="m365-roadmap", source_name="Roadmap",
                    canonical_url="https://www.microsoft.com/roadmap?id=123")
    with patch("storage.table_client.TableClient.from_connection_string", return_value=client):
        store = NewsStore("unused")
        assert store.index_roadmap([item]) == 1
        initial = client.submit_transaction.call_args.args[0][0][1]
        client.query_entities.return_value = [initial]
        client.submit_transaction.reset_mock()
        assert store.index_roadmap([item]) == 0
        client.submit_transaction.assert_not_called()
        changed = item.model_copy(update={"title": "Teams: Updated feature"})
        assert store.index_roadmap([changed]) == 1
        updated = client.submit_transaction.call_args.args[0][0][1]
        assert updated["RowKey"] == initial["RowKey"]
        assert updated["FirstSeenAt"] == initial["FirstSeenAt"]
