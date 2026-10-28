import json

import pytest

from preorder_sniper.config import load_products


def test_load_products_rejects_incomplete_product(tmp_path):
    products_file = tmp_path / "products.json"
    products_file.write_text(json.dumps([{"retailer": "amazon"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly"):
        load_products(products_file)
