"""Build every profile card into assets/, with matching heights so they sit side by side.

    PROFILE_TOKEN=... python3 scripts/build.py [--debug]
"""

import languages
import stats

if __name__ == "__main__":
    lang_items = languages.collect()
    stat_data = stats.collect()
    h = max(languages.height(lang_items), stats.height(stat_data))

    languages.OUT.parent.mkdir(parents=True, exist_ok=True)
    languages.OUT.write_text(languages.render(lang_items, min_h=h))
    stats.OUT.write_text(stats.render(stat_data, min_h=h))
    print(f"Wrote {languages.OUT.name} and {stats.OUT.name} ({h}px tall) in {languages.OUT.parent}")
