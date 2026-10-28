from preorder_sniper.watcher import selector_marker, selector_matches_html


def test_selector_marker_handles_id_and_class_selectors():
    assert selector_marker("#add-to-cart-button") == 'id="add-to-cart-button"'
    assert selector_marker(".add-to-cart-button") == "add-to-cart-button"


def test_selector_matches_html_supports_configured_selector_types():
    html = (
        '<button id="add-to-cart-button"></button>'
        '<button class="button add-to-cart-button"></button>'
        '<button data-test="shipItButton"></button>'
    )

    assert selector_matches_html("#add-to-cart-button", html)
    assert selector_matches_html(".add-to-cart-button", html)
    assert selector_matches_html("[data-test='shipItButton']", html)
