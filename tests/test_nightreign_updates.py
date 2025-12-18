from automation.nightreign_updates import (
    NightreignLatestUpdate,
    parse_latest_update,
)


def test_parse_latest_update_basic() -> None:
    html = """
    <html>
      <body>
        <h2>最新ニュース</h2>
        <ul>
          <li>[2025.12.18]テストニュース</li>
        </ul>

        <h2>最新アップデート</h2>
        <h3>[2025.12.17]アップデートファイル配信のお知らせ(App Ver. 1.031 /
        Regulation Ver. 1.03.2)</h3>
        <p>
          <a href="https://nightreign.eldenring.jp/article/251217_1.html">
            アップデート詳細
          </a>
        </p>
      </body>
    </html>
    """

    update = parse_latest_update(html)

    assert isinstance(update, NightreignLatestUpdate)
    assert update.date_text == "2025.12.17"
    assert "アップデートファイル配信のお知らせ" in update.title
    assert update.app_version == "1.031"
    assert update.regulation_version == "1.03.2"
    assert update.url == "https://nightreign.eldenring.jp/article/251217_1.html"
